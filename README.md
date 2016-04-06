claviger
********

claviger manages users and ssh keys across multiple servers.

Quick introduction
==================

Tell claviger which keys you want to put on which server
by creating a `~/.claviger` file.  An example

```yaml
users:
  username:
    keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINYZEwjtu8w9Hsvx85TlYE95MLV9Whc3N1ajrH7+gu7A
    uid: 5001
    group: maingroup
    enabled: true
    additional_groups:
      - addlgrp1
      - addlgrp2
  username2:
    keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINYZEwjtu8w9Hsvx85TlYE95MLV9Whc3N1ajrH7+gu7A
    uid: 5002
    group: maingroup
    enabled: true
servers:
  servername.tld:
    ssh_user: root
    users:
      - username
      - username2
```

Then run `claviger`.

Installation
============

To install claviger, simply run:

    pip install git+ssh://git@github.com:PCSTrac/claviger.git

Also, the servers that this will be run on need a user with passwordless sudo access (or root)

Claviger config file
====================

A .claviger is written in YAML.  It contains two main maps, `servers` and `users`. `users` are configured in the `users` map, then refrenced in the `users` list under each server if they are managed in that server.

A complete example of the claviger file can be found at `example.claviger` in this repo.

See below for the available options in the config file.

Key stanzas
-----------
The key of a `key` stanza is the username taht you want to manage.

A key stanza can contain the following entries:

| Key | Description |
| ---: | ----------- |
| `keys` | An array of public keys for this user. The format is the OpenSSH format (the same format used in an `authorized_keys` file). This replaces all keys in the `authorized_keys` file with these, so if this is set to `[]` **it will clear out the authorized keys for this user**<br/>*Default*: `[]`|
| `uid` | The UID of the user. If this is specified, the user will be created or modified to have it match. If it is not provided, linux will automatically create and manage it.<br/>*Default*: managed by the server.|
| `group` | The main linux group for this user. The group **must** already exist on the server.<br/>*Default*: Created and managed by the server (generally it's set to the username)|
| `enabled` | If set to false the user will be disabled (have their shell set to `/bin/false`). *Default*: `true` |
| `additional_groups` | An array of additional groups to apply to this user. The group **must** already exist on the server. This replaces all additional groups for this user, so if this is set to `[]` **it will clear out all additional groups for this user**<br/>*Default*: `[]` |

Server stanzas
--------------
The key of a server stanza is the hostname of the server.

If a server key starts with a dollar sign (for instance $work`),
then it is considered `abstract` --- see below.

A server stanza is a map which may have the following entries:

| Key | Description |
| ---: | ----------- |
| `hostname` | The hostname of the server<br/>*Default*: taken from the stanza key.|
| `users` | An array of users that will be managed for this server. If a user is not included in this list, it will not be touched on this server.<br/>*Default*: `[]`|
| `ssh_user` | The user that claviger will login as. <br/>*Default*: `root`|
| `port` | The port that will be used to SSH into the server. *Default*: `22` |
| `like` | The name of another server stanza. If set the entries for the other stanza will act as defaults for this stanza.<br/>*Default*: `$default` |
| `abstract` | `true` or `false`. If set to `true` claviger will treat this as an abstract entry and will not do anything to this server.<br/>*Default*: `false`|

Abstract servers and `$default`
---------------------------------

claviger will not check an *abstract* server.  This is useful to cleanly configure multiple servers.

```yaml
$high_security_servers:
  users:
    - usera
    - userb
    - userc
  ssh_user: management_user
  port: 4489
```

By default, server inherits from the hidden ``$default`` abstract server.

```yaml
$default:
  ssh_user: root
  port: 22
  users: []
```
.. _YAML: http://yaml.org
