"""Username rename with ACL checks."""
from plogical.usernameUtils import (
    normalize_username,
    validate_username_format,
    username_exists_exact,
)
from plogical.adminIdentity import is_primary_administrator, is_primary_admin_username
from plogical.acl import ACLManager


def can_rename_user(actor, target_admin):
    if actor is None or target_admin is None:
        return False, 'Access denied.'
    if is_primary_administrator(actor):
        return True, ''
    if actor.pk == target_admin.pk:
        return True, ''
    try:
        current_acl = ACLManager.loadedACL(actor.pk)
        if current_acl.get('admin') == 1:
            return True, ''
        if target_admin.owner == actor.pk:
            return True, ''
    except Exception:
        pass
    return False, 'You do not have permission to rename this user.'


def rename_administrator(actor, target_pk, new_username):
    from loginSystem.models import Administrator
    new_username = normalize_username(new_username)
    ok, msg = validate_username_format(new_username)
    if not ok:
        return {'status': 0, 'error_message': msg}
    try:
        target = Administrator.objects.get(pk=target_pk)
    except Administrator.DoesNotExist:
        return {'status': 0, 'error_message': 'User not found.'}
    allowed, deny = can_rename_user(actor, target)
    if not allowed:
        return {'status': 0, 'error_message': deny}
    if normalize_username(target.userName) == new_username:
        return {'status': 1, 'userName': new_username}
    if username_exists_exact(new_username, exclude_pk=target.pk):
        return {'status': 0, 'error_message': 'Username already exists.'}
    if is_primary_admin_username(target.userName) and not is_primary_administrator(actor):
        return {'status': 0, 'error_message': 'Cannot rename the primary administrator.'}
    old_name = target.userName
    target.userName = new_username
    target.save(update_fields=['userName'])
    from plogical.session_utils import invalidate_all_sessions_for_user
    sessions_cleared = invalidate_all_sessions_for_user(target.pk)
    return {
        'status': 1,
        'userName': new_username,
        'oldUserName': old_name,
        'sessionsCleared': sessions_cleared,
    }
