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

    def _authorized_keys_path(self, user_name):
        return os.path.join('~' + user_name, '.ssh', 'authorized_keys').replace('\\', '/')

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
        cmd = ['scp', '-S', '-B', '-P', str(self.port), src, target]
        l.debug('Copying file from %s to %s using SCP', src, target)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = [x.decode('utf-8') for x in p.communicate()]
        l.debug('Command output:')
        l.debug('    stdout: {0}'.format(stdout))
        l.debug('    stderr: {0}'.format(stderr))
        l.debug('    return value: {0}'.format(p.returncode))
        return stdout, stderr, p.returncode

    def _user_exists(self, user_name):
        return self.run("getent passwd " + user_name)[2] == 0

    def get_file(self, file_path_to_get):
        with tempfile.NamedTemporaryFile() as tempf:
            stdout, stderr, returncode = self._scp('{0}@{1}:{2}'.format(self.ssh_user, self.hostname, file_path_to_get), tempf.name.replace('C:', '/c').replace('\\', '/'))
            if returncode != 0:
                raise interpret_ssh_error(returncode, stderr, stdout)
            return tempf.read()

    def put_file(self, file_path_to_put, file_data):
        with tempfile.NamedTemporaryFile() as tempf:
            tempf.write(file_data)
            tempf.flush()
            stdout, stderr, returncode = self._scp(tempf.name.replace('C:', '/c').replace('\\', '/'), '{0}@{1}:{2}'.format(self.ssh_user, self.hostname, file_path_to_put))
            if returncode != 0:
                raise interpret_ssh_error(returncode, stderr, stdout)

    def set_user_permissions(self, user_name, user_group):
        cmd = '''
        chmod 700 /home/{0}/.ssh;
        chmod 700 /home/{0}/.ssh/authorized_keys;
        chown -R {0}:{1} /home/{0}/.ssh
        '''.format(user_name, user_group)
        stdout, stderr, returncode = self.run(cmd)
        if returncode != 0:
            raise interpret_ssh_error(returncode, stderr, stdout)

    def sync_user_account(self, user_name, uid, main_group, alternate_groups, enabled):
        user_add_mod = 'useradd'
        if self._user_exists(user_name):
            user_add_mod = 'usermod'

        shell = '/bin/bash'
        if enabled == False:
            shell = '/bin/false'

        # add alt groups, if there are no alt-groups specified, then replace them with the default group (which is ignored)
        alt_groups_flag = ''
        if len(alternate_groups) > 0:
            for group in alternate_groups:
                alt_groups_flag+= ' ' + group
        else:
            alt_groups_flag=' ' + main_group

        cmd = '''
            {0} -s {1} -u {2} -g {3} -G{4} {5};
            mkdir -p /home/{5}/.ssh;
        '''.format(user_add_mod, shell, uid, main_group, alt_groups_flag, user_name)
        stdout, stderr, returncode = self.run(cmd)
        if returncode != 0:
            raise interpret_ssh_error(returncode, stderr, stdout)

    def sync_user_key(self, user_name, keys):
        try:
            old_auth_keys_file_data = self.get_file(self._authorized_keys_path())
        except SSHError:
            old_auth_keys_file_data = ''

        ak = claviger.authorized_keys.parse('')
        for key in keys:
            if not ak.contains(key['key']):
                ak.add(key['options'], key['keytype'], key['key'], key['comment'])
        authorized_keys_file_data = six.binary_type(ak)

        if old_auth_keys_file_data != authorized_keys_file_data:
            self.put_file(self._authorized_keys_path(), authorized_keys_file_data)
