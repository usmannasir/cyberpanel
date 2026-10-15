"""Drive credential refresh without changing client identity or leaking credentials."""
import copy
from datetime import datetime, timedelta, timezone
import json
import re

GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'


def custom_client(auth):
    # Historical rclone enrollment explicitly wrote two blank client fields.
    # Those are still shared-client destinations, not incomplete custom clients.
    return ('handoff_version' in auth or
            any(auth.get(key) not in (None, '') for key in ('client_id', 'client_secret')))


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._~+/=-]{1,8192}', value) or value == 'None':
        raise ValueError('Invalid Drive credentials')
    return value


def drive_credentials(auth, force_refresh=False):
    """Return credentials and a new auth record; never mutate a failed caller record.

    Legacy records keep their existing shared-client refresh endpoint. New records
    must refresh with their own client; they can never fall back to that endpoint.
    """
    from google.oauth2.credentials import Credentials
    result = copy.deepcopy(auth)
    try:
        token = _token(result['token'])
        refresh = _token(result['refresh_token'])
        if custom_client(result):
            if type(result.get('handoff_version')) is not int or result['handoff_version'] != 2 or result.get('token_uri') != GOOGLE_TOKEN_URI:
                raise ValueError()
            client_id = result['client_id']
            secret = result['client_secret']
            if (not isinstance(client_id, str) or
                    not re.fullmatch(r'[A-Za-z0-9_.-]{1,256}\.apps\.googleusercontent\.com', client_id) or
                    not isinstance(secret, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{1,512}', secret)):
                raise ValueError()
            expiry = datetime.fromisoformat(result['expiry'].replace('Z', '+00:00'))
            if expiry.tzinfo is None:
                raise ValueError()
            credentials = Credentials(token, refresh_token=refresh, token_uri=GOOGLE_TOKEN_URI,
                                      client_id=client_id, client_secret=secret, scopes=result['scopes'],
                                      expiry=expiry.astimezone(timezone.utc).replace(tzinfo=None))
            if force_refresh or credentials.expired:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                result['token'] = _token(credentials.token)
                result['refresh_token'] = _token(credentials.refresh_token)
                if not credentials.expiry or credentials.expiry <= datetime.utcnow():
                    raise ValueError()
                result['expiry'] = credentials.expiry.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        else:
            if force_refresh:
                result['token'] = legacy_access_token(refresh)
            credentials = Credentials(result['token'], refresh, result['token_uri'], None, None, result['scopes'])
        return credentials, result
    except Exception:
        # Do not surface network exception strings: they can include credentials.
        raise ValueError('Google Drive authorization failed') from None


def legacy_access_token(refresh_token):
    import requests
    try:
        response = requests.post('https://platform.cyberpersons.com/refreshToken',
                                 data=json.dumps({'refresh_token': _token(refresh_token)}), timeout=30)
        response.raise_for_status()
        return _token(response.json()['access_token'])
    except Exception:
        raise ValueError('Google Drive authorization failed') from None


def update_legacy_remote_as_user(domain, username, remote, access_token, refresh_token):
    """Privilege boundary: secrets travel only through stdin to the website user."""
    import pwd
    import subprocess
    import sys
    from pathlib import Path
    if (not isinstance(domain, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,253}', domain) or
            not isinstance(username, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', username)):
        raise ValueError('Invalid website owner')
    owner = pwd.getpwnam(username)
    if owner.pw_uid == 0 or owner.pw_dir != '/home/' + domain:
        raise ValueError('Invalid website owner')
    result = subprocess.run(
        ['sudo', '-n', '-u', username, sys.executable, str(Path(__file__).resolve()), '--home', owner.pw_dir],
        input=json.dumps({'remote': remote, 'access_token': _token(access_token),
                          'refresh_token': _token(refresh_token)}).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
    if result.returncode:
        raise ValueError('Google Drive destination was not updated')


def update_legacy_remote(config_path, remote, access_token, refresh_token, expected_uid):
    """Replace only a legacy remote's token line, preserving every unrelated byte."""
    import configparser
    import fcntl
    import os
    from pathlib import Path
    import stat
    import tempfile
    if os.geteuid() == 0 or os.geteuid() != expected_uid:
        raise ValueError('Drive configuration must be updated as its unprivileged owner')
    access_token, refresh_token = _token(access_token), _token(refresh_token)
    # Existing remotes may have spaces or dots; no command is constructed from
    # this name, so do not impose the stricter new-enrollment naming policy.
    if not isinstance(remote, str) or not re.fullmatch(r'[^\r\n\[\]]{1,1024}', remote) or remote != remote.strip():
        raise ValueError('Invalid Drive destination')
    path = Path(config_path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe Drive configuration')
    if path.parent.stat().st_mode & 0o022:
        raise ValueError('Unsafe Drive configuration')
    lock = os.open(str(path.parent / '.gdrive-oauth.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    temporary = None
    try:
        lock_info = os.fstat(lock)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1 or lock_info.st_uid != expected_uid or lock_info.st_mode & 0o077:
            raise ValueError('Unsafe Drive lock')
        fcntl.flock(lock, fcntl.LOCK_EX)
        descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != expected_uid or info.st_size > 4 * 1024 * 1024:
                raise ValueError('Unsafe Drive configuration')
            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                old = source.read(4 * 1024 * 1024 + 1)
        finally:
            os.close(descriptor)
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.read_string(old.decode('utf-8'))
        values = dict(parser[remote])
        if values.get('type') != 'drive' or custom_client(values):
            raise ValueError('Not a legacy Drive destination')
        prior = json.loads(values['token'])
        if prior.get('refresh_token') != refresh_token:
            raise ValueError('Drive credentials changed concurrently')
        # Shared-client endpoint returns no expiry. Keep the previous conservative
        # immediate-refresh behavior, but use a real timestamp, never a fixed date.
        new_token = dict(prior, access_token=access_token, token_type='Bearer',
                         expiry=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'))
        lines = old.decode('utf-8').splitlines(keepends=True)
        section, replaced = None, 0
        for index, line in enumerate(lines):
            header = re.fullmatch(r'\s*\[([^\]]+)\]\s*(?:[;#].*)?(?:\r?\n)?', line)
            if header:
                section = header.group(1)
            if section == remote and re.match(r'^\s*token\s*=', line):
                newline = '\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
                lines[index] = line[:line.index('=') + 1] + ' ' + json.dumps(new_token, separators=(',', ':')) + newline
                replaced += 1
        if replaced != 1:
            raise ValueError('Ambiguous Drive configuration')
        descriptor, temporary = tempfile.mkstemp(prefix='.gdrive-refresh-', dir=str(path.parent))
        with os.fdopen(descriptor, 'wb') as output:
            os.fchmod(output.fileno(), stat.S_IMODE(info.st_mode))
            if os.fstat(output.fileno()).st_gid != info.st_gid:
                os.fchown(output.fileno(), -1, info.st_gid)
            output.write(''.join(lines).encode('utf-8'))
            output.flush()
            os.fsync(output.fileno())
        # Native rclone does not take our enrollment/refresh lock. Detect edits
        # made since the read, including an atomic replacement with equal bytes.
        # This is not a filesystem compare-and-swap: operators must still
        # serialize enrollment/configuration edits with active rclone processes.
        current_fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            current_info = os.fstat(current_fd)
            fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                         value.st_mtime_ns, value.st_ctime_ns)
            if not stat.S_ISREG(current_info.st_mode) or fingerprint(current_info) != fingerprint(info):
                raise ValueError('Drive configuration changed concurrently')
            with os.fdopen(current_fd, 'rb', closefd=False) as current:
                if current.read(4 * 1024 * 1024 + 1) != old:
                    raise ValueError('Drive configuration changed concurrently')
            # Catch replacements of the path while its old descriptor was read.
            if fingerprint(path.lstat()) != fingerprint(info):
                raise ValueError('Drive configuration changed concurrently')
        finally:
            os.close(current_fd)
        os.replace(temporary, path)
        temporary = None
        directory = os.open(str(path.parent), os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary:
            os.unlink(temporary)
        os.close(lock)


def main():
    import argparse
    import os
    from pathlib import Path
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    args = parser.parse_args()
    try:
        if os.geteuid() == 0:
            raise ValueError()
        data = json.loads(sys.stdin.buffer.read(32769))
        home = Path(args.home)
        if not home.is_absolute() or home.stat().st_uid != os.geteuid():
            raise ValueError()
        update_legacy_remote(str(home / '.config/rclone/rclone.conf'), data['remote'],
                             data['access_token'], data['refresh_token'], os.geteuid())
    except Exception:
        print('Google Drive destination was not updated.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
