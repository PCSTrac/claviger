import os.path
import logging
import tempfile
import subprocess


l = logging.getLogger(__name__)

class SSH(object):
    def connect(self, hostname, port,  ssh_user):
        return SSHSession(hostname, port, ssh_user)


def interpret_ssh_error(exitcode, stderr, stdout):
    """ Interpret the output of `ssh' and create a suitable exception """
    if 'Host key verification failed' in stderr:
        return HostKeyVerificationFailed()
    msg = 'scp failed: exitcode {0}'.format(exitcode)
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
    def _ssh(self, src, trg):
        cmd = ['ssh', '-B', '-P', str(self.port), src, trg]
        l.debug('executing %s', cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        stdout_txt, stderr_txt = [x.decode('utf-8') for x in p.communicate()]
        if p.returncode != 0:
            raise interpret_scp_error(p.returncode, stderr_txt, stdout_txt)

    def run(self, cmd):
        cmd = ['ssh', '{0}@{1}'.format(self.ssh_user, self.hostname), '"' + cmd + '"']
        l.debug('running command %s', cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        stdout_txt, stderr_txt = [x.decode('utf-8') for x in p.communicate()]
        if p.returncode != 0:
            raise interpret_ssh_error(p.returncode, stderr_txt, stdout_txt)
        return stdout_txt
