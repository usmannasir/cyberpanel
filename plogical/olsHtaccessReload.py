"""Reload OLS once per observed .htaccess snapshot, with private durable state."""
import fcntl
import os
import json
import stat
import subprocess
import sys

STATE = '/var/lib/cyberpanel/ols-htaccess'
OLS = '/usr/local/lsws/bin/openlitespeed'
CRON = '*/3 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/olsHtaccessReload.py'
LEGACY = "*/3 * * * * if ! find /home/*/public_html/ -maxdepth 2 -type f -newer /usr/local/lsws/cgid -name '.htaccess' -exec false {} +; then %s; fi"
LEGACY_COMMANDS = {'systemctl restart lsws', '/usr/local/lsws/bin/lswsctrl restart'}


def migrate_cron(data, is_ols):
    """Replace only exact stock active watchers; retain user comments/workarounds."""
    kept = []
    installed = False
    for line in data.splitlines(keepends=True):
        value = line.strip()
        recognized = value == CRON or value in {LEGACY % cmd for cmd in LEGACY_COMMANDS}
        if recognized:
            if is_ols and not installed:
                kept.append(CRON + '\n')
                installed = True
        else:
            kept.append(line)
    result = ''.join(kept)
    if is_ols and not installed:
        result += ('' if not result or result.endswith('\n') else '\n') + CRON + '\n'
    return result


def merge_defaults(existing, defaults):
    """Install missing stock commands without replacing customized schedules."""
    commands = {line.split(None, 5)[5] for line in existing.splitlines()
                if line.strip() and not line.lstrip().startswith('#') and len(line.split(None, 5)) == 6}
    result = existing
    for line in defaults.splitlines():
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5] not in commands:
            result += ('' if not result or result.endswith('\n') else '\n') + line + '\n'
            commands.add(fields[5])
    return result


def snapshot_rules(home):
    # Same maximum depth as the stock find: files at public_html and one level below.
    snapshot = {}
    def scan(path, depth):
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.name == '.htaccess' and entry.is_file(follow_symlinks=False):
                    info = entry.stat(follow_symlinks=False)
                    # Signatures distinguish later edits even when mtimes are preserved,
                    # restored from an archive, or ahead of the system clock.
                    snapshot[entry.path] = [info.st_dev, info.st_ino, info.st_size,
                                           info.st_mtime_ns, info.st_ctime_ns]
                elif depth and entry.is_dir(follow_symlinks=False):
                    scan(entry.path, depth - 1)
    with os.scandir(home) as sites:
        for site in sites:
            if site.is_dir(follow_symlinks=False):
                path = os.path.join(site.path, 'public_html')
                try:
                    info = os.lstat(path)
                except FileNotFoundError:
                    continue
                if stat.S_ISDIR(info.st_mode):
                    scan(path, 1)
    return snapshot


def run(state=STATE, home='/home', reload=None):
    os.makedirs(state, mode=0o700, exist_ok=True)
    info = os.lstat(state)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError('Unsafe OLS reload state directory')
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
    fd = os.open(os.path.join(state, 'lock'), flags, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise RuntimeError('Unsafe OLS reload lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'busy'
        stamp = os.path.join(state, 'snapshot.json')
        try:
            with os.fdopen(os.open(stamp, os.O_RDONLY | os.O_NOFOLLOW)) as stream:
                previous = json.load(stream)
        except FileNotFoundError:
            previous = {}
        observed = snapshot_rules(home)  # Capture before reload; subsequent edits remain pending.
        if observed == previous:
            return 'unchanged'
        if reload is None:
            reload = lambda: subprocess.run(['/usr/local/lsws/bin/lswsctrl', 'restart'], check=True)
        reload()  # Failure leaves the previous snapshot intact for retry.
        temporary = os.path.join(state, 'snapshot.new')
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(observed, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, stamp)
        return 'reloaded'


if __name__ == '__main__':
    try:
        if os.geteuid() != 0:
            raise RuntimeError('OLS reload watcher requires root')
        if os.path.isfile(OLS):
            run()
    except Exception as error:
        print('OLS htaccess watcher failed: %s' % error, file=sys.stderr)
        sys.exit(1)
