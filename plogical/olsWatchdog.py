"""Coordinate the CyberPanel OLS watchdog with an exclusively locked OLS upgrade."""
import fcntl
import hashlib
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import tempfile

LEGACY = '102339b7888b253d56eecf9b2e1aac7bfa15f8661c393c2324cb96fd77315634'
COOPERATIVE = 'b4aa22d3f13ee8c1f4b66274d9f961ab1a58bd6732e1ffa069653e822b7fb0c1'
SCRIPT = Path('/etc/cyberpanel/watchdog.sh')
ALIAS = Path('/usr/local/bin/watchdog')
SERVICES = ('lsws', 'web', 'litespeed', 'openlitespeed')
PROTOCOL = '--ols-lock-v1'
REFUSAL = 'Cannot verify the CyberPanel OLS watchdog. Leave OLS and its monitor unchanged and review the OLS watchdog process before retrying.'


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def process_fields(entry):
    return (entry / 'stat').read_text().rsplit(')', 1)[1].split()


def trusted_file(path):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid or info.st_mode & 0o022:
        raise RuntimeError(REFUSAL)
    return info


def inspect_watchdog(root, proc='/proc', allow_legacy=False):
    """Read script bytes from the executing Bash descriptor, never argv alone."""
    monitors = []
    for entry in Path(proc).iterdir():
        if not entry.name.isdigit():
            continue
        candidate = False
        try:
            args = [os.fsdecode(part) for part in (entry / 'cmdline').read_bytes().split(b'\0') if part]
            indexes = [i for i, arg in enumerate(args[:-1])
                       if Path(arg).name in ('watchdog', 'watchdog.sh') and
                       args[i + 1] in SERVICES + ('check', 'status', 'kill')]
            if not indexes:
                if any(arg in SERVICES for arg in args) and (entry / 'fd/255').is_symlink():
                    if os.readlink(str(entry / 'fd/255')).split(' (deleted)')[0] == str(SCRIPT):
                        raise RuntimeError(REFUSAL)
                continue
            candidate = True
            if indexes != [1] or len(args) < 3:
                raise RuntimeError(REFUSAL)
            if args[2] not in SERVICES:
                if args[2] in ('check', 'status', 'kill'):
                    raise RuntimeError('The CyberPanel watchdog is changing monitored services. Retry when it finishes.')
                continue
            pid = int(entry.name)
            fields = process_fields(entry)
            if fields[0] in ('X', 'Z'):
                continue
            if (args[1] not in (str(SCRIPT), str(ALIAS)) or
                    not os.path.samefile(str(entry / 'exe'), '/bin/bash') or
                    (entry / 'status').read_text().split('Uid:', 1)[1].splitlines()[0].split() != ['0'] * 4):
                raise RuntimeError(REFUSAL)
            fd = entry / 'fd/255'
            if os.readlink(str(fd)) not in (str(SCRIPT), str(SCRIPT) + ' (deleted)'):
                raise RuntimeError(REFUSAL)
            trusted_file(fd)
            digest = hash_file(fd)
            if len(args) == 3 and digest == LEGACY:
                if not allow_legacy:
                    raise RuntimeError('An active legacy CyberPanel OLS watchdog must be prepared before changing OLS.')
                kind = 'legacy'
            elif (digest == COOPERATIVE and args[3:4] == [PROTOCOL] and
                  (len(args) == 4 or (len(args) == 7 and all(a.isdigit() for a in args[4:])))):
                kind = 'cooperative'
            else:
                raise RuntimeError(REFUSAL)
            monitors.append((pid, fields[19], kind, int(fields[1]), args[2:]))
        except (FileNotFoundError, ProcessLookupError):
            # An exited PID is benign. Missing script/proc proof on a living
            # candidate is not.
            if candidate and entry.exists():
                raise RuntimeError(REFUSAL)
    parents = {record[0] for record in monitors if record[2] == 'cooperative'}
    monitors = [r for r in monitors if not (r[2] == 'cooperative' and r[3] in parents)]
    if (len(monitors) > 2 or len({r[2] for r in monitors}) != len(monitors) or
            (monitors and Path(root) != Path('/usr/local/lsws'))):
        raise RuntimeError(REFUSAL)
    return monitors


def check_watchdog(root, proc='/proc'):
    return inspect_watchdog(root, proc)


def atomic_script(data, original):
    if SCRIPT.is_symlink() or hash_file(SCRIPT) != original:
        raise RuntimeError(REFUSAL)
    before = trusted_file(SCRIPT)
    info = SCRIPT.parent.stat()
    if SCRIPT.parent.is_symlink() or info.st_uid or info.st_mode & 0o022:
        raise RuntimeError(REFUSAL)
    with tempfile.NamedTemporaryFile(dir=str(SCRIPT.parent), delete=False) as out:
        temp = Path(out.name)
        try:
            out.write(data)
            out.flush()
            os.fchown(out.fileno(), before.st_uid, before.st_gid)
            os.fchmod(out.fileno(), stat.S_IMODE(before.st_mode))
            os.fsync(out.fileno())
            current = SCRIPT.lstat()
            if (current.st_dev, current.st_ino, current.st_mode, current.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_mode, before.st_mtime_ns):
                raise RuntimeError(REFUSAL)
            os.replace(str(temp), str(SCRIPT))
        finally:
            if temp.exists():
                temp.unlink()


def manual_session(entry):
    candidates = []
    for line in (entry / 'cgroup').read_text().splitlines():
        hierarchy, controllers, path = line.split(':', 2)
        if (hierarchy == '0' and not controllers) or 'name=systemd' in controllers.split(','):
            candidates.append(path)
    if len(set(candidates)) != 1:
        return False
    path = candidates[0]
    parts = path.strip('/').split('/')
    return (path in ('/', '/init.scope') or
            (len(parts) == 3 and parts[0] == 'user.slice' and parts[1].startswith('user-') and
             parts[1].endswith('.slice') and parts[2].startswith('session-') and parts[2].endswith('.scope')))


def sleep_child(entry):
    args = (entry / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
    if args == [b'sleep', b'60']:
        return os.path.samefile(str(entry / 'exe'), '/bin/sleep')
    wrapper = Path('/usr/bin/sleep')
    coreutils = Path('/usr/bin/coreutils')
    if args != [b'/usr/bin/coreutils', b'--coreutils-prog-shebang=sleep', b'/usr/bin/sleep', b'60']:
        return False
    trusted_file(wrapper)
    trusted_file(coreutils)
    return (wrapper.read_bytes() == b'#!/usr/bin/coreutils --coreutils-prog-shebang=sleep\n' and
            os.path.samefile(str(entry / 'exe'), str(coreutils)))


def idle_legacy(record, proc):
    pid, ticks, _, ppid, _ = record
    entry = Path(proc) / str(pid)
    fields = process_fields(entry)
    if (fields[19] != ticks or fields[0] != 'S' or ppid != 1 or
            not manual_session(entry)):
        raise RuntimeError(REFUSAL)
    status = dict(line.split(':', 1) for line in (entry / 'status').read_text().splitlines() if ':' in line)
    if any(int(status[label].strip(), 16) & (1 << (signal.SIGTERM - 1)) for label in ('SigBlk', 'SigIgn', 'SigCgt')):
        raise RuntimeError('The OLS watchdog does not accept normal termination. Arrange a targeted watchdog maintenance window before upgrading.')
    children = (entry / ('task/%d/children' % pid)).read_text().split()
    if len(children) != 1:
        raise RuntimeError(REFUSAL)
    child = Path(proc) / children[0]
    if not sleep_child(child):
        raise RuntimeError(REFUSAL)
    return child, process_fields(child)[19]


def lock_identity(root, require_exclusive=False):
    directory = Path(root)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid or info.st_mode & 0o022:
        raise RuntimeError('Unverified OLS transaction lock directory')
    path = directory / '.ols-bundle-install.lock'
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        actual = os.fstat(fd)
        if (not stat.S_ISREG(actual.st_mode) or actual.st_uid or actual.st_mode & 0o022 or
                actual.st_nlink != 1 or (actual.st_dev, actual.st_ino) != (path.lstat().st_dev, path.lstat().st_ino)):
            raise RuntimeError('Unverified OLS transaction lock file')
        if require_exclusive:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise RuntimeError('The OLS watchdog handoff requires the exclusive OLS bundle lock')
        return actual.st_dev, actual.st_ino
    finally:
        os.close(fd)


def prepare_watchdog(root, running, proc='/proc', script=None):
    """Called under the installer's exclusive lock. Retire only an attested idle worker."""
    records = inspect_watchdog(root, proc, allow_legacy=True)
    if records and not running:
        raise RuntimeError('Stopped OLS has an active auto-start watchdog. Resolve its monitoring policy before upgrading.')
    if records:
        lock_identity(root, require_exclusive=True)
    legacy = next((r for r in records if r[2] == 'legacy'), None)
    if legacy is None:
        return
    if not (hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')):
        raise RuntimeError('This runtime lacks PID-safe watchdog handoff. Arrange a targeted OLS watchdog maintenance window before upgrading.')
    if not ALIAS.is_symlink() or ALIAS.resolve() != SCRIPT or SCRIPT.is_symlink():
        raise RuntimeError(REFUSAL)
    trusted_file(SCRIPT)
    if script is None:
        adjacent = Path(__file__).with_name('watchdog.sh')
        script = adjacent if adjacent.exists() else Path(__file__).resolve().parents[1] / 'CPScripts/watchdog.sh'
    data = Path(script).read_bytes()
    if hashlib.sha256(data).hexdigest() != COOPERATIVE:
        raise RuntimeError('Cannot verify the release OLS watchdog script')
    current = hash_file(SCRIPT)
    if current not in (LEGACY, COOPERATIVE):
        raise RuntimeError(REFUSAL)
    pidfd = os.pidfd_open(legacy[0])
    try:
        child = idle_legacy(legacy, proc)
        pending = next((r for r in records if r[2] == 'cooperative'), None)
        if pending and pending[4][2:4] != [str(legacy[0]), legacy[1]]:
            raise RuntimeError(REFUSAL)
        if current == LEGACY:
            atomic_script(data, LEGACY)
        if pending is None:
            reader, writer = os.pipe()
            try:
                successor = subprocess.Popen(['/bin/bash', str(SCRIPT), legacy[4][0], PROTOCOL,
                                              str(legacy[0]), legacy[1], str(writer)],
                                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             start_new_session=True, close_fds=True, pass_fds=(writer,),
                                             env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                                                  'HOME': '/root', 'LANG': 'C'})
            finally:
                os.close(writer)
            try:
                if not select.select([reader], [], [], 5)[0] or os.read(reader, 32) != b'ready\n':
                    raise RuntimeError('The successor OLS monitor did not acknowledge its handoff; old monitor retained')
            finally:
                os.close(reader)
            records = inspect_watchdog(root, proc, allow_legacy=True)
            pending = next((r for r in records if r[0] == successor.pid and r[2] == 'cooperative'), None)
            if pending is None:
                raise RuntimeError(REFUSAL)
        # The new monitor waits for exactly this old PID and start time.
        # It survives launcher exit and cannot enter check_service under our lock.
        if idle_legacy(legacy, proc) != child:
            raise RuntimeError(REFUSAL)
        signal.pidfd_send_signal(pidfd, signal.SIGTERM)
        if not select.select([pidfd], [], [], 5)[0]:
            raise RuntimeError('The old OLS monitor did not retire; OLS was not changed')
        # This exact sleep was still alive after the shell's exit; it could
        # never have returned to the legacy loop to launch another control call.
        sleep, started = child
        if process_fields(sleep)[19] != started or not sleep_child(sleep):
            raise RuntimeError('Could not prove the old monitor remained idle during retirement; OLS was not changed')
        monitors = check_watchdog(root, proc)
        if not any(r[:3] == pending[:3] for r in monitors):
            raise RuntimeError('Could not verify the successor OLS watchdog; OLS was not changed')
    finally:
        os.close(pidfd)
