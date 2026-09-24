"""Provision the fixed Roundcube privilege boundary during root install/upgrade.

This module is never called by the web process. It grants no general Python or
shell access and does not modify the server's main sudoers policy.
"""
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

PYTHON = Path('/usr/local/CyberPanel/bin/python')
HELPER = Path('/usr/local/CyberCP/plogical/roundcubeRuntime.py')
SUDOERS = Path('/etc/sudoers')
DIRECTORY = Path('/etc/sudoers.d')
TARGET = DIRECTORY / 'cyberpanel-roundcube'
VISUDO = Path('/usr/sbin/visudo')
MARKER = '# Managed by CyberPanel: isolated Roundcube management.\n'


def policy():
    return MARKER + ''.join(
        'cyberpanel,lscpd ALL=(root) NOPASSWD: %s -I -S %s %s\n' % (PYTHON, HELPER, action)
        for action in ('install', 'enable', 'disable')
    )


def matching_legacy_policy(content):
    """Adopt only the same narrowly scoped grant, never arbitrary sudo syntax."""
    commands = {'%s -I -S %s %s' % (PYTHON, HELPER, action)
                for action in ('install', 'enable', 'disable')}
    grants = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([a-z, ]+)\s+ALL\s*=\s*\(root\)\s+NOPASSWD:\s*(.+)', line)
        if not match:
            return False
        users = {user.strip() for user in match[1].split(',')}
        allowed = {command.strip() for command in match[2].split(',')}
        if not users or not users <= {'cyberpanel', 'lscpd'} or not allowed <= commands:
            return False
        grants.update((user, command) for user in users for command in allowed)
    return grants == {(user, command) for user in ('cyberpanel', 'lscpd') for command in commands}


def trusted_path(path):
    """Check lexical and resolved ancestry, including symlink owners/targets."""
    pending = [Path(path)]
    checked = set()
    while pending:
        current = pending.pop()
        if not current.is_absolute():
            raise RuntimeError('Roundcube policy paths must be absolute.')
        if current in checked:
            continue
        checked.add(current)
        if len(checked) > 256:
            raise RuntimeError('Roundcube policy path has too many symlink components.')
        info = current.lstat()
        if info.st_uid != 0 or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
            raise RuntimeError('Roundcube policy requires root-owned, non-writable paths: %s' % current)
        if stat.S_ISLNK(info.st_mode):
            current.resolve(strict=True)  # Reject dangling links and loops.
            target = Path(os.readlink(current))
            pending.append(target if target.is_absolute() else current.parent / target)
        if current.parent != current:
            pending.append(current.parent)


def provision():
    if os.geteuid() != 0:
        raise RuntimeError('Roundcube sudo policy must be provisioned as root.')
    for path in (PYTHON, HELPER, VISUDO, SUDOERS):
        trusted_path(path)
        if not path.is_file():
            raise RuntimeError('Missing regular Roundcube policy dependency: %s' % path)
    for path in (PYTHON, VISUDO):
        if not os.access(path, os.X_OK):
            raise RuntimeError('Roundcube policy dependency is not executable: %s' % path)
    # Do not silently install an ineffective rule or modify unrelated sudo policy.
    if not re.search(r'^\s*(?:@|#)includedir\s+["\']?/etc/sudoers\.d["\']?\s*(?:#.*)?$',
                     SUDOERS.read_text(), re.MULTILINE):
        raise RuntimeError('Enable /etc/sudoers.d in the server sudoers policy before provisioning Roundcube.')
    trusted_path(DIRECTORY.parent)
    DIRECTORY.mkdir(mode=0o755, exist_ok=True)
    trusted_path(DIRECTORY)
    if not DIRECTORY.is_dir() or DIRECTORY.is_symlink():
        raise RuntimeError('Roundcube sudoers directory must be a real directory.')
    content = policy()
    if TARGET.exists() or TARGET.is_symlink():
        trusted_path(TARGET)
        if TARGET.is_symlink() or not TARGET.is_file():
            raise RuntimeError('Roundcube sudoers policy must be a regular file.')
        existing = TARGET.read_text()
        if not existing.startswith(MARKER) and not matching_legacy_policy(existing):
            raise RuntimeError('Existing Roundcube sudoers policy is unmanaged; review it before provisioning.')
    subprocess.run([str(VISUDO), '-c'], check=True, capture_output=True, timeout=30)
    descriptor, temporary = tempfile.mkstemp(prefix='.cyberpanel-roundcube-', dir=str(DIRECTORY))
    try:
        with os.fdopen(descriptor, 'w') as stream:
            os.fchown(stream.fileno(), 0, 0)
            os.fchmod(stream.fileno(), 0o440)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        subprocess.run([str(VISUDO), '-cf', temporary], check=True, capture_output=True, timeout=30)
        os.replace(temporary, TARGET)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
