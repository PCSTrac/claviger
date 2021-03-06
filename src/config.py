""" Reads claviger's configuration file. """
import yaml
import logging
import os.path
import textwrap
import itertools
import collections

import six
import tarjan
import jsonschema

import claviger.authorized_keys

class ConfigError(Exception):
    pass

ParsedServerKey = collections.namedtuple('ParsedServerKey', ('hostname', 'abstract'))

l = logging.getLogger(__name__)

# Schema for the configuration file.
_SCHEMA = None

def get_schema():
    global _SCHEMA
    if not _SCHEMA:
        l.debug('loading schema...')
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.schema.yml')) as f:
            _SCHEMA = yaml.load(f)
        l.debug('done loading schema!')
    return _SCHEMA

class ConfigurationError(Exception):
    pass

def parse_server_key(key):
    """ Converts a server key like localhost to a tuple (hostname, abstract) """
    abstract = False
    hostname = None
    if key.startswith('$'):
        abstract = True
    else:
        hostname = key
    return ParsedServerKey(hostname=hostname, abstract=abstract)

def load(path):
    """ Loads the configuration file.

        A lot of the work is done by YAML.  We validate the easy bits with
        a JSON schema. The rest by hand. """
    l.debug('loading configuration file...')
    with open(path) as f:
        cfg = yaml.load(f)

    if not isinstance(cfg, dict):
        raise ConfigurationError('Configuration file is empty')

    l.debug('checking schema...')
    # First small fixes which the schema can't handle
    cfg.setdefault('servers', {})
    cfg['servers'].setdefault('$default', {})
    cfg.setdefault('users', {})

    # Now check the schema
    jsonschema.validate(cfg, get_schema())

    l.debug('processing users...')
    users = {}
    for user_name, user_obj in six.iteritems(cfg['users']):
        user_obj.setdefault('uid', '')
        user_obj.setdefault('group', '')
        user_obj.setdefault('additional_groups', [])
        user_obj.setdefault('enabled', True)
        for index, key in enumerate(user_obj['keys']):
            config_key_string = claviger.authorized_keys.Entry.parse(user_obj['keys'][index])
            user_obj['keys'][index] = {
                'key': config_key_string.key,
                'options': config_key_string.options,
                'comment': config_key_string.comment,
                'keytype': config_key_string.keytype
            }
        user_obj['name'] = user_name
        users[user_name] = user_obj
    cfg['users'] = users

    l.debug('processing server stanza short-hands...')
    new_servers = {}
    for server_key, server in six.iteritems(cfg['servers']):
        server.setdefault('port', 22)
        server.setdefault('ssh_user', 'root')
        server.setdefault('users', [])
        parsed_server_key = parse_server_key(server_key)
        server.setdefault('hostname', parsed_server_key.hostname)
        server_name = server['hostname']
        server.setdefault('like', '$default' if server_key != '$default' else None)
        server.setdefault('abstract', parsed_server_key.abstract)
        for user_name in itertools.chain(server['users']):
            if not user_name in cfg['users']:
                "User {0} (on {1}) does not exist".format(user_name, server_name)
        if server_name in new_servers:
            raise ConfigurationError("Duplicate server name {0}".format(server_name))
        new_servers[server_key] = server
    cfg['servers'] = new_servers

    l.debug('resolving server stanza inheritance...')
    # create dependancy graph and use Tarjan's algorithm to find a possible
    # order to evaluate the server stanzas.
    server_dg = {server_name: [server['like']] if server['like'] else []
                    for server_name, server in six.iteritems(cfg['servers'])}
    for server_cycle_names in tarjan.tarjan(server_dg):
        if len(server_cycle_names) != 1:
            raise ConfigurationError("There is a cyclic dependacy among the servers {0}".format(server_cycle_names))
        target_server = cfg['servers'][server_cycle_names[0]]
        if not target_server['like']:
            continue
        if not target_server['like'] in cfg['servers']:
            pass
        source_server = cfg['servers'][target_server['like']]

        # First the simple attributes
        for attr in ('port', 'hostname', 'ssh_user'):
            if attr in source_server:
                if target_server[attr] is None:
                    target_server[attr] = source_server[attr]

        # Now, the  user list
        for user in source_server['users']:
            if key not in target_server['users']:
                target_server['users'].append(user)

    l.debug('done config...')
    return cfg
