"""Cloudflare credentials for paid SSL V2; never evaluate account.conf as shell."""
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile

ACCOUNT = Path('/root/.acme.sh/account.conf')
NAMES = ('CF_Token', 'CF_Key', 'CF_Email', 'CF_Account_ID', 'CF_Zone_ID')
ERROR = 'Cloudflare settings could not be saved. Check the credential type and server configuration.'


def validate(mode, secret, email=''):
    if mode not in ('token', 'global_key'):
        raise ValueError(ERROR)
    if not isinstance(secret, str) or not re.fullmatch(r'[A-Za-z0-9._~+/=-]{10,4096}', secret):
        raise ValueError(ERROR)
    if mode == 'global_key':
        if not isinstance(email, str) or not re.fullmatch(r'[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}', email):
            raise ValueError(ERROR)
        return {'CF_Key': secret, 'CF_Email': email}
    return {'CF_Token': secret}


def _safe_parent(path):
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(ERROR)
    info = path.parent.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError(ERROR)


def _contents(path):
    _safe_parent(path)
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return ''
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_size > 1024 * 1024:
            raise ValueError(ERROR)
        with os.fdopen(fd, 'r', closefd=False) as source:
            return source.read(1024 * 1024 + 1)
    finally:
        os.close(fd)


def credentials(path=ACCOUNT):
    values = {}
    for line in _contents(Path(path)).splitlines():
        match = re.match(r'^\s*(?:export\s+)?((?:SAVED_)?CF_(?:Token|Key|Email|Account_ID|Zone_ID))\s*=(.*)$', line)
        if not match:
            continue
        try:
            parts = shlex.split(match[2], comments=True)
        except ValueError:
            raise ValueError(ERROR) from None
        if len(parts) != 1:
            raise ValueError(ERROR)
        values[match[1]] = parts[0]
    def value(name):
        return values.get(name) or values.get('SAVED_' + name, '')
    if value('CF_Token'):
        return validate('token', value('CF_Token'))
    if value('CF_Key'):
        return validate('global_key', value('CF_Key'), value('CF_Email'))
    return {}


def save(mode, secret, email='', path=ACCOUNT):
    updates = validate(mode, secret, email)
    path = Path(path)
    _safe_parent(path)
    lock = os.open(str(path.parent / '.cyberpanel-cloudflare.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    temporary = None
    try:
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError(ERROR)
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = _contents(path)
        pattern = re.compile(r'^\s*(?:export\s+)?(?:SAVED_)?CF_(?:Token|Key|Email|Account_ID|Zone_ID)\s*=')
        kept = ''.join(line for line in old.splitlines(keepends=True) if not pattern.match(line))
        if kept and not kept.endswith('\n'):
            kept += '\n'
        kept += ''.join("SAVED_%s=%s\n" % (name, shlex.quote(value)) for name, value in updates.items())
        fd, temporary = tempfile.mkstemp(prefix='.cyberpanel-cloudflare-', dir=str(path.parent))
        with os.fdopen(fd, 'w') as destination:
            os.fchmod(destination.fileno(), 0o600)
            destination.write(kept)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            os.unlink(temporary)
        os.close(lock)


def metadata(path=ACCOUNT):
    result = credentials(path)
    return {'configured': bool(result), 'mode': 'token' if result.get('CF_Token') else 'global_key' if result else 'token'}


def request(action, payload=None):
    """Use the install/upgrade-provisioned fixed action; secrets travel on stdin."""
    if action not in ('metadata', 'save'):
        raise ValueError(ERROR)
    command = [sys.executable, '-I', '-S', str(Path(__file__).resolve()), action]
    if os.geteuid() != 0:
        command = ['sudo', '-n', '--', '/usr/local/CyberPanel/bin/python', '-I', '-S',
                   '/usr/local/CyberCP/plogical/cloudflareCredentials.py', action]
    try:
        result = subprocess.run(command, input=json.dumps(payload or {}).encode(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=15, check=False)
        if result.returncode:
            raise ValueError(ERROR)
        status = json.loads(result.stdout)
        if set(status) != {'configured', 'mode'} or type(status['configured']) is not bool or status['mode'] not in ('token', 'global_key'):
            raise ValueError(ERROR)
        return status
    except Exception:
        raise ValueError(ERROR) from None


def find_zone(domain, auth=None, session=None):
    """Check the actual enclosing zone without requiring origin A/AAAA records."""
    if not isinstance(domain, str) or len(domain) > 253 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', domain):
        return 0, 'Invalid domain.'
    labels = domain.lower().split('.')
    if len(labels) < 2 or any(not part or len(part) > 63 or part.startswith('-') or part.endswith('-') for part in labels):
        return 0, 'Invalid domain.'
    try:
        auth = credentials() if auth is None else auth
        if not auth:
            return 0, 'Cloudflare credentials are not configured.'
        if auth.get('CF_Token'):
            headers = {'Authorization': 'Bearer ' + auth['CF_Token']}
        else:
            headers = {'X-Auth-Key': auth['CF_Key'], 'X-Auth-Email': auth['CF_Email']}
        if session is None:
            import requests
            session = requests
        for offset in range(len(labels) - 1):
            name = '.'.join(labels[offset:])
            response = session.get('https://api.cloudflare.com/client/v4/zones', headers=headers,
                                   params={'name': name, 'per_page': 1}, timeout=10, allow_redirects=False)
            if response.status_code != 200:
                return 0, 'Cloudflare zone lookup failed. Check token permissions and zone scope.'
            data = response.json()
            if data.get('success') is not True:
                return 0, 'Cloudflare zone lookup failed. Check token permissions and zone scope.'
            if any(zone.get('name') == name and zone.get('status') == 'active' for zone in data.get('result', [])):
                return 1, None
        return 0, 'Domain is not in an active Cloudflare zone accessible to these credentials.'
    except Exception:
        return 0, 'Cloudflare zone lookup failed. Check credentials and network access.'


if __name__ == '__main__':
    try:
        if os.geteuid() != 0 or len(sys.argv) != 2:
            raise ValueError(ERROR)
        action = sys.argv[1]
        if action == 'save':
            payload = json.loads(sys.stdin.buffer.read(16385))
            save(payload.get('mode'), payload.get('secret'), payload.get('email', ''))
        elif action != 'metadata':
            raise ValueError(ERROR)
        print(json.dumps(metadata()))
    except Exception:
        print(json.dumps({'error': ERROR}))
        sys.exit(1)
