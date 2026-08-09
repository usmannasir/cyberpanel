"""Panel username validation and case-exact auth helpers."""
import re

USERNAME_RE = re.compile(r'^[A-Za-z0-9_-]{3,50}$')
GENERIC_AUTH_FAIL = 'Invalid username or password.'


def normalize_username(value):
    if value is None:
        return ''
    return str(value).strip()


def validate_username_format(username):
    username = normalize_username(username)
    if not username:
        return False, 'Username is required.'
    if not USERNAME_RE.match(username):
        return False, 'Username must be 3-50 characters (letters, numbers, underscore, hyphen).'
    return True, ''


def username_exists_exact(username, exclude_pk=None):
    from loginSystem.models import Administrator
    username = normalize_username(username)
    if not username:
        return False
    qs = Administrator.objects.filter(userName=username)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def resolve_administrator_by_login_name(submitted):
    from loginSystem.models import Administrator
    from django.core.exceptions import ObjectDoesNotExist
    submitted = normalize_username(submitted)
    if not submitted:
        return None, False
    try:
        admin = Administrator.objects.get(userName=submitted)
        return admin, admin.userName == submitted
    except Administrator.DoesNotExist:
        try:
            admin = Administrator.objects.get(userName__iexact=submitted)
            return admin, False
        except Administrator.DoesNotExist:
            return None, False
        except Administrator.MultipleObjectsReturned:
            return None, False


def require_exact_username_match(stored, submitted):
    if stored is None or submitted is None:
        return False
    return normalize_username(stored) == normalize_username(submitted)
