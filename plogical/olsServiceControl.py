"""Identify and control only the verified OpenLiteSpeed installation during an upgrade."""
import hashlib
import importlib.util
import locale
import os
import platform
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
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
REVIEWED_JAMMY_CONTROLLER = '83435cff252f314ec65c0b61c7eba01289c721a2bf4e4351a402501b6f4bf709'
RECOVERED_JAMMY_BUNDLE = (
    '863687f29a529d379224fe32115d9326028038dd2d38e5aac26ddb4bc5a3bf55',
    '41ae567f45931691e34facf1914bf78bb95236d9f8b1ee75d455cbbc19ca6d8b',
    '62e0feec6a3914e889750cef4e07942db21ba35c77ffa83c86f707e4d4463fbe',
)
RECOVERY_POLICY_NAME = '.cyberpanel-stock-recovery-policy'
RECOVERY_POLICY_BYTES = b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n'
RECOVERY_POLICY_DIAGNOSTIC = '[StockRecovery] Native AutoSSL remains inactive to preserve stock behavior'
# OpenLiteSpeed's own process titles: its main, its workers and its CGI daemon.
PROCESS_TITLE = re.compile(rb'openlitespeed \((?:lshttpd - (?:main|#[0-9]+)|lscgid)\)\x00*')


def recovery_policy_identity(root):
    """Read one bounded, root-owned policy without following links or FIFOs."""
    root = Path(root)
    path = root / RECOVERY_POLICY_NAME
    # Opening the directory pins the parent used for every subsequent operation.
    directory = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        try:
            fd = os.open(RECOVERY_POLICY_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=directory)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise RuntimeError('Unsafe stock recovery policy: ' + str(path)) from error
        try:
            parent = os.fstat(directory)
            before = os.fstat(fd)
            fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                      'st_size', 'st_mtime_ns', 'st_ctime_ns')
            identity = tuple(getattr(before, name) for name in fields)
            if (parent.st_uid != 0 or parent.st_mode & 0o022 or not stat.S_ISREG(before.st_mode)
                    or before.st_uid != 0 or before.st_nlink != 1
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_size != len(RECOVERY_POLICY_BYTES)):
                raise RuntimeError('Unsafe stock recovery policy metadata: ' + str(path))
            if os.read(fd, len(RECOVERY_POLICY_BYTES) + 1) != RECOVERY_POLICY_BYTES:
                raise RuntimeError('Unknown stock recovery policy content: ' + str(path))
            current = os.stat(RECOVERY_POLICY_NAME, dir_fd=directory, follow_symlinks=False)
            if (identity != tuple(getattr(os.fstat(fd), name) for name in fields)
                    or identity != tuple(getattr(current, name) for name in fields)
                    or not os.path.samestat(parent, root.lstat())):
                raise RuntimeError('Stock recovery policy changed while reading')
            return identity
        finally:
            os.close(fd)
    finally:
        os.close(directory)


class RecoveryPolicy:
    """An absent policy is created only while stopped; rollback removes only ours."""
    def __init__(self, root):
        self.root = Path(root)
        parent = self.root.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
            raise RuntimeError('Unsafe stock recovery policy parent')
        self.parent_identity = (parent.st_dev, parent.st_ino, parent.st_uid, parent.st_gid, parent.st_mode)
        self.original = recovery_policy_identity(root)
        self.created = None

    def verify(self):
        parent = self.root.lstat()
        if self.parent_identity != (parent.st_dev, parent.st_ino, parent.st_uid, parent.st_gid, parent.st_mode):
            raise RuntimeError('Stock recovery policy parent changed')
        expected = self.created if self.created is not None else self.original
        if recovery_policy_identity(self.root) != expected:
            raise RuntimeError('Stock recovery policy changed during the transaction')
        return expected

    def apply(self):
        self.verify()
        if self.original is not None or self.created is not None:
            return
        fd, temporary = tempfile.mkstemp(prefix='.ols-policy-', dir=str(self.root))
        try:
            with os.fdopen(fd, 'wb') as output:
                os.fchmod(output.fileno(), 0o600)
                os.fchown(output.fileno(), 0, 0)
                output.write(RECOVERY_POLICY_BYTES)
                output.flush()
                os.fsync(output.fileno())
            self.verify()
            # link is an atomic no-overwrite publication; never replace a new file.
            os.link(temporary, str(self.root / RECOVERY_POLICY_NAME), follow_symlinks=False)
            os.unlink(temporary)
            self.created = recovery_policy_identity(self.root)
            directory = os.open(str(self.root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    def rollback(self):
        self.verify()
        if self.created is not None:
            os.unlink(str(self.root / RECOVERY_POLICY_NAME))
            self.created = None
            directory = os.open(str(self.root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        self.verify()


def jammy_platform():
    values = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip().strip(chr(34) + chr(39))
    return (values.get('ID') == 'ubuntu' and values.get('VERSION_ID') == '22.04'
            and platform.machine() in ('x86_64', 'amd64'))


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


def started_before(ticks, other):
    """Whether a process start time (clock ticks, as text) is earlier than another; unknown is not earlier."""
    try:
        return int(ticks) < int(other)
    except (TypeError, ValueError):
        return False


def run(args, timeout=30):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=timeout)


class OLSWorkersRemain(RuntimeError):
    """The controller no longer has a master PID but OLS processes still exist."""


class OLSPreviousGeneration(RuntimeError):
    """An earlier generation of this OLS service is still finishing its connections.

    A graceful restart or reload (lswsctrl restart/reload, SIGUSR1) starts a new
    main process. The old main and every worker still serving a connection keep
    running, reparented to init, until those connections end: on a busy server
    with long downloads or slow clients that can take a long time. They run the
    installed binary in the same service but no longer descend from the master
    that status reports.
    """
    def __init__(self, generation):
        self.generation = dict(generation)  # pid -> start ticks, as observed
        super().__init__('A previous OpenLiteSpeed generation is still finishing connections (PIDs %s)'
                         % ', '.join(str(pid) for pid in sorted(self.generation)))


class OLSRestarting(RuntimeError):
    """OpenLiteSpeed's restart marker exists: a graceful restart is in progress (about 0.1 s).

    The main process creates admin/tmp/.restart when it is told to restart and
    the new main removes it once it is ready to serve. A marker that stays
    means that the restart never finished (see restart_unfinished).
    """


def restart_unfinished(restarting, seconds):
    """What to say once the restart marker has outlasted the wait: the reason and the next step."""
    return OLSRestarting('A restart of OpenLiteSpeed did not finish within %d seconds (%s). Restart OpenLiteSpeed '
                         '(systemctl restart lsws), check that the websites load, and run the upgrade again'
                         % (seconds, restarting))


class OLSStartedDuringStop(RuntimeError):
    """The service was started again while the upgrade's stop was still in progress.

    The vendor unit stops with KillMode=none and `lswsctrl delay-stop`: systemd
    reports the unit stopped at once, while OpenLiteSpeed counts down two seconds
    before it ends. A `systemctl restart lsws` (CyberPanel restarts OpenLiteSpeed
    that way after many panel actions) in that window runs `lswsctrl start`, which
    sends SIGUSR1 to the main still counting down: a new main takes over.
    """
    def __init__(self, master):
        self.master = master
        super().__init__('OpenLiteSpeed was started again (main PID %d) while the upgrade was stopping it' % master)


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
        self._draining_cgroup = None  # control group text of the master our stop action addressed
        self.watch_lock = None
        self._reviewed_stock_controller = None
        self._recovery_policy = None
        self._observed_policy_identity = None
        self._policy_checked = False
        self.kill = os.kill
        self._generation_seen = {}  # (pid, start ticks) -> first seen, monotonic
        self._generation_signalled = set()  # (pid, start ticks) already sent SIGKILL

    # How long every process of an earlier generation must have been seen draining before the upgrade ends it.
    PREVIOUS_GENERATION_WAIT = 60
    # How long a graceful restart that is in progress is waited for before a state inspection gives up.
    RESTART_WAIT = 20

    def _previous_generation(self, master, processes, strays):
        """{pid: start ticks} when every stray belongs to an earlier generation of this service, else None.

        The master must belong to a vendor OLS service. Each stray's tree must
        end in a process whose parent is init, started before the master, and
        every stray must sit in exactly the master's control group. That root
        is the old main (the master's own command line) or, once the old main
        has exited, one of its workers or its CGI daemon left under init (an
        OpenLiteSpeed process title). A process that is exiting has already lost
        its command line and control group; it is waited for, never ended (see
        _end_previous_generation). Anything else stays an unmanaged process.
        """
        try:
            master_cmdline = (self.proc / str(master) / 'cmdline').read_bytes()
            master_cgroup = (self.proc / str(master) / 'cgroup').read_text()
            if process_owner(master_cgroup) not in VENDOR_UNITS or not master_cmdline:
                return None
        except (FileNotFoundError, ProcessLookupError, RuntimeError):
            return None
        generation = {}
        for pid in strays:
            root, seen = pid, set()
            while processes[root][0] in processes:
                if root in seen:
                    return None
                seen.add(root)
                root = processes[root][0]
            try:
                if processes[root][0] != 1 or int(processes[root][1]) >= int(processes[master][1]):
                    return None
                for member in (root, pid):
                    cmdline = (self.proc / str(member) / 'cmdline').read_bytes()
                    cgroup = (self.proc / str(member) / 'cgroup').read_text()
                    if not cmdline and cgroup in ('', master_cgroup):
                        continue  # exiting
                    if cgroup != master_cgroup or (member == root and cmdline != master_cmdline
                                                   and not PROCESS_TITLE.fullmatch(cmdline)):
                        return None
            except (FileNotFoundError, ProcessLookupError):
                continue  # Gone since the scan; the next one decides.
            except ValueError:
                return None
            generation[pid] = processes[pid][1]
        return generation

    def _end_previous_generation(self, generation):
        """SIGKILL exactly the processes observed, each identified again by start time and binary first.

        A process that is exiting (no command line any more) cannot be identified further and ends by itself.
        """
        ended = []
        for pid, ticks in sorted(generation.items()):
            entry = self.proc / str(pid)
            try:
                if (entry / 'stat').read_text().rsplit(')', 1)[1].split()[19] != ticks:
                    continue
                if not os.path.samefile(str(entry / 'exe'), str(self.binary)):
                    continue
                if not (entry / 'cmdline').read_bytes():
                    continue
                self.kill(pid, signal.SIGKILL)
                ended.append(pid)
            except (FileNotFoundError, ProcessLookupError):
                continue
            except (IndexError, PermissionError) as error:
                raise RuntimeError('Cannot end previous OpenLiteSpeed process %d: %s' % (pid, error)) from error
        return ended

    @staticmethod
    def _unit_check(check, master, roots):
        """check(master); beside an earlier generation, systemd may still name that generation's main as
        MainPID (systemd 239 keeps it until it exits, then reads the PID file). Nothing else is accepted."""
        try:
            check(master)
        except RuntimeError:
            for root in roots:
                try:
                    check(root)
                    return
                except RuntimeError:
                    continue
            raise

    def settle_previous_generation(self, check):
        """Return check(). A previous generation is ended only once every one of its processes (pid and start
        time) has been seen draining for PREVIOUS_GENERATION_WAIT seconds, so a generation left by a restart
        during the wait gets its own full wait. Bounded: refuses after three waits."""
        hard = time.monotonic() + 3 * self.PREVIOUS_GENERATION_WAIT
        while True:
            try:
                return check()
            except OLSPreviousGeneration as previous:
                now = time.monotonic()
                for key in previous.generation.items():
                    self._generation_seen.setdefault(key, now)
                if now >= hard:
                    raise
                if any(now - self._generation_seen[key] < self.PREVIOUS_GENERATION_WAIT
                       for key in previous.generation.items()):
                    time.sleep(1)
                    continue
                pending = {pid: ticks for pid, ticks in previous.generation.items()
                           if (pid, ticks) not in self._generation_signalled}
                pids = self._end_previous_generation(pending)
                self._generation_signalled.update((pid, pending[pid]) for pid in pids)
                if pids:
                    print('Ended a previous OpenLiteSpeed generation that was still finishing connections '
                          'after %d seconds: PIDs %s' % (self.PREVIOUS_GENERATION_WAIT,
                                                         ', '.join(str(pid) for pid in pids)), flush=True)
                time.sleep(1)

    def bind_recovery_policy(self, policy, original_core, candidate_core):
        if not jammy_platform() or candidate_core != RECOVERED_JAMMY_BUNDLE[0]:
            raise RuntimeError('Stock recovery policy requires the pinned Jammy core')
        self._recovery_policy = (policy, original_core, candidate_core)
        policy.verify()

    def verify_stock_recovery_policy(self, candidate_core_sha256=None):
        identity = recovery_policy_identity(self.root)
        if self._recovery_policy is not None:
            policy, original_core, candidate_core = self._recovery_policy
            policy.verify()
            if candidate_core_sha256 is not None and candidate_core_sha256 != candidate_core:
                raise RuntimeError('Candidate does not support the stock recovery policy')
            if identity is not None:
                if self.binary.is_symlink() or not self.binary.is_file():
                    raise RuntimeError('Stock recovery policy requires a regular installed core')
                if digest(self.binary) not in (original_core, candidate_core):
                    raise RuntimeError('Installed core differs from the policy transaction')
            return identity
        if self._policy_checked and identity != self._observed_policy_identity:
            raise RuntimeError('Stock recovery policy identity changed, appeared or disappeared')
        if identity is None:
            self._policy_checked = True
            return None
        if candidate_core_sha256 is None:
            if self.binary.is_symlink() or not self.binary.is_file():
                raise RuntimeError('Stock recovery policy requires a regular installed core')
            expected = digest(self.binary)
        else:
            expected = candidate_core_sha256
        if not jammy_platform() or expected != RECOVERED_JAMMY_BUNDLE[0]:
            raise RuntimeError('Installed or candidate core does not support the stock recovery policy')
        self._observed_policy_identity = identity
        self._policy_checked = True
        return identity

    def _bind_reviewed_controller(self, names, original, candidate):
        if self.unit not in (None, 'lshttpd.service'):
            raise RuntimeError('Reviewed controller requires lshttpd.service')
        identity = self.reviewed_controller_identity()
        if identity is None:
            raise RuntimeError('Reviewed controller command path is not pinned')
        self._reviewed_stock_controller = (names, original, candidate, identity)
        # The edited stop() branch must never be used for live host control.
        # The pinned unit is reverified with ExecStop=delay-stop at every state.
        self.unit = 'lshttpd.service'
        self.manager_identified = True

    def reviewed_controller_requested(self):
        directory = self.root/'bin'
        if (self.root.is_symlink() or directory.is_symlink()
                or self.control.resolve().parent != directory or not self.control.is_file()):
            raise RuntimeError('The OLS controller command path cannot be verified')
        return digest(self.control) == REVIEWED_JAMMY_CONTROLLER

    def authorize_stock_controller(self, selected):
        """Bind the reviewed controller to one exact stock transaction only."""
        from olsStockClassifier import reviewed_jammy_controller
        if not self.reviewed_controller_requested():
            return
        if not reviewed_jammy_controller(self.root, selected):
            raise RuntimeError('Reviewed controller requires the exact Jammy stock tuple')
        from installBundle import release_set
        names = ('bin/openlitespeed', 'modules/cyberpanel_ols.so', 'modules/mod_security.so')
        original = tuple(digest(self.root/name) for name in names)
        candidate = tuple(release_set(selected)[kind] for kind in ('binary', 'module', 'modsec'))
        self._bind_reviewed_controller(names, original, candidate)

    def authorize_recovered_jammy_controller(self):
        """Ordinary upgrades may retain the exact verified CRS recovery bundle.

        No stock grant, hash wildcard or package-name inference is used here.
        This works when this helper is loaded alone from an upgrade staging tree.
        """
        if not self.reviewed_controller_requested():
            return
        names = ('bin/openlitespeed', 'modules/cyberpanel_ols.so', 'modules/mod_security.so')
        controller = self.root/'bin/lswsctrl.open'
        if (not jammy_platform() or controller.is_symlink() or not controller.is_file()
                or digest(controller) != REVIEWED_JAMMY_CONTROLLER
                or any((self.root/name).is_symlink() or not (self.root/name).is_file() for name in names)
                or tuple(digest(self.root/name) for name in names) != RECOVERED_JAMMY_BUNDLE):
            raise RuntimeError('Reviewed controller requires the exact recovered Jammy bundle')
        if self.verify_stock_recovery_policy() is None:
            raise RuntimeError('Reviewed recovered controller requires the stock recovery policy')
        self._bind_reviewed_controller(names, RECOVERED_JAMMY_BUNDLE, RECOVERED_JAMMY_BUNDLE)

    def reviewed_controller_identity(self):
        path = self.root/'bin/lswsctrl.open'
        if (not self.control.is_symlink() or os.readlink(str(self.control)) != 'lswsctrl.open'
                or path.is_symlink() or not path.is_file()
                or self.control.resolve() != path.resolve()
                or digest(self.control) != REVIEWED_JAMMY_CONTROLLER):
            return None
        target, link = path.stat(), self.control.lstat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_ctime_ns')
        return (tuple(getattr(target, name) for name in fields),
                tuple(getattr(link, name) for name in fields), os.readlink(str(self.control)))

    def reviewed_stock_controller(self):
        if self._reviewed_stock_controller is None:
            return False
        if not jammy_platform() or self.unit != 'lshttpd.service':
            return False
        names, original, candidate, identity = self._reviewed_stock_controller
        path = self.root/'bin/lswsctrl.open'
        if path.is_symlink() or not path.is_file() or digest(path) != REVIEWED_JAMMY_CONTROLLER:
            return False
        if self.reviewed_controller_identity() != identity:
            return False
        if any((self.root/name).is_symlink() or not (self.root/name).is_file() for name in names):
            return False
        values = tuple(digest(self.root/name) for name in names)
        # Known partial placement can be inspected only to prove quiescence
        # before rollback. It must never be started or treated as a live bundle.
        return all(value in (old, new) for value, old, new in zip(values, original, candidate))

    def reviewed_bundle_complete(self):
        if self._reviewed_stock_controller is None:
            return True
        names, original, candidate, _ = self._reviewed_stock_controller
        return tuple(digest(self.root/name) for name in names) in (original, candidate)

    def controller(self):
        self.verify_stock_recovery_policy()
        directory = self.root / 'bin'
        env = directory / 'lsws_env'
        if (self.root.is_symlink() or directory.is_symlink() or
                self.control.resolve().parent != directory or not self.control.is_file() or
                (not self.reviewed_stock_controller() if self._reviewed_stock_controller is not None
                 else digest(self.control) not in CONTROLLER_HASHES) or env.is_symlink() or
                not env.is_file() or digest(env) != ENV_HASH):
            raise RuntimeError('The OLS controller or its PID configuration cannot be verified')
        # The vendor start command runs bin/get_trial_key.sh when that file exists and
        # starts wswatch.sh when WSWATCH is 1. Neither is part of OpenLiteSpeed or of
        # CyberPanel, so a start made here would run something nobody has verified.
        # Each refusal names what was found and what removes it.
        hook = directory / 'get_trial_key.sh'
        if os.path.lexists(str(hook)):
            raise RuntimeError(
                '%s exists. The start command of OpenLiteSpeed runs that file on every start; it is the trial key '
                'hook of LiteSpeed Enterprise and no part of OpenLiteSpeed or of CyberPanel. Move it away '
                '(mv %s /root/) and run the upgrade again' % (hook, hook))
        if os.getenv('WSWATCH'):
            raise RuntimeError(
                'The environment variable WSWATCH is set, which makes the start command of OpenLiteSpeed start '
                "LiteSpeed's own watchdog script. Run the upgrade again from a shell without it (unset WSWATCH)")
        marker = self.root / 'admin/tmp/.restart'
        if os.path.lexists(str(marker)):
            raise OLSRestarting('OpenLiteSpeed is restarting: its restart marker %s exists' % marker)

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
        # Something else may be restarting OpenLiteSpeed right now (the panel's cron
        # job does after an .htaccess change, and so does a panel action). That is
        # over in a moment and is waited for, as settled_state() does; only a marker
        # that stays refuses.
        deadline = time.monotonic() + self.RESTART_WAIT
        while True:
            try:
                initial = self.settle_previous_generation(self.inspect_state)
                break
            except OLSRestarting as restarting:
                if time.monotonic() >= deadline:
                    raise restart_unfinished(restarting, self.RESTART_WAIT) from restarting
                time.sleep(0.25)
        self.verify_mapped_bundle(initial)
        if watchdog.inspect_watchdog(self.root, self.proc, allow_legacy=True):
            self.watch_lock = watchdog.lock_identity(self.root, require_exclusive=True)
        watchdog.prepare_watchdog(self.root, bool(initial), self.proc, script)
        if self.state() != initial:
            raise RuntimeError('OLS changed state during watchdog handoff')
        return initial

    def state(self):
        return self.inspect_state(allow_legacy=False)

    def draining_leftovers(self, processes):
        """What remains while our verified stop drains: None when anything unaccounted for is present.

        Identities observed before our stop action are waited for. A process of the
        generation before the master being stopped (see _earlier_than_draining) is
        returned as {pid: start ticks} so that change() ends it with the service; {}
        means only our own processes remain.
        """
        if not self.draining or not self._draining_processes:
            return None
        earlier = {}
        for pid, (parent, ticks) in processes.items():
            known = self._draining_processes.get(pid) == ticks
            if not known and not started_before(ticks, self.draining[1]):
                return None  # Started with or after the master being stopped and not seen before.
            try:
                cgroup = (self.proc / str(pid) / 'cgroup').read_text()
                if known:
                    if process_owner(cgroup) != self.draining[2]:
                        return None
                    continue
                if not self._earlier_than_draining(pid, processes, cgroup):
                    return None
            except (FileNotFoundError, ProcessLookupError):
                continue  # Disappearance still requires a fresh empty snapshot.
            earlier[pid] = ticks
        return earlier

    def _earlier_than_draining(self, pid, processes, cgroup):
        """An orphaned process of the generation before the master being stopped.

        A graceful restart shortly before our stop leaves the old main's workers or
        CGI daemon under init until their connections end. Its tree's root has init as
        parent, started before the master being stopped, carries an OpenLiteSpeed process
        title, and every member sits in exactly that master's control group. A member
        that is exiting has lost its command line and control group.
        """
        if self._draining_cgroup is None:
            return False
        root, seen = pid, set()
        while processes[root][0] in processes:
            if root in seen:
                return False
            seen.add(root)
            root = processes[root][0]
        if processes[root][0] != 1 or not started_before(processes[root][1], self.draining[1]):
            return False
        for member in (pid, root):
            text = cgroup if member == pid else (self.proc / str(member) / 'cgroup').read_text()
            cmdline = (self.proc / str(member) / 'cmdline').read_bytes()
            if not cmdline and text in ('', self._draining_cgroup):
                continue  # exiting
            if text != self._draining_cgroup or (member == root and not PROCESS_TITLE.fullmatch(cmdline)):
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
        if not self.reviewed_bundle_complete() and (master or processes):
            raise RuntimeError('A partially placed OLS bundle is not independently stopped')
        if not master:
            if processes:
                if self.draining:
                    earlier = self.draining_leftovers(processes)
                    if earlier is None:
                        raise RuntimeError('An unverified OLS process appeared during shutdown')
                    if earlier:
                        raise OLSPreviousGeneration(earlier)
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
            earlier = (self.draining_leftovers(processes) if dead and self.draining and master == self.draining[0]
                       and (master_fields is None or master_fields[19] == self.draining[1]) else None)
            if earlier:
                raise OLSPreviousGeneration(earlier)
            if earlier is not None:
                # The PID file may outlive the master while its known workers
                # finish exiting. This is a pending stop, never a stopped state.
                raise OLSWorkersRemain('Original OLS master exited while its verified workers drain')
            raise RuntimeError('OLS status PID does not identify the installed master '
                               '(reported=%s, live=%s, stopping=%s)' %
                               (master, sorted(processes), self.draining is not None))
        strays = []
        for pid in processes:
            seen, current = set(), pid
            while current != master:
                if current in seen or current not in processes:
                    strays.append(pid)
                    break
                seen.add(current)
                current = processes[current][0]
        previous, roots = None, []
        if strays:
            generation = self._previous_generation(master, processes, strays)
            if generation is None:
                raise RuntimeError('An unmanaged OLS process is also running')
            # Raised only after the master's own unit checks below have passed.
            previous = OLSPreviousGeneration(generation)
            roots = sorted(pid for pid in generation if processes[pid][0] == 1)
        try:
            owner = process_owner((self.proc / str(master) / 'cgroup').read_text())
        except (FileNotFoundError, ProcessLookupError):
            if (self.draining is not None and (master, processes[master][1]) == self.draining[:2]
                    and self.draining_leftovers(processes) is not None):
                # The verified master can exit after the /proc scan but before
                # this read. Never infer quiescence from that race: the bounded
                # stop loop must obtain a fresh empty snapshot with unit proof.
                raise OLSWorkersRemain('Original OLS master exited during ownership inspection')
            raise
        if self.draining is not None:
            if (master, processes[master][1], owner) == self.draining:
                if previous is not None:
                    # A graceful restart shortly before our stop left processes of the
                    # generation before; they end with the service (see change()).
                    raise previous
                raise OLSWorkersRemain('Original OLS master is draining after its verified stop action')
            if owner == self.draining[2] and started_before(self.draining[1], processes[master][1]):
                raise OLSStartedDuringStop(master)
            if previous is not None:
                raise RuntimeError('An unmanaged OLS process is also running')
        self._unit_check(lambda pid: self.verify_unit_claims(pid, owner), master, roots)
        if self.manager_identified and owner != self.unit:
            raise RuntimeError('OLS changed its service manager')
        self.unit = owner
        self.manager_identified = True
        self._unit_check(self.systemd, master, roots)
        if previous is not None:
            raise previous
        self._observed_processes = {pid: entry[1] for pid, entry in processes.items()}
        return master, processes[master][1], owner

    def settled_state(self, retire_previous=True):
        """retire_previous=False only reports: an earlier generation then raises OLSPreviousGeneration."""
        deadline = time.monotonic() + self.RESTART_WAIT
        while True:
            try:
                return self.settle_previous_generation(self.state) if retire_previous else self.state()
            except (OLSWorkersRemain, OLSRestarting) as pending:
                if time.monotonic() >= deadline:
                    if isinstance(pending, OLSRestarting):
                        raise restart_unfinished(pending, self.RESTART_WAIT) from pending
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

    def change(self, action, expected, again=False):
        """Stop or start the service and wait until it is verified so.

        A stop that the service outlives because it was started again (see
        OLSStartedDuringStop) is repeated once on the instance that took over.
        """
        if action not in ('stop', 'start') or self.state() != expected:
            raise RuntimeError('OLS changed state before the ' + action + ' action')
        wanted_running = action == 'start'
        if wanted_running and self._recovery_policy is not None:
            policy, original_core, candidate_core = self._recovery_policy
            if digest(self.binary) == candidate_core and policy.verify() is None:
                raise RuntimeError('Cannot start the recovered core without its stock recovery policy')
        if wanted_running and not self.reviewed_bundle_complete():
            raise RuntimeError('Cannot start a partially placed OLS bundle; restore the complete originals first')
        if bool(expected) == wanted_running:
            return expected
        self.verify_mapped_bundle(expected)
        observed = dict(self._observed_processes)
        try:
            cgroup = (self.proc / str(expected[0]) / 'cgroup').read_text() if action == 'stop' else None
        except (FileNotFoundError, ProcessLookupError):
            cgroup = None
        command = ['systemctl', action, self.unit] if self.unit else [str(self.control), action]
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if result.returncode:
            raise RuntimeError('OpenLiteSpeed service %s failed' % action)
        self.draining = expected if action == 'stop' else None
        self._draining_processes = observed if action == 'stop' else {}
        self._draining_cgroup = cgroup
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                try:
                    state = self.state()
                except OLSStartedDuringStop as started:
                    if again:
                        raise RuntimeError('%s, and again after the upgrade stopped it once more; nothing was '
                                           'replaced. Something on this server restarts OpenLiteSpeed during the '
                                           'upgrade: run it again when the server is quiet' % started)
                    print(str(started) + '; stopping it once more', flush=True)
                    break
                except OLSRestarting:
                    if action != 'stop':
                        raise
                    time.sleep(0.25)  # a restart of the instance being stopped (see OLSStartedDuringStop)
                    continue
                except OLSWorkersRemain:
                    # Master PID removal can precede worker exit. A pending
                    # transition is never evidence that files may be replaced.
                    time.sleep(0.25)
                    continue
                except OLSPreviousGeneration as previous:
                    if action != 'stop':
                        raise
                    # The vendor stop (KillMode=none, delay-stop) lets OpenLiteSpeed
                    # end by itself after systemctl returns. Processes of the
                    # generation before it, left by a graceful restart, end with the
                    # service as its own connections do; the next snapshot must
                    # still come back empty before any file is replaced.
                    ended = self._end_previous_generation(previous.generation)
                    if ended:
                        print('Ended processes of the previous OpenLiteSpeed generation with the stop: PIDs %s'
                              % ', '.join(str(pid) for pid in ended), flush=True)
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
            else:
                raise RuntimeError('OpenLiteSpeed did not ' + action)
        finally:
            self.draining = None
            self._draining_processes = {}
            self._draining_cgroup = None
        # The instance that took over is settled (systemd finishes its start job,
        # the stopped one its countdown) and verified like any other before it is stopped.
        self.wait_for_unit()
        return self.change('stop', self.settled_state(), again=True)

    def wait_for_unit(self, timeout=60):
        """Wait while systemd still runs a job of the unit (activating, deactivating, reloading).

        `lswsctrl start` keeps the unit activating for seconds after it sent SIGUSR1;
        its claims on the main PID are verifiable only once that job has finished.
        """
        if self.unit is None or not Path('/run/systemd/system').is_dir():
            return
        deadline = time.monotonic() + timeout
        while True:
            result = run(['systemctl', 'show', self.unit, '--property=ActiveState'])
            state = result.stdout.strip().partition('=')[2]
            if result.returncode or state not in ('activating', 'deactivating', 'reloading'):
                return
            if time.monotonic() >= deadline:
                raise RuntimeError('The OpenLiteSpeed unit is still %s after %d seconds' % (state, timeout))
            time.sleep(0.5)

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
