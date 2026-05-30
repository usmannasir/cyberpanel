"""Primary administrator detection (replaces hardcoded userName == admin)."""

PRIMARY_ADMIN_PK = 1


def is_primary_administrator(user):
    if user is None:
        return False
    if getattr(user, 'pk', None) == PRIMARY_ADMIN_PK:
        return True
    try:
        uname = getattr(user, 'userName', None)
        return str(uname) == 'admin'
    except Exception:
        return False


def is_primary_admin_username(name):
    return str(name or '') == 'admin'
