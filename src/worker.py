""" Contains the code to check the authorized_keys file on a server.

    We run several checks in parallel using the multiprocessing module.
    To avoid serialization (and other) issues, we separate the worker
    environment in this module  with the rest of the program. """

import sys
import difflib
import traceback
import collections

import claviger.ssh


# this is what we return
JobReturn = collections.namedtuple('JobReturn', ('server_name', 'user_name', 'ok', 'err'))


def sync_user_for_server(server, user):
    try:
        ssh = claviger.ssh.SSH()

        user_name = user['name']
        uid = user['uid']
        main_group = user['group']
        enabled = user['enabled']
        additional_groups = user['additional_groups']
        keys = user['keys']

        conn = ssh.connect(server['hostname'], server['port'], server['ssh_user'])

        # First sync the user's account and attributes
        conn.sync_user_account(user_name, uid, main_group, alternate_groups, enabled)
        # Then sync their keys
        conn.sync_user_keys(user_name, keys)
        # Finally, fix permissions on the files
        conn.user_set_permissions(user_name)

        return JobReturn(server_name=server['name'], user_name=user_name, ok=True, err='')
    except claviger.ssh.SSHError as e:
        return JobReturn(server_name=server['name'], user_name=user_name, ok=False, err=e)
    except Exception as e:
        # multiprocessing does not pass the stacktrace to the parent process.
        #   ( see http://stackoverflow.com/questions/6126007 )
        # Thus we force the stacktrace in the message.
        raise Exception(''.join(traceback.format_exception(*sys.exc_info())))
