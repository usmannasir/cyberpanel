"""Identify and control only the verified OpenLiteSpeed installation during an upgrade."""
import hashlib
import importlib.util
import locale
import os
from pathlib import Path
import re
import stat
import subprocess
import time


_watchdog_spec = importlib.util.spec_from_file_location('olsWatchdog', str(Path(__file__).with_name('olsWatchdog.py')))
watchdog = importlib.util.module_from_spec(_watchdog_spec)
_watchdog_spec.loader.exec_module(watchdog)


CONTROLLER_HASHES = {
    'cacef63b88f0eb0f95b82259c311dfe9b5ff08760f50ff30342dc6615246a114',
    '5af78d0aede6c139f030210e1c080575a742789ed0110fa112357eecd1e27f67',
}
ENV_HASH = '1851443bf9fa883d94967751e705611d5a630bfb0f5bf05553d73b6ed89edeb8'
UNIT_HASH = 'e1a05ef5fbaba9b5eed156ac77fe4b91019cd0e433bfefd46cdfa02af78b199d'
VENDOR_UNITS = {'lsws.service', 'lshttpd.service', 'openlitespeed.service'}


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def original_record(backup):
    backup = Path(backup)
    if not os.path.lexists(str(backup)):
        return None
    info = backup.lstat()
    record = {'uid': info.st_uid, 'gid': info.st_gid}
    if stat.S_ISLNK(info.st_mode):
        record['link'] = os.readlink(str(backup))
    elif stat.S_ISREG(info.st_mode):
        record['file'] = str(backup)
    else:
        raise RuntimeError('Nonregular OLS backup entry: ' + str(backup))
    return record


def verify_originals(records):
    for name, old in records.items():
        path = Path(name)
        if old is None:
            ok = not os.path.lexists(str(path))
        else:
            info = path.lstat()
            ok = (info.st_uid, info.st_gid) == (old['uid'], old['gid'])
            if 'link' in old:
                ok = ok and path.is_symlink() and os.readlink(str(path)) == old['link']
            else:
                backup = Path(old['file'])
                ok = (ok and stat.S_ISREG(info.st_mode) and info.st_mode == backup.stat().st_mode
                      and digest(path) == digest(backup))
        if not ok:
            raise RuntimeError('OLS entry differs from the rollback receipt: ' + str(path))


def attributes(path):
    info = os.lstat(str(path))
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError('Nonregular OLS release file: ' + str(path))
    return info.st_mode, info.st_uid, info.st_gid


def bundle_records(required, directory, hashes, assets):
    old = {entry['target']: assets._old[entry['path']] for entry in assets.entries}
    new = {entry['target']: (entry['sha256'], attributes(entry['staged'])) for entry in assets.entries}
    for kind, _, target, _, backup in required:
        old[target] = original_record(Path(directory) / backup)
        new[target] = hashes[kind], attributes(Path(directory) / (kind + '.new'))
    return old, new


def verify_installed(records):
    for name, (checksum, metadata) in records.items():
        path = Path(name)
        if attributes(path) != metadata or digest(path) != checksum:
            raise RuntimeError('Installed OLS release file failed verification: ' + str(path))


def process_owner(cgroup):
    owners = set()
    for line in cgroup.splitlines():
        fields = line.split(':', 2)
        if len(fields) != 3 or not fields[0].isdigit() or not fields[2].startswith('/'):
            raise RuntimeError('Cannot establish the OLS master control group')
        if not ((fields[0] == '0' and fields[1] == '') or 'name=systemd' in fields[1].split(',')):
            continue
        parts = Path(fields[2]).parts
        if '..' in parts:
            raise RuntimeError('Unresolved OLS master control group')
        units = [part for part in parts if part.endswith('.service')]
        owners.add(units[-1] if units else None)
    if len(owners) != 1:
        raise RuntimeError('Missing or conflicting OLS service ownership evidence')
    owner = owners.pop()
    if owner is not None and owner not in VENDOR_UNITS:
        raise RuntimeError('An unrecognized systemd service owns the OLS master: ' + owner)
    return owner


def run(args, timeout=30):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=timeout)


class OLSWorkersRemain(RuntimeError):
    """The controller no longer has a master PID but OLS processes still exist."""


class OLSService:
    def __init__(self, root='/usr/local/lsws', proc='/proc', unit=None):
        self.root = Path(root)
        self.proc = Path(proc)
        self.binary = self.root / 'bin/openlitespeed'
        self.control = self.root / 'bin/lswsctrl'
        if unit is not None and unit not in VENDOR_UNITS:
            raise RuntimeError('Unknown OLS manager in recovery receipt')
        self.unit = unit
        self.manager_identified = unit is not None
        self.draining = None
        self._observed_processes = {}
        self._draining_processes = {}
        self.watch_lock = None

    def controller(self):
        directory = self.root / 'bin'
        env = directory / 'lsws_env'
        if (self.root.is_symlink() or directory.is_symlink() or
                self.control.resolve().parent != directory or not self.control.is_file() or
                digest(self.control) not in CONTROLLER_HASHES or env.is_symlink() or
                not env.is_file() or digest(env) != ENV_HASH):
            raise RuntimeError('The OLS controller or its PID configuration cannot be verified')
        if (os.path.lexists(str(self.root / 'admin/tmp/.restart')) or
                os.path.lexists(str(directory / 'get_trial_key.sh')) or os.getenv('WSWATCH')):
            raise RuntimeError('An OLS restart marker, trial hook or watchdog is active')

    def verify_unit_claims(self, pid, owner):
        if not Path('/run/systemd/system').is_dir():
            return
        claims = set()
        for unit in sorted(VENDOR_UNITS):
            result = run(['systemctl', 'show', unit, '--property=Id,LoadState,ActiveState,MainPID'])
            values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            if values.get('LoadState') == 'not-found':
                continue
            if result.returncode or values.get('LoadState') != 'loaded':
                raise RuntimeError('Cannot classify OLS systemd unit ' + unit)
            if values.get('ActiveState') in ('inactive', 'failed') and values.get('MainPID') == '0':
                continue
            if (not pid or values.get('ActiveState') != 'active' or values.get('MainPID') != str(pid)
                    or values.get('Id') not in VENDOR_UNITS):
                raise RuntimeError('Conflicting OLS systemd manager or PID')
            claims.add(values['Id'])
        if claims != ({owner} if owner else set()):
            raise RuntimeError('OLS systemd unit and process control group disagree')

    def systemd(self, pid):
        if self.unit is None:
            return
        props = ('Id,FragmentPath,LoadState,ActiveState,MainPID,NeedDaemonReload,DropInPaths,'
                 'ExecStart,ExecStop,ExecReload,ExecStartPre,ExecStartPost,ExecStopPost,ExecCondition')
        result = run(['systemctl', 'show', self.unit, '--property=' + props])
        values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        path = Path(values.get('FragmentPath', ''))
        if (result.returncode or values.get('Id') != self.unit or values.get('LoadState') != 'loaded' or
                values.get('NeedDaemonReload') != 'no' or values.get('DropInPaths') != '' or
                not path.is_absolute() or not path.is_file() or digest(path) != UNIT_HASH or
                any(values.get(key) for key in ('ExecStartPre', 'ExecStartPost', 'ExecStopPost', 'ExecCondition'))):
            raise RuntimeError('Unverified OLS systemd unit, hook or drop-in: ' + self.unit)
        for prop, action in [('ExecStart', 'start'), ('ExecStop', 'delay-stop'), ('ExecReload', 'restart')]:
            value = values.get(prop, '')
            if (value.count('path=') != 1 or value.count('argv[]=') != 1 or
                    ('path=%s ;' % self.control) not in value or
                    ('argv[]=%s %s ;' % (self.control, action)) not in value):
                raise RuntimeError('Unexpected OLS systemd action: ' + prop)
        if values.get('MainPID') != str(pid or 0):
            raise RuntimeError('OLS systemd MainPID disagrees with its controller')
        if pid and values.get('ActiveState') != 'active':
            raise RuntimeError('OLS systemd unit is not established as active')
        if not pid and values.get('ActiveState') not in ('failed', 'inactive'):
            raise RuntimeError('OLS systemd unit is not established as stopped')

    def inspect_state(self, allow_legacy=True):
        if self.watch_lock is not None and watchdog.lock_identity(self.root) != self.watch_lock:
            raise RuntimeError('OLS watchdog transaction lock inode changed')
        monitors = watchdog.inspect_watchdog(self.root, self.proc, allow_legacy)
        state = self._native_state()
        if monitors and not state and allow_legacy:
            raise RuntimeError('Stopped OLS has an active auto-start watchdog. Resolve its monitoring policy before upgrading.')
        return state

    def prepare_state(self, script=None):
        initial = self.inspect_state()
        self.verify_mapped_bundle(initial)
        if watchdog.inspect_watchdog(self.root, self.proc, allow_legacy=True):
            self.watch_lock = watchdog.lock_identity(self.root, require_exclusive=True)
        watchdog.prepare_watchdog(self.root, bool(initial), self.proc, script)
        if self.state() != initial:
            raise RuntimeError('OLS changed state during watchdog handoff')
        return initial

    def state(self):
        return self.inspect_state(allow_legacy=False)

    def verified_draining_workers(self, processes):
        """Only wait for identities observed before our verified stop action."""
        if not self.draining or not self._draining_processes:
            return False
        for pid, (_, ticks) in processes.items():
            if self._draining_processes.get(pid) != ticks:
                return False
            try:
                owner = process_owner((self.proc / str(pid) / 'cgroup').read_text())
            except (FileNotFoundError, ProcessLookupError):
                continue  # Disappearance still requires a fresh empty snapshot.
            if owner != self.draining[2]:
                return False
        return True

    def _native_state(self):
        self.controller()
        result = run([str(self.control), 'status'])
        matched = re.findall(r'is running with PID ([1-9][0-9]*)\.', result.stdout)
        stopped = 'is not running.' in result.stdout
        if len(matched) != (0 if stopped else 1):
            raise RuntimeError('Cannot determine OpenLiteSpeed service state')
        master = int(matched[0]) if matched else None
        aliases = {str(self.root / 'bin' / name) for name in ('openlitespeed', 'litespeed', 'lshttpd')}
        processes = {}
        for entry in self.proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                name = (entry / 'comm').read_text().strip()
                if re.search(r'wswatch.sh', name):
                    raise RuntimeError('Vendor OLS control could terminate an active watchdog')
                executable = os.readlink(str(entry / 'exe'))
                same_binary = os.path.samefile(str(entry / 'exe'), str(self.binary))
                if not same_binary and ('litespeed' in name or executable.split(' (deleted)')[0] in aliases):
                    raise RuntimeError('A different or deleted LiteSpeed process is active')
                if same_binary:
                    fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                    processes[int(entry.name)] = (int(fields[1]), fields[19])
            except (FileNotFoundError, ProcessLookupError):
                continue
        if not master:
            if processes:
                if self.draining and not self.verified_draining_workers(processes):
                    raise RuntimeError('An unverified OLS process appeared during shutdown')
                raise OLSWorkersRemain('OLS status missed a running process')
            self.verify_unit_claims(None, None)
            self.systemd(None)
            self._observed_processes = {}
            return None
        if master not in processes:
            # kill -0 in the vendor script can still see a dead/zombie PID.
            try:
                master_fields = (self.proc / str(master) / 'stat').read_text().rsplit(')', 1)[1].split()
                dead = master_fields[0] in ('Z', 'X', 'x')
            except (FileNotFoundError, ProcessLookupError):
                master_fields = None
                dead = True
            if dead and not processes:
                self.verify_unit_claims(None, None)
                self.systemd(None)
                self._observed_processes = {}
                return None
            if (dead and self.draining and master == self.draining[0] and
                    (master_fields is None or master_fields[19] == self.draining[1]) and
                    self.verified_draining_workers(processes)):
                # The PID file may outlive the master while its known workers
                # finish exiting. This is a pending stop, never a stopped state.
                raise OLSWorkersRemain('Original OLS master exited while its verified workers drain')
            raise RuntimeError('OLS status PID does not identify the installed master '
                               '(reported=%s, live=%s, stopping=%s)' %
                               (master, sorted(processes), self.draining is not None))
        for pid in processes:
            seen = set()
            while pid != master:
                if pid in seen or pid not in processes:
                    raise RuntimeError('An unmanaged OLS process is also running')
                seen.add(pid)
                pid = processes[pid][0]
        owner = process_owner((self.proc / str(master) / 'cgroup').read_text())
        if self.draining is not None and (master, processes[master][1], owner) == self.draining:
            raise OLSWorkersRemain('Original OLS master is draining after its verified stop action')
        self.verify_unit_claims(master, owner)
        if self.manager_identified and owner != self.unit:
            raise RuntimeError('OLS changed its service manager')
        self.unit = owner
        self.manager_identified = True
        self.systemd(master)
        self._observed_processes = {pid: entry[1] for pid, entry in processes.items()}
        return master, processes[master][1], owner

    def settled_state(self):
        deadline = time.monotonic() + 20
        while True:
            try:
                return self.state()
            except OLSWorkersRemain:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)

    def verify_mapped_bundle(self, state):
        if not state:
            return
        checked = set()
        names = {str(self.root / 'modules' / name) for name in ('cyberpanel_ols.so', 'mod_security.so')}
        for line in (self.proc / str(state[0]) / 'maps').read_text().splitlines():
            fields = line.split(None, 5)
            if len(fields) != 6 or fields[5].split(' (deleted)')[0] not in names:
                continue
            path = Path(fields[5])
            if fields[5].endswith(' (deleted)') or not path.is_file():
                raise RuntimeError('Live OLS module differs from the installed bundle')
            identity = (fields[3], fields[4], fields[5])
            if identity not in checked:
                mapped = self.proc / str(state[0]) / 'map_files' / fields[0]
                if not os.path.samefile(str(mapped), str(path)) and digest(mapped) != digest(path):
                    raise RuntimeError('Live OLS module differs from the installed bundle')
                checked.add(identity)

    def change(self, action, expected):
        if action not in ('stop', 'start') or self.state() != expected:
            raise RuntimeError('OLS changed state before the ' + action + ' action')
        wanted_running = action == 'start'
        if bool(expected) == wanted_running:
            return expected
        self.verify_mapped_bundle(expected)
        observed = dict(self._observed_processes)
        command = ['systemctl', action, self.unit] if self.unit else [str(self.control), action]
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if result.returncode:
            raise RuntimeError('OpenLiteSpeed service %s failed' % action)
        self.draining = expected if action == 'stop' else None
        self._draining_processes = observed if action == 'stop' else {}
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                try:
                    state = self.state()
                except OLSWorkersRemain:
                    # Master PID removal can precede worker exit. A pending
                    # transition is never evidence that files may be replaced.
                    time.sleep(0.25)
                    continue
                if bool(state) == wanted_running:
                    if state:
                        time.sleep(1)
                        if self.state() != state:
                            raise RuntimeError('OLS master did not remain stable after startup')
                        self.verify_mapped_bundle(state)
                    return state
                time.sleep(1)
            raise RuntimeError('OpenLiteSpeed did not ' + action)
        finally:
            self.draining = None
            self._draining_processes = {}

    def reload(self, expected):
        if expected is None or self.state() != expected:
            raise RuntimeError('OLS changed state before configuration reload')
        self.verify_mapped_bundle(expected)
        command = ['systemctl', 'reload', self.unit] if self.unit else [str(self.control), 'reload']
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if result.returncode:
            raise RuntimeError('OpenLiteSpeed configuration reload failed')
        time.sleep(1)
        current = self.settled_state()
        if not current:
            raise RuntimeError('OpenLiteSpeed is unavailable after configuration reload')
        self.verify_mapped_bundle(current)


def replace_config(path, expected, content):
    """Replace only the version we read and retain ownership, mode and ACLs."""
    import shutil
    import tempfile
    if path != path.resolve() or not path.is_file() or path.read_bytes() != expected:
        raise RuntimeError('OLS configuration changed or is linked: ' + str(path))
    info = path.stat()
    descriptor, temporary = tempfile.mkstemp(prefix='.ols-config-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'wb') as target:
            target.write(content)
            target.flush()
            os.fchown(target.fileno(), info.st_uid, info.st_gid)
            shutil.copystat(str(path), temporary)
            for attribute in os.listxattr(str(path)):
                if os.getxattr(str(path), attribute) != os.getxattr(temporary, attribute):
                    raise RuntimeError('Could not retain OLS file attributes: ' + str(path))
            os.fsync(target.fileno())
        current = path.lstat()
        fields = ('st_dev', 'st_ino', 'st_ctime_ns', 'st_mtime_ns', 'st_size')
        if any(getattr(current, field) != getattr(info, field) for field in fields) or path.read_bytes() != expected:
            raise RuntimeError('OLS configuration changed before replacement: ' + str(path))
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_config_changes(changes, validate, service):
    """Validate both sides of a config-only migration and retain service state."""
    validate()
    initial = service.prepare_state()
    originals = []
    activation_attempted = False
    try:
        for name, (before, after) in changes.items():
            path = Path(name)
            if os.path.commonpath([str(service.root / 'conf'), str(path)]) != str(service.root / 'conf'):
                raise RuntimeError('Configuration outside OLS conf: ' + str(path))
            original = path.read_bytes()
            if path.read_text() != before:
                raise RuntimeError('OLS configuration changed during migration: ' + name)
            updated = after.encode(locale.getpreferredencoding(False))
            replace_config(path, original, updated)
            originals.append((path, original, updated))
        validate()
        if service.state() != initial:
            raise RuntimeError('OLS service changed during configuration migration')
        if initial:
            activation_attempted = True
            service.reload(initial)
    except Exception as original_error:
        failures = []
        for path, original, updated in reversed(originals):
            try:
                replace_config(path, updated, original)
            except Exception as error:
                failures.append(str(error))
        if failures:
            raise RuntimeError('OLS configuration restoration incomplete: ' + ', '.join(failures)) from original_error
        if originals:
            validate()
            state = service.settled_state()
            if activation_attempted and not state:
                service.change('start', None)
            elif activation_attempted:
                service.reload(state)
        raise
