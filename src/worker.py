""" Contains the code to check the authorized_keys file on a server.

    We run several checks in parallel using the multiprocessing module.
    To avoid serialization (and other) issues, we separate the worker
    environment in this module  with the rest of the program. """

import sys
import difflib
import traceback
import collections

import six

import claviger.scp
import claviger.authorized_keys

# arguments send by the main process
Job = collections.namedtuple('Job',
                ('server', 'user_name', 'user', 'dry_run', 'no_diff'))

# this is what we return
JobReturn = collections.namedtuple('JobReturn',
                ('server_name', 'ok', 'result'))
# if everything is ok, the result field is of the following type ...
JobResult = collections.namedtuple('JobResult',
                ('n_keys_added', 'n_keys_removed', 'n_keys_ignored'))
# ... otherwise it is an exception

def check_server(job):
    number_users_added = 0
    for user_name in job.server['users']:
        check_server_for_user(claviger.worker.Job(server=self.cfg['servers'][server_name],
                            user_name=user_name,
                            user=job.users[user_name],
                            dry_run=self.args.dry_run,
                            no_diff=self.args.no_diff))
        number_users_added += 1
    return JobReturn(server_name=job.server['name'], ok=True,
                    result=JobResult(n_keys_added=number_users_added,
                                     n_keys_removed=0,
                                     n_keys_ignored=0))


def check_server_for_user(job):
    try:
        scp = claviger.scp.SCP()
        n_keys_removed = 0
        n_keys_added = 0
        n_keys_ignored = 0
        server = job.server
        user_obj = job.user
        conn = scp.connect(server['hostname'], server['port'],
                                    server['ssh_user'])

        # First make the user if they don't exist
        conn.user_make_if_not_present(user_name)
        # Then pull the current authorized_keys
        original_raw_ak = conn.get(user_name)
        ak = claviger.authorized_keys.parse(original_raw_ak)

        key = job.user['key']
        # TODO update comment/options
        if not ak.contains(key['key']):
            n_keys_added += 1
            ak.add(key['options'], key['keytype'], key['key'], key['comment'])

        raw_ak = six.binary_type(ak)
        conn.put(user_name, raw_ak)
        conn.user_set_permissions(user_name)
    except claviger.scp.SCPError as e:
        return JobReturn(server_name=server['name'], ok=False, result=e)
    except Exception as e:
        # multiprocessing does not pass the stacktrace to the parent process.
        #   ( see http://stackoverflow.com/questions/6126007 )
        # Thus we force the stacktrace in the message.
        raise Exception(''.join(traceback.format_exception(*sys.exc_info())))
