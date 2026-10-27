"""Provision the fixed Google Drive privilege boundary during root install/upgrade.

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
HELPER = Path('/usr/local/CyberCP/plogical/gdriveConfig.py')
SUDOERS = Path('/etc/sudoers')
DIRECTORY = Path('/etc/sudoers.d')
TARGET = DIRECTORY / 'cyberpanel-gdrive'
VISUDO = Path('/usr/sbin/visudo')
MARKER = '# Managed by CyberPanel: isolated Google Drive management.\n'


def policy():
    commands = '%s -I -S %s' % (PYTHON, HELPER)
    return (MARKER + 'Cmnd_Alias CYBERPANEL_GDRIVE = ' + commands + '\n'
            'Defaults!CYBERPANEL_GDRIVE env_reset, !setenv, '
            'secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
            'lscpd ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_GDRIVE\n'
            'cyberpanel ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_GDRIVE\n')


def trusted_path(path):
    """Check lexical and resolved ancestry, including symlink owners/targets."""
    pending = [Path(path)]
    checked = set()
    while pending:
        current = pending.pop()
        if not current.is_absolute():
            raise RuntimeError('Fixed sudo policy paths must be absolute.')
        if current in checked:
            continue
        checked.add(current)
        if len(checked) > 256:
            raise RuntimeError('Fixed sudo policy path has too many symlink components.')
        info = current.lstat()
        if info.st_uid != 0 or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
            raise RuntimeError('Fixed sudo policy requires root-owned, non-writable paths: %s' % current)
        if stat.S_ISLNK(info.st_mode):
            current.resolve(strict=True)  # Reject dangling links and loops.
            target = Path(os.readlink(current))
            pending.append(target if target.is_absolute() else current.parent / target)
        if current.parent != current:
            pending.append(current.parent)


def provision():
    return provision_fixed(PYTHON, HELPER, TARGET, policy())


def provision_fixed(python, helper, target, content):
    """Install one exact root-authored policy after checking the entire trust chain."""
    PYTHON, HELPER, TARGET = Path(python), Path(helper), Path(target)
    if TARGET.parent != DIRECTORY or not re.fullmatch(r'[A-Za-z0-9_-]+', TARGET.name):
        raise RuntimeError('Fixed sudo policy must use an active /etc/sudoers.d filename.')
    if os.geteuid() != 0:
        raise RuntimeError('Fixed sudo policy must be provisioned as root.')
    for path in (PYTHON, HELPER, VISUDO, SUDOERS):
        trusted_path(path)
        if not path.is_file():
            raise RuntimeError('Missing regular fixed sudo policy dependency: %s' % path)
    for path in (PYTHON, VISUDO):
        if not os.access(path, os.X_OK):
            raise RuntimeError('fixed sudo policy dependency is not executable: %s' % path)
    # Do not silently install an ineffective rule or modify unrelated sudo policy.
    if not re.search(r'^\s*(?:@|#)includedir\s+["\']?/etc/sudoers\.d["\']?\s*(?:#.*)?$',
                     SUDOERS.read_text(), re.MULTILINE):
        raise RuntimeError('Enable /etc/sudoers.d in the server sudoers policy before provisioning a fixed helper.')
    trusted_path(DIRECTORY.parent)
    DIRECTORY.mkdir(mode=0o755, exist_ok=True)
    trusted_path(DIRECTORY)
    if not DIRECTORY.is_dir() or DIRECTORY.is_symlink():
        raise RuntimeError('Fixed helper sudoers directory must be a real directory.')
    if TARGET.exists() or TARGET.is_symlink():
        trusted_path(TARGET)
        if TARGET.is_symlink() or not TARGET.is_file():
            raise RuntimeError('Fixed helper sudoers policy must be a regular file.')
        existing = TARGET.read_text()
        if existing != content:
            raise RuntimeError('Existing Fixed helper sudoers policy is unmanaged; review it before provisioning.')
    subprocess.run([str(VISUDO), '-c'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    descriptor, temporary = tempfile.mkstemp(prefix='.cyberpanel-gdrive-', dir=str(DIRECTORY))
    backup = None
    try:
        with os.fdopen(descriptor, 'w') as stream:
            os.fchown(stream.fileno(), 0, 0)
            os.fchmod(stream.fileno(), 0o440)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        subprocess.run([str(VISUDO), '-cf', temporary], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if TARGET.exists():
            backup_fd, backup = tempfile.mkstemp(prefix='.gdrive-policy-backup-', dir=str(DIRECTORY))
            os.close(backup_fd)
            os.unlink(backup)
            os.link(TARGET, backup)
        os.replace(temporary, TARGET)
        try:
            # Validate in the complete policy too: aliases may conflict with
            # another include even when this candidate is valid by itself.
            subprocess.run([str(VISUDO), '-c'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        except BaseException:
            if backup is not None:
                os.replace(backup, TARGET)
            else:
                TARGET.unlink()
            raise
    finally:
        if backup is not None and os.path.exists(backup):
            os.unlink(backup)
        if os.path.exists(temporary):
            os.unlink(temporary)
