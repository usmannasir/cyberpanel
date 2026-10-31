"""Recover only the public half of the existing One-Click Backup identity."""
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import uuid


class BackupKeyError(RuntimeError):
    pass


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _file(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, None
    except OSError:
        raise BackupKeyError('Backup key path is unsafe or unreadable; no keys were changed.')
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
        os.close(fd)
        raise BackupKeyError('Backup key must be an owned regular file; no keys were changed.')
    return fd, info


def _same(path, before):
    try:
        now = path.lstat()
    except FileNotFoundError:
        return before is None
    return before is not None and _identity(now) == _identity(before)


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _run_keygen(args, fd, runner):
    try:
        return runner(['ssh-keygen'] + args + ['-f', '/proc/self/fd/%s' % fd],
                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE, universal_newlines=True, timeout=10,
                      check=False, pass_fds=(fd,))
    except (OSError, subprocess.TimeoutExpired):
        raise BackupKeyError('Backup key validation could not complete; no keys were changed.')


def existing_backup_public_key(directory='/root/.ssh', runner=subprocess.run):
    """Never create, replace, chmod, or regenerate a private key.

    Run via the existing privileged process boundary. An absent/corrupt public
    file may be repaired from the existing unencrypted private key. A valid
    but different public key is refused, preserving an ambiguous identity.
    """
    directory = Path(directory)
    try:
        parent = directory.lstat()
    except OSError:
        raise BackupKeyError('Backup SSH directory is missing; no keys were created.')
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
        raise BackupKeyError('Backup SSH directory is unsafe; no keys were changed.')
    private, public = directory / 'cyberpanel', directory / 'cyberpanel.pub'
    lock_path = directory / '.cyberpanel-public-key.lock'
    try:
        lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError:
        raise BackupKeyError('Backup key repair lock is unsafe; no keys were changed.')
    private_fd = public_fd = None
    temporary = None
    try:
        lock_info = os.fstat(lock)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.geteuid() or lock_info.st_mode & 0o077 or lock_info.st_nlink != 1:
            raise BackupKeyError('Backup key repair lock is unsafe; no keys were changed.')
        deadline = time.monotonic() + 2
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise BackupKeyError('Backup key repair is busy; retry later.')
                time.sleep(0.025)
        private_fd, private_info = _file(private)
        if private_fd is None:
            raise BackupKeyError('Existing backup private key is missing. No key was generated; restore or configure the intended backup identity first.')
        if private_info.st_mode & 0o077:
            raise BackupKeyError('Backup private key permissions are unsafe; no keys were changed.')
        public_fd, public_info = _file(public)
        if public_info is not None and (public_info.st_size > 16384 or public_info.st_mode & 0o022):
            raise BackupKeyError('Backup public key file is unsafe; no keys were changed.')
        result = _run_keygen(['-y', '-P', ''], private_fd, runner)
        if result.returncode:
            raise BackupKeyError('Existing backup private key is invalid, encrypted, or unreadable. Non-interactive validation failed; no keys were changed.')
        parts = result.stdout.strip().split()
        # Match the platform CreateSFTPAccount validator without narrowing an
        # existing supported identity to the installer's RSA default.
        accepted_types = ('ssh-rsa', 'ssh-ed25519', 'ssh-dss',
                          'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384',
                          'ecdsa-sha2-nistp521', 'sk-ssh-ed25519@openssh.com',
                          'sk-ecdsa-sha2-nistp256@openssh.com')
        if len(parts) < 2 or parts[0] not in accepted_types:
            raise BackupKeyError('Existing backup key type is not supported by the platform; no keys were changed.')
        derived = ' '.join(parts[:2])
        original = os.read(public_fd, 16385) if public_fd is not None else None
        def identity_unchanged():
            # Parent timestamps change when our lock/temp/backup is created;
            # its identity and permissions, not those timestamps, are pinned.
            current_parent = directory.lstat()
            return ((current_parent.st_dev, current_parent.st_ino, current_parent.st_mode, current_parent.st_uid) ==
                    (parent.st_dev, parent.st_ino, parent.st_mode, parent.st_uid)
                    and _same(private, private_info)
                    and (lock_path.lstat().st_dev, lock_path.lstat().st_ino) == (lock_info.st_dev, lock_info.st_ino))
        def unchanged():
            return identity_unchanged() and _same(public, public_info)
        if not unchanged():
            raise BackupKeyError('Backup key paths changed during validation; no keys were changed.')
        if original is not None:
            existing = original.decode('utf-8', 'replace').strip().split()
            if existing[:2] == parts[:2] and len(original.decode('utf-8', 'replace').strip().splitlines()) == 1:
                return {'status': 1, 'public_key': derived, 'repaired': False}
            os.lseek(public_fd, 0, os.SEEK_SET)
            check = _run_keygen(['-l'], public_fd, runner)
            if check.returncode == 0:
                raise BackupKeyError('Backup public and private keys do not match. Review the intended identity; no keys were changed.')
        fd, name = tempfile.mkstemp(prefix='.cyberpanel-pub-', dir=directory)
        temporary = Path(name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write((derived + '\n').encode('ascii'))
            stream.flush(); os.fsync(stream.fileno())
            published_info = os.fstat(stream.fileno())
        if not unchanged():
            raise BackupKeyError('Backup key paths changed before publication; no keys were changed.')
        if original is not None:
            backup = directory / ('.cyberpanel.pub.before-repair-' + uuid.uuid4().hex)
            bfd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(bfd, 'wb') as stream:
                stream.write(original); stream.flush(); os.fsync(stream.fileno())
            _sync_directory(directory)
            if not unchanged():
                raise BackupKeyError('Backup key paths changed before publication; no keys were changed.')
            os.replace(temporary, public)
            temporary = None
        else:
            os.link(temporary, public, follow_symlinks=False)
            temporary.unlink(); temporary = None
        _sync_directory(directory)
        # A non-cooperating owner can rotate paths despite our lock. Refuse
        # deployment if observable drift occurs; never undo a foreign change.
        current_public = public.lstat()
        published_fields = lambda info: (info.st_dev, info.st_ino, info.st_mode,
                                        info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns)
        if (not identity_unchanged() or current_public.st_nlink != 1
                or published_fields(current_public) != published_fields(published_info)):
            raise BackupKeyError('Backup key paths changed after public-key publication. Deployment stopped; inspect the key files before retrying. No private key was changed.')
        return {'status': 1, 'public_key': derived, 'repaired': True}
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        if private_fd is not None:
            os.close(private_fd)
        if public_fd is not None:
            os.close(public_fd)
        os.close(lock)


if __name__ == '__main__':
    try:
        print(json.dumps(existing_backup_public_key()))
    except BackupKeyError as exc:
        print(json.dumps({'status': 0, 'error_message': str(exc)}))
    except Exception:
        print(json.dumps({'status': 0, 'error_message': 'Backup public key repair failed. No private key was changed; inspect the key files before retrying.'}))
