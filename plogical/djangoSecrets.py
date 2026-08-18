"""Load Django SECRET_KEY from a protected file (not from source)."""
import os
import secrets

SECRET_KEY_FILE = os.environ.get('CYBERPANEL_DJANGO_SECRET_FILE', '/etc/cyberpanel/django_secret')
SECRET_KEY_ENV = 'CYBERPANEL_DJANGO_SECRET_KEY'


def _read_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            return handle.read().strip()
    except OSError:
        return ''


def _write_file(path, value):
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, mode=0o750, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(value)
            handle.write('\n')
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def get_django_secret_key(fallback=None, create_if_missing=True):
    env_val = os.environ.get(SECRET_KEY_ENV, '').strip()
    if env_val:
        return env_val
    file_val = _read_file(SECRET_KEY_FILE)
    if file_val:
        return file_val
    if create_if_missing:
        if fallback:
            if _write_file(SECRET_KEY_FILE, fallback):
                return fallback
        generated = secrets.token_urlsafe(64)
        if _write_file(SECRET_KEY_FILE, generated):
            return generated
    if fallback:
        return fallback
    raise RuntimeError('Django SECRET_KEY missing; set %s or %s' % (SECRET_KEY_FILE, SECRET_KEY_ENV))
