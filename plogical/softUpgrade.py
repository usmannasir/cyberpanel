"""Launch a panel-initiated upgrade with the selected release's own Python helpers."""
import ast
import fcntl
import json
import os
import re
import hashlib
import http.client
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen


REPOSITORY = 'https://github.com/usmannasir/cyberpanel.git'
RAW = 'https://raw.githubusercontent.com/usmannasir/cyberpanel'
HELPERS = (
    ('from cyberpanel_version import ', 'cyberpanel_version.py'),
    ('from cyberpanel_firewall_migration import ', 'cyberpanel_firewall_migration.py'),
    ('from lscpd_binary import ', 'lscpd_binary.py'),
    ('def load_ols_security_assets(', 'plogical/olsSecurityAssets.py'),
    ('olsParserRecovery.py', 'plogical/olsParserRecovery.py'),
    ('olsStockClassifier.py', 'plogical/olsStockClassifier.py'),
    ('olsNativeValidation.py', 'plogical/olsNativeValidation.py'),
    ('olsServiceControl.py', 'plogical/olsServiceControl.py'),
)


STATUS_ROOT = Path('/run/cyberpanel-soft-upgrades')


def status_path(job):
    if not re.fullmatch(r'[0-9a-f]{32}', job):
        raise ValueError('Invalid upgrade run identifier.')
    return STATUS_ROOT / job


def live_start_ticks(stat):
    # The process name may contain spaces and closing parentheses.
    fields = stat.rsplit(')', 1)[-1].split()
    if len(fields) < 20 or fields[0] == 'Z':
        return None
    return fields[19]


def read_status(job):
    """A root-side negative result is distinct from transport unavailability."""
    try:
        record = json.loads(status_path(job).read_text())
    except FileNotFoundError:
        return {'state': 'missing'}
    if record['state'] in ('starting', 'running'):
        try:
            observed = live_start_ticks(Path('/proc/%d/stat' % int(record['pid'])).read_text())
        except (FileNotFoundError, ProcessLookupError):
            observed = None
        if not observed or observed != record.get('start_ticks'):
            return {'state': 'failed', 'message': 'The upgrade launcher stopped before reporting completion. Check the upgrade log and service state before retrying.'}
    return record


def record_status(job, state, message='', activation=None):
    path = status_path(job)
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    with tempfile.NamedTemporaryFile(mode='w', dir=STATUS_ROOT, delete=False) as output:
        record = {'state': state, 'message': message}
        if activation is not None:
            record['activation'] = activation
        if state in ('starting', 'running'):
            record['pid'] = os.getpid()
            record['start_ticks'] = live_start_ticks(Path('/proc/self/stat').read_text())
        json.dump(record, output)
        os.chmod(output.name, 0o600)
    os.replace(output.name, path)


def validate_branch(branch):
    if not re.fullmatch(r'stable|v[0-9]+(?:\.[0-9]+)+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?', branch):
        raise ValueError('Select a stable CyberPanel release branch.')
    return branch


def resolve_release(branch):
    validate_branch(branch)
    ref = 'refs/heads/' + branch
    result = subprocess.run(['git', 'ls-remote', '--exit-code', REPOSITORY, ref],
                            check=True, stdout=subprocess.PIPE, universal_newlines=True, timeout=30)
    match = re.fullmatch(r'([0-9a-f]{40})\s+' + re.escape(ref), result.stdout.strip())
    if not match:
        raise ValueError('Could not resolve the selected CyberPanel release.')
    return match.group(1)


def stage_release(stage, revision):
    def fetch(path):
        with urlopen('%s/%s/%s' % (RAW, revision, path), timeout=30) as response:
            content = response.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise ValueError('Unexpected release file size: ' + path)
        if path == 'CPScripts/watchdog.sh':
            if not content.startswith(b'#!/bin/bash\n'):
                raise ValueError('Invalid release watchdog script')
            tree = None
        else:
            tree = ast.parse(content, filename=path)
        (stage / Path(path).name).write_bytes(content)
        return content.decode('utf-8'), tree

    source, tree = fetch('plogical/upgrade.py')
    if not any(isinstance(node, ast.ClassDef) and node.name == 'Upgrade' for node in tree.body):
        raise ValueError('Missing Upgrade class in selected release.')
    if 'from plogical.olsSecurityAssets import' in source:
        raise ValueError('This release requires an installed OLS helper. Choose the current stable release.')
    for marker, path in HELPERS:
        if marker in source:
            helper, _ = fetch(path)
            if path == 'plogical/olsServiceControl.py' and 'olsWatchdog.py' in helper:
                fetch('plogical/olsWatchdog.py')
                fetch('CPScripts/watchdog.sh')


def run(branch, lock_fd=None):
    revision = resolve_release(branch)
    with tempfile.TemporaryDirectory(prefix='cyberpanel-soft-upgrade-') as directory:
        stage = Path(directory)
        stage_release(stage, revision)
        with tempfile.TemporaryFile() as errors:
            # The service manager can terminate the launcher independently.
            # The running upgrader must retain the same flock until it exits.
            inherited = (lock_fd,) if lock_fd is not None else ()
            result = subprocess.run([sys.executable, '-u', str(stage / 'upgrade.py'),
                                     'SoftUpgrade,' + branch], cwd=stage, stderr=errors,
                                    pass_fds=inherited)
            if result.returncode:
                errors.seek(max(0, errors.tell() - 2000))
                diagnostic = errors.read().decode('utf-8', errors='replace').strip()
                raise RuntimeError('Upgrade exited with code %s. %s' % (result.returncode, diagnostic))
        return 0


SYSTEMCTL = '/usr/bin/systemctl'
SYSTEMD_RUN = '/usr/bin/systemd-run'
PANEL_CONF = Path('/usr/local/lscp/conf')
PANEL_PID = Path('/tmp/lscpd/lscpd.pid')
PANEL_BINARY = Path('/usr/local/lscp/bin/lscpd')


def process_identity(pid, proc=Path('/proc')):
    try:
        content = (proc / str(pid) / 'stat').read_text()
        ticks = live_start_ticks(content)
        if ticks is None:
            return None
        return {'pid': int(pid), 'start_ticks': ticks}
    except (OSError, ValueError):
        return None


def native_panel_master(manager_pid, group, pid_path=PANEL_PID, binary=PANEL_BINARY, proc=Path('/proc')):
    # Older vendor units omit PIDFile, and systemd cannot always guess a main
    # process after restart. Verify the controller's native PID rather than
    # treating a healthy but untracked daemon as activated without identity.
    try:
        info = pid_path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RuntimeError('Cannot verify the native panel PID file.')
    text = pid_path.read_text().strip()
    if not re.fullmatch(r'[1-9][0-9]{0,9}', text):
        raise RuntimeError('The native panel PID file is invalid.')
    pid = int(text)
    if manager_pid and manager_pid != pid:
        raise RuntimeError('The panel service manager disagrees with the native controller PID.')
    identity = process_identity(pid, proc)
    if identity is None:
        return None
    directory = proc / text
    if not os.path.samefile(str(directory / 'exe'), str(binary)):
        raise RuntimeError('The native panel PID does not identify the installed executable.')
    if not any(line.rsplit(':', 1)[-1] == group for line in (directory / 'cgroup').read_text().splitlines()):
        raise RuntimeError('The native panel PID belongs to a different control group.')
    return identity


def panel_state():
    result = subprocess.run([SYSTEMCTL, 'show', 'lscpd', '--property=MainPID,ActiveState,ControlGroup'],
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=10)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    group = values.get('ControlGroup', '')
    if not group or not group.startswith('/') or not group.endswith('/lscpd.service'):
        raise RuntimeError('Cannot verify the panel service control group.')
    manager_pid = int(values.get('MainPID', '0'))
    master = native_panel_master(manager_pid, group)
    workers = []
    native = []
    for path in Path('/proc').glob('[0-9]*'):
        try:
            name = (path / 'comm').read_text().strip()
            if name not in ('lswsgi', 'lscpd'):
                continue
            if not any(line.rsplit(':', 1)[-1] == group for line in (path / 'cgroup').read_text().splitlines()):
                continue
            identity = process_identity(path.name)
            if identity:
                fields = (path / 'stat').read_text().rsplit(')', 1)[-1].split()
                identity['ppid'] = int(fields[1])
                if name == 'lswsgi':
                    workers.append(identity)
                else:
                    if not os.path.samefile(str(path / 'exe'), str(PANEL_BINARY)):
                        raise RuntimeError('A different panel executable is active.')
                    native.append(identity)
        except (OSError, ValueError):
            continue
    if master and (not any(p['pid'] == master['pid'] for p in native) or not all(
            worker_belongs_to_master(p, master) for p in native)):
        raise RuntimeError('The panel native processes do not share the verified master.')
    return {'master': master, 'workers': workers, 'active': values.get('ActiveState') == 'active',
            'manager_pid': manager_pid}


def panel_endpoint(conf=PANEL_CONF):
    binding = (conf / 'bind.conf').read_text().strip()
    if not binding:
        return '127.0.0.1', 8090
    match = re.fullmatch(r'(\*|\[[0-9a-fA-F:]+\]|[0-9a-fA-F:.]+):([0-9]{1,5})', binding)
    if not match or not 1 <= int(match.group(2)) <= 65535:
        raise RuntimeError('Cannot verify the configured panel listen address.')
    address = match.group(1).strip('[]')
    return ('127.0.0.1' if address in ('*', '0.0.0.0') else '::1' if address == '::' else address), int(match.group(2))


def probe_panel(conf=PANEL_CONF):
    # This local readiness check trusts the root-owned installed leaf certificate
    # by exact DER pin, including a panel's default self-signed certificate.
    pem = (conf / 'cert.pem').read_text()
    match = re.search(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', pem, re.S)
    if not match:
        raise RuntimeError('Cannot read the installed panel certificate.')
    expected = ssl.PEM_cert_to_DER_cert(match.group(0))
    address, port = panel_endpoint(conf)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((address, port), timeout=3) as connection:
        with context.wrap_socket(connection, server_hostname='localhost') as secured:
            if secured.getpeercert(binary_form=True) != expected:
                raise RuntimeError('The panel readiness endpoint certificate does not match the installed certificate.')
            secured.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = http.client.HTTPResponse(secured)
            response.begin()
            body = response.read(256 * 1024 + 1)
            if response.status != 200 or not body or len(body) > 256 * 1024 or b'<html' not in body.lower():
                raise RuntimeError('The restarted panel did not return its login page.')
    return {'http_status': 200, 'certificate_sha256': hashlib.sha256(expected).hexdigest()}


def worker_belongs_to_master(worker, master):
    pid = worker['pid']
    for unused in range(32):
        if pid == master['pid']:
            return True
        try:
            fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[-1].split()
            pid = int(fields[1])
        except (OSError, ValueError):
            return False
        if pid <= 1:
            return False
    return False


def activate_panel_runtime(lock_fd, timeout=90):
    before = panel_state()
    subprocess.run([SYSTEMCTL, 'restart', 'lscpd'], check=True, timeout=90,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(lock_fd,))
    deadline = time.monotonic() + timeout
    last_error = 'The panel has not loaded a fresh application worker.'
    while time.monotonic() < deadline:
        try:
            after = panel_state()
            master = after['master']
            retired = ([before['master']] if before['master'] else []) + before['workers']
            if not after['active'] or not master or any(process_identity(p['pid']) ==
                    {'pid': p['pid'], 'start_ticks': p['start_ticks']} for p in retired):
                raise RuntimeError('The previous panel runtime is still draining.')
            health = probe_panel()
            after = panel_state()
            if not after['active'] or after['master'] != master or not after['workers'] or not all(
                    int(worker['start_ticks']) >= int(master['start_ticks']) and
                    worker_belongs_to_master(worker, master) for worker in after['workers']):
                raise RuntimeError('The panel has not loaded a fresh application worker.')
            return dict(health, master=master, workers=after['workers'],
                        previous_runtime_retired=True)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, http.client.HTTPException) as error:
            last_error = str(error)
        time.sleep(.2)
    raise RuntimeError('Panel runtime activation failed: ' + last_error)


def require_job_scope(job, pid='self'):
    expected = '/cyberpanel-soft-upgrade-%s.scope' % job
    groups = [line.rsplit(':', 1)[-1] for line in Path('/proc/%s/cgroup' % pid).read_text().splitlines()]
    if any('/lscpd.service/' in group or group.endswith('/lscpd.service') for group in groups) or not any(
            group.endswith(expected) for group in groups):
        raise RuntimeError('The upgrade worker must run in its independent systemd scope.')


def worker_io(job):
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    descriptor = os.open(str(status_path(job)) + '.launcher.log',
                         os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise RuntimeError('Cannot verify the upgrade worker log.')
        os.dup2(descriptor, 1)
        os.dup2(descriptor, 2)
    finally:
        os.close(descriptor)
    descriptor = os.open(os.devnull, os.O_RDONLY)
    try:
        os.dup2(descriptor, 0)
    finally:
        os.close(descriptor)


def admission_path(job):
    return Path(str(status_path(job)) + '.admitted')


def decide_admission(job, decision):
    """Accept and cancel compete for one immutable, fully written decision."""
    with tempfile.NamedTemporaryFile(mode='w', dir=STATUS_ROOT, delete=False) as output:
        temporary = output.name
        json.dump(decision, output)
        os.chmod(temporary, 0o600)
    try:
        try:
            os.link(temporary, str(admission_path(job)))
            return decision
        except FileExistsError:
            return json.loads(admission_path(job).read_text())
    finally:
        os.unlink(temporary)


def await_worker_admission(job, timeout=30):
    """No upgrade may begin without the short-lived caller's checked handoff."""
    record_status(job, 'starting')
    own = process_identity(os.getpid())
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            admitted = json.loads(admission_path(job).read_text())
        except FileNotFoundError:
            admitted = None
        if admitted == dict(own, decision='accept'):
            return
        if admitted is not None or read_status(job).get('state') == 'failed':
            raise RuntimeError('The upgrade caller did not authorize the worker handoff.')
        time.sleep(0.1)
    decision = decide_admission(job, {'decision': 'cancel'})
    if decision == dict(own, decision='accept'):
        return
    raise RuntimeError('The upgrade worker handoff timed out before admission.')


def launch_panel_job(branch, job, timeout=20):
    validate_branch(branch)
    status_path(job)
    if admission_path(job).exists():
        raise RuntimeError('This upgrade run was already admitted.')
    record_status(job, 'starting')
    caller = os.getpid()
    try:
        process = subprocess.Popen([SYSTEMD_RUN, '--scope', '--quiet', '--slice=system.slice',
                                    '--unit=cyberpanel-soft-upgrade-' + job, '--',
                                    sys.executable, '-I', str(Path(__file__).resolve()),
                                    '--worker', branch, job], start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = read_status(job)
            if status.get('state') == 'failed':
                raise RuntimeError(status.get('message', 'Worker admission failed.'))
            if status.get('state') == 'starting' and status.get('pid') != caller:
                identity = process_identity(status['pid'])
                if identity != {'pid': status['pid'], 'start_ticks': status.get('start_ticks')}:
                    raise RuntimeError('The upgrade worker identity changed during admission.')
                require_job_scope(job, identity['pid'])
                if decide_admission(job, dict(identity, decision='accept')).get('decision') != 'accept':
                    raise RuntimeError('The worker handoff was cancelled before admission.')
                # Never wait for the scope: the old WSGI process must be able to
                # finish its ApplicationInstaller thread before runtime activation.
                return 0
            if process.poll() is not None:
                raise RuntimeError('The independent worker exited before admission.')
            time.sleep(0.1)
        raise RuntimeError('The independent worker did not become ready before admission timed out.')
    except Exception as error:
        decide_admission(job, {'decision': 'cancel'})
        record_status(job, 'failed', 'Could not launch the independent upgrade worker: ' + str(error))
        return 1


def run_panel_job(branch, job, require_admission=False):
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    try:
        with (STATUS_ROOT / '.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Another panel upgrade is in progress.')
            if require_admission:
                await_worker_admission(job)
            record_status(job, 'running')
            run(branch, lock_fd=lock.fileno())
            activation = activate_panel_runtime(lock.fileno())
            record_status(job, 'complete', activation=activation)
            return 0
    except Exception as error:
        record_status(job, 'failed', str(error))
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--status':
        print(json.dumps(read_status(sys.argv[2])))
    elif len(sys.argv) == 4 and sys.argv[1] == '--worker':
        status_path(sys.argv[3])
        require_job_scope(sys.argv[3])
        worker_io(sys.argv[3])
        sys.exit(run_panel_job(sys.argv[2], sys.argv[3], require_admission=True))
    else:
        sys.exit(launch_panel_job(sys.argv[1], sys.argv[2]))
