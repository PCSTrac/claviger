import os.path
import logging
import tempfile
import subprocess

import six
import claviger.authorized_keys

l = logging.getLogger(__name__)

class SSH(object):
    def connect(self, hostname, port,  ssh_user):
        return SSHSession(hostname, port, ssh_user)


def interpret_ssh_error(exitcode, stderr, stdout):
    """ Interpret the output of `ssh' and create a suitable exception """
    if 'Host key verification failed' in stderr:
        return HostKeyVerificationFailed()
    msg = 'ssh failed: exitcode {0}'.format(exitcode)
    if stderr.strip():
        msg += '; stderr {0}'.format(repr(stderr))
    if stdout.strip():
        msg += '; stdout {0}'.format(repr(stdout))
    return SSHError(msg)

class SSHError(Exception):
    pass
class HostKeyVerificationFailed(SSHError):
    pass

class SSHSession(object):
    def __init__(self, hostname, port, ssh_user):
        self.hostname = hostname
        self.port = port if port else 22
        self.ssh_user = ssh_user

    def _fix_path_for_windows(self, path):
        return path.replace('\\', '/').replace('c:', '/c').replace('b:', '/b')

    def _authorized_keys_path(self, user_name):
        return self._fix_path_for_windows(os.path.join('~' + user_name, '.ssh', 'authorized_keys'))

    def _ssh(self, cmdToRun):
        cmd = ['ssh', '{0}@{1}'.format(self.ssh_user, self.hostname), cmdToRun]
        l.debug('Running command  %s on remote server %s@%s', cmdToRun, self.ssh_user, self.hostname)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = [x.decode('utf-8') for x in p.communicate()]
        l.debug('Command output:')
        l.debug('    stdout: {0}'.format(stdout))
        l.debug('    stderr: {0}'.format(stderr))
        l.debug('    return value: {0}'.format(p.returncode))
        return stdout, stderr, p.returncode

    def _scp(self, src, target):
        cmd = ['scp', '-B', '-P', str(self.port), src, target]
        l.debug('Copying file from %s to %s using SCP', src, target)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = [x.decode('utf-8') for x in p.communicate()]
        l.debug('Command output:')
        l.debug('    stdout: {0}'.format(stdout))
        l.debug('    stderr: {0}'.format(stderr))
        l.debug('    return value: {0}'.format(p.returncode))
        return stdout, stderr, p.returncode

    def _user_exists(self, user_name):
        return self._ssh("getent passwd " + user_name)[2] == 0

    def get_file(self, file_path_to_get):
        stdout, stderr, returncode = self._ssh('sudo cat {0}'.format(file_path_to_get))
        if stderr != '':
            raise interpret_ssh_error(returncode, stderr, stdout)
        return stdout

    def put_file(self, file_path_to_put, file_data):
        stdout, stderr, returncode = self._ssh('sudo echo "{0}" > {1}'.format(file_data, file_path_to_put))
        if stderr != '':
            raise interpret_ssh_error(returncode, stderr, stdout)

    def set_user_permissions(self, user_name, user_group):
        cmd = '''
        chmod 700 /home/{0}/.ssh;
        chmod 700 /home/{0}/.ssh/authorized_keys;
        chown -R {0}:{1} /home/{0}/.ssh
        '''.format(user_name, user_group)
        stdout, stderr, returncode = self._ssh(cmd)
        if stderr != '':
            raise interpret_ssh_error(returncode, stderr, stdout)

    def sync_user_account(self, user_name, uid, main_group, additional_groups, enabled):
        user_add_mod = 'useradd'
        if self._user_exists(user_name):
            user_add_mod = 'usermod'

        shell = '/bin/bash'
        if enabled == False:
            shell = '/bin/false'

        # add alt groups, if there are no alt-groups specified, then replace them with the default group (which is ignored)
        alt_groups_flag = ''
        if len(additional_groups) > 0:
            for group in additional_groups:
                alt_groups_flag+= ' ' + group
        else:
            alt_groups_flag=' ' + main_group

        cmd = '''
            {0} -s {1} -u {2} -g {3} -G{4} {5};
            mkdir -p /home/{5}/.ssh;
        '''.format(user_add_mod, shell, uid, main_group, alt_groups_flag, user_name)
        stdout, stderr, returncode = self._ssh(cmd)
        if stderr != '':
            raise interpret_ssh_error(returncode, stderr, stdout)

    def sync_user_keys(self, user_name, keys):
        try:
            old_auth_keys_file_data = self.get_file(self._authorized_keys_path(user_name))
        except SSHError:
            old_auth_keys_file_data = ''

        ak = claviger.authorized_keys.parse('')
        for key in keys:
            if not ak.contains(key['key']):
                ak.add(key['options'], key['keytype'], key['key'], key['comment'])
        authorized_keys_file_data = six.binary_type(ak)

        if old_auth_keys_file_data != authorized_keys_file_data:
            self.put_file(self._authorized_keys_path(user_name), authorized_keys_file_data)
