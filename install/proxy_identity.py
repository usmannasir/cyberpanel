"""Provision private PHP-to-panel peer keys before source activation."""
import argparse
import grp
import json
import hmac
import os
import re
import secrets
import shutil
import stat
import sys
import tempfile

PMA_PEER_KEY = '/etc/cyberpanel/pmaPeerKey'
PMA_PHP_PEER_KEY = '/etc/cyberpanel/pmaPeerKeyPHP'


def _ensure(path, group, expected=None):
    gid = grp.getgrnam(group).gr_gid
    created = False
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = True
    except FileExistsError:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1:
            raise RuntimeError('Unsafe phpMyAdmin peer-key file; refusing activation')
        if created:
            value = expected or secrets.token_hex(32).encode('ascii')
            if os.write(fd, value) != len(value):
                raise RuntimeError('Incomplete phpMyAdmin peer-key write')
            os.fsync(fd)
        else:
            value = os.read(fd, 65)
            if not re.fullmatch(b'[a-f0-9]{64}', value) or info.st_mode & 0o027:
                raise RuntimeError('Invalid or exposed phpMyAdmin peer key; refusing activation')
            if expected is not None and not hmac.compare_digest(value, expected):
                raise RuntimeError('phpMyAdmin peer-key copies disagree; refusing activation')
        os.fchown(fd, 0, gid)
        os.fchmod(fd, 0o640)
    finally:
        os.close(fd)
    return value


def ensure_pma_peer_key(path=PMA_PEER_KEY, php_path=PMA_PHP_PEER_KEY,
                        group='cyberpanel', php_group='lscpd'):
    # Different service accounts get private copies; no new group memberships or
    # world-readable key. A retained key survives repeat upgrades and rollbacks.
    key = _ensure(path, group)
    _ensure(php_path, php_group, expected=key)


def _read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'r', encoding='utf-8') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise RuntimeError('phpMyAdmin staging requires regular source files')
        return source.read()


def _database_target(config_path):
    value = _read_regular(config_path).strip()
    if not value:
        raise RuntimeError('Empty database configuration; refusing activation')
    # Local installations retain a legacy plaintext root password. Remote
    # installations use a JSON object; never silently fall back for broken JSON.
    if not value.startswith(('{', '[')):
        return 'localhost', 3306
    try:
        config = json.loads(value)
        if not isinstance(config, dict) or not isinstance(config.get('mysqlhost'), str):
            raise ValueError()
        return config['mysqlhost'], config['mysqlport']
    except (ValueError, KeyError, TypeError):
        raise RuntimeError('Malformed remote database configuration; refusing activation') from None


def _staged_pma_directory(staged_root):
    root = os.path.abspath(staged_root)
    # The cloned staging tree is private to root. Reject links at every relevant
    # component so helper replacement can never write into the live installation.
    for directory in (root, os.path.join(root, 'public'),
                      os.path.join(root, 'public', 'phpmyadmin')):
        try:
            info = os.lstat(directory)
        except FileNotFoundError:
            if directory == root:
                raise
            return None
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('Unsafe phpMyAdmin staging directory; refusing activation')
    return os.path.join(root, 'public', 'phpmyadmin')


def _replace_helper(destination, content, gid):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                dir=os.path.dirname(destination), prefix='.pma-peer-', delete=False) as output:
            temporary = output.name
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
            os.fchown(output.fileno(), 0, gid)
            os.fchmod(output.fileno(), 0o640)
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def _copy_pma_directory(source_fd, destination, top=True):
    """Copy a retained app through pinned descriptors, never following links."""
    source_info = os.fstat(source_fd)
    os.makedirs(destination, mode=0o700, exist_ok=True)
    if not stat.S_ISDIR(os.lstat(destination).st_mode):
        raise RuntimeError('Unsafe retained phpMyAdmin destination')
    with os.scandir(source_fd) as entries:
        retained_entries = list(entries)
    for entry in retained_entries:
        if top and entry.name in ('phpmyadminsignin.php', 'phpmyadminsession.php'):
            continue  # Always use the new release's auth code, never the old copy.
        descriptor = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=source_fd)
        try:
            info = os.fstat(descriptor)
            target = os.path.join(destination, entry.name)
            if stat.S_ISDIR(info.st_mode):
                _copy_pma_directory(descriptor, target, top=False)
            elif stat.S_ISREG(info.st_mode):
                temporary = None
                try:
                    with os.fdopen(os.dup(descriptor), 'rb') as original:
                        with tempfile.NamedTemporaryFile(dir=destination,
                                prefix='.pma-retain-', delete=False) as output:
                            temporary = output.name
                            shutil.copyfileobj(original, output)
                            output.flush()
                            os.fsync(output.fileno())
                            os.fchown(output.fileno(), info.st_uid, info.st_gid)
                            os.fchmod(output.fileno(), stat.S_IMODE(info.st_mode) & 0o777)
                    os.replace(temporary, target)
                    temporary = None
                finally:
                    if temporary is not None:
                        os.unlink(temporary)
            else:
                raise RuntimeError('Unsupported retained phpMyAdmin file type')
        finally:
            os.close(descriptor)
    os.chown(destination, source_info.st_uid, source_info.st_gid, follow_symlinks=False)
    os.chmod(destination, stat.S_IMODE(source_info.st_mode) & 0o777)


def _preserve_phpmyadmin(current_root, staged_root):
    current_root, staged_root = os.path.abspath(current_root), os.path.abspath(staged_root)
    if os.path.commonpath((current_root, staged_root)) in (current_root, staged_root):
        raise RuntimeError('Current and staged source trees must be separate')
    current = _staged_pma_directory(current_root)
    staged = _staged_pma_directory(staged_root)
    if current is None:
        if staged is not None and not os.path.isfile(os.path.join(staged, 'index.php')):
            raise RuntimeError('Retained phpMyAdmin application is missing')
        return
    descriptor = os.open(current, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        index = os.open('index.php', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            if not stat.S_ISREG(os.fstat(index).st_mode):
                raise RuntimeError('Retained phpMyAdmin entry point is not a regular file')
        finally:
            os.close(index)
        _copy_pma_directory(descriptor, os.path.join(staged_root, 'public', 'phpmyadmin'))
    finally:
        os.close(descriptor)


def prepare_staged_phpmyadmin(staged_root, config_path='/etc/cyberpanel/mysqlPassword',
                             path=PMA_PEER_KEY, php_path=PMA_PHP_PEER_KEY,
                             group='cyberpanel', php_group='lscpd', current_root=None):
    """Prepare the coupled verifier/signer before the caller activates source.

    Existing phpMyAdmin config is retained by the upgrade's state copier. When
    present, refresh both PHP auth helpers from the new source, never from the
    old public signer. All errors propagate so activate_source is not entered.
    """
    if current_root is not None:
        _preserve_phpmyadmin(current_root, staged_root)
    directory = _staged_pma_directory(staged_root)
    helpers = []
    if directory is not None:
        from install.database_consumers import render_phpmyadmin_signon
        host, port = _database_target(config_path)
        source_dir = os.path.join(os.path.abspath(staged_root), 'plogical')
        if not stat.S_ISDIR(os.lstat(source_dir).st_mode):
            raise RuntimeError('Unsafe phpMyAdmin source directory; refusing activation')
        for name in ('phpmyadminsignin.php', 'phpmyadminsession.php'):
            content = _read_regular(os.path.join(source_dir, name))
            if not content.strip():
                raise RuntimeError('Empty phpMyAdmin source helper; refusing activation')
            if name == 'phpmyadminsignin.php':
                content = render_phpmyadmin_signon(content, host, port)
            helpers.append((os.path.join(directory, name), content))
    ensure_pma_peer_key(path, php_path, group, php_group)
    gid = grp.getgrnam(php_group).gr_gid
    for destination, content in helpers:
        _replace_helper(destination, content, gid)
    return bool(helpers)


if __name__ == '__main__':
    # Executed directly from staged/install before that tree becomes importable.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-root')
    parser.add_argument('--current-root')
    arguments = parser.parse_args()
    if arguments.staged_root:
        if not arguments.current_root:
            parser.error('--current-root is required with --staged-root')
        prepare_staged_phpmyadmin(arguments.staged_root, current_root=arguments.current_root)
    else:
        ensure_pma_peer_key()
