#!/usr/local/CyberCP/bin/python
"""Multi-Server Manager from the command line. Run as root, with the panel's Python:

    /usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py status
    /usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py role off|controller|node
    /usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py disable
    /usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py revoke LINK_ID

"role" gives this server its role and "disable" is "role off". "revoke", on a
managed server, ends the link of one controller for good (controllers.end).
"status" shows the role and the links.

This is the program that writes the role file. The panel's own role page does
not write it: it asks the panel's root helper to run one of the three command
lines in ROLE_COMMANDS, which are fixed texts. Ending a link on the Controllers
page runs revoke_command(), whose two variable words are the link id of the
row (32 hexadecimal digits) and the number of the signed-in administrator,
both checked again here. Nothing else is taken from the command line, and
nothing from the environment or from standard input.

A role is refused, and the file is left as it is, when it is not one of the
three words, and when it is "controller" or "node" while this server still has
links of the other kind: a controller first removes its servers, a managed
server first ends its controllers. "off" is always possible and asks the
database nothing, so the feature can be switched off whatever state the panel
is in.

Exit status: 0 done, 1 refused or failed, 2 not a command.
"""
import os
import re
import sys

PYTHON = '/usr/local/CyberCP/bin/python'
PROGRAM = '/usr/local/CyberCP/multiServer/msctl.py'
ROLES = ('off', 'controller', 'node')
ROLE_COMMANDS = dict((role, '%s %s role %s' % (PYTHON, PROGRAM, role)) for role in ROLES)

USAGE = 'usage: msctl.py status | role off|controller|node | disable | revoke LINK_ID'
NOT_ROOT = 'Run this as root.'
ROLE_SET = 'This server is now: %s.'
ROLE_KEPT = 'This server already is: %s.'
HAS_SERVERS = ('This controller still has servers. Remove each of them on the Nodes page first, then change '
               'the role.')
HAS_CONTROLLERS = ('This server is still managed by a controller. End each link on the Controllers page '
                   'first, then change the role.')
CANNOT_CHECK = ('The role was not changed: the Multi-Server tables could not be read to see whether links '
                'exist. "role off" works without them.')
NOT_A_NODE = 'Only a managed server ends a link here. On a controller, remove the server on the Nodes page.'
ENDED = 'The link is ended. Its controller can no longer manage this server.'
ALREADY_ENDED = 'This link was ended before.'
NO_SUCH_LINK = 'There is no such link on this server.'
FAILED = 'The link could not be ended. Nothing was changed for other links.'

_LINK = re.compile(r'[0-9a-f]{32}')
_ADMIN = re.compile(r'[1-9][0-9]{0,8}')
_PLAIN = re.compile(r'[A-Za-z0-9 ._:,-]{1,128}')


def revoke_command(link_id, admin_id):
    """The command line that ends one link, for the panel's root helper."""
    if type(link_id) is not str or _LINK.fullmatch(link_id) is None or type(admin_id) is not int \
            or _ADMIN.fullmatch(str(admin_id)) is None:
        raise ValueError('A link id and the number of an administrator are required.')
    return '%s %s revoke %s %d' % (PYTHON, PROGRAM, link_id, admin_id)


def main(arguments, say=print):
    if os.geteuid() != 0:
        say(NOT_ROOT)
        return 1
    if arguments == ['status']:
        return status(say)
    if arguments == ['disable']:
        return set_role('off', say)
    if len(arguments) == 2 and arguments[0] == 'role' and arguments[1] in ROLES:
        return set_role(arguments[1], say)
    if arguments[:1] == ['revoke'] and len(arguments) in (2, 3) and _LINK.fullmatch(arguments[1]) \
            and (len(arguments) == 2 or _ADMIN.fullmatch(arguments[2])):
        return revoke(arguments[1], int(arguments[2]) if len(arguments) == 3 else None, say)
    say(USAGE)
    return 2


def set_role(role, say=print):
    from install import multiserver_identity
    from multiServer import keys
    if role not in ROLES:
        say(USAGE)
        return 2
    if keys.role() == role:
        say(ROLE_KEPT % role)
        return 0
    if role != keys.OFF:
        refusal = _in_the_way(role)
        if refusal is not None:
            say(refusal)
            return 1
    multiserver_identity.set_role(role)
    say(ROLE_SET % role)
    return 0


def _in_the_way(role):
    """Why this server cannot take a role yet, or None. Whatever cannot be checked is in the way."""
    from multiServer import keys
    try:
        _start_django()
        from multiServer import models
        if role == keys.NODE:
            return HAS_SERVERS if models.Node.objects.exists() else None
        live = (models.PENDING, models.ACTIVE, models.PAUSED)
        return HAS_CONTROLLERS if models.Link.objects.filter(status__in=live).exists() else None
    except Exception:
        return CANNOT_CHECK


def revoke(link_id, admin_id=None, say=print):
    from install import multiserver_identity
    from multiServer import keys
    if keys.role() != keys.NODE:
        say(NOT_A_NODE)
        return 1
    try:
        _start_django()
        from multiServer import controllers, views
        administrator = views.active_full_administrator(admin_id) if admin_id is not None else None
        outcome = controllers.end(link_id, administrator.userName if administrator is not None else None,
                                  multiserver_identity.bump_generation)
    except Exception:
        say(FAILED)
        return 1
    say({True: ENDED, False: NO_SUCH_LINK}.get(outcome, ALREADY_ENDED))
    return 0 if outcome else 1


def status(say=print):
    from multiServer import keys
    role = keys.role()
    say('Role: %s' % role)
    if role == keys.OFF:
        return 0
    try:
        _start_django()
        from multiServer import models, switch
        if switch.active_role() != role:
            say('Not running: the Multi-Server tables are missing or signing does not work on this server.')
        if role == keys.NODE:
            say('Revocation counter: %d' % keys.generation())
            for link in models.Link.objects.order_by('created_at', 'link_id'):
                say('Controller link %s  %s  from %s' % _plain(link.link_id, link.status, link.allowed_ips))
        else:
            for node in models.Node.objects.defer('sealed').order_by('label', 'link_id'):
                say('Server %s  %s  %s' % _plain(node.link_id, node.status, node.label))
    except Exception:
        say('The links could not be read from the database.')
        return 1
    return 0


def _plain(*values):
    """Values of a row for a terminal: anything but plain short text is not printed."""
    return tuple(value if type(value) is str and _PLAIN.fullmatch(value) else '?' for value in values)


def _start_django():
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    django.setup()


if __name__ == '__main__':
    # The panel, and nothing beside this file, is what gets imported: the directory of this file holds
    # modules whose names (keys, crypto, audit ...) must not stand in for anybody else's.
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1:]))
