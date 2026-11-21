"""The switch in front of everything Multi-Server Manager does.

The feature is off on every server until root gives the server a role. It also
stays off, whatever the role file says, while its tables are missing or lack a
unique index, and where Ed25519 signing does not work (FIPS mode).
"""
from multiServer import keys

_SIGNING = False


def active_role():
    """'controller' or 'node' when the feature can run on this server, otherwise 'off'.

    Never raises. The role file is read on every call, so switching the feature
    off is seen by the next request in every worker; with the feature off
    nothing else is looked at.
    """
    try:
        role = keys.role()
        if role == keys.OFF or not _signing():
            return keys.OFF
        from multiServer import schema
        return role if schema.ready() else keys.OFF
    except Exception:
        return keys.OFF


def _signing():
    # Only success is remembered, as for the tables.
    global _SIGNING
    if not _SIGNING:
        from multiServer import crypto
        _SIGNING = crypto.self_test() is True
    return _SIGNING
