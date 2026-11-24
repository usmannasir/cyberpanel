"""Launch a panel-initiated upgrade with the selected release's own Python helpers."""
import ast
import fcntl
import json
import os
import re
import hashlib
import shutil
import http.client
import signal
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
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
INSTALLATION = Path('/usr/local/CyberCP')

# The longest step that writes nothing, the panel's web worker build, has a
# limit of 15 minutes. An upgrade that wrote nothing for twice that is stopped;
# from the page an administrator may stop one that wrote nothing for 5 minutes.
IDLE_LIMIT = 30 * 60
STOP_AFTER = 5 * 60
LONGEST = 4 * 3600
# git waits on a stalled HTTPS transfer for as long as the connection stays open.
GIT_ENVIRONMENT = {'GIT_HTTP_LOW_SPEED_LIMIT': '1000', 'GIT_HTTP_LOW_SPEED_TIME': '60',
                   'GIT_TERMINAL_PROMPT': '0'}
# What git prints when it got no complete answer from GitHub.
UNREACHABLE = re.compile(r'unable to access|Could not resolve|Failed to connect|timed out|too slow|'
                         r'Connection (?:reset|refused)|RPC failed|early EOF|remote end hung up|'
                         r'returned error: (?:5[0-9][0-9]|429)|SSL|TLS|gnutls', re.I)


def status_path(job):
    if not re.fullmatch(r'[0-9a-f]{32}', job):
        raise ValueError('Invalid upgrade run identifier.')
    return STATUS_ROOT / job


def stop_path(job):
    return Path(str(status_path(job)) + '.stop')


def idle_seconds(record, clock=time.time):
    """How long a running upgrade has written nothing, or None when unknown."""
    active = record.get('active')
    if isinstance(active, bool) or not isinstance(active, (int, float)):
        return None
    return max(0, int(clock() - active))


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
        idle = idle_seconds(record)
        if idle is not None:
            record.update(idle=idle, stoppable=idle >= STOP_AFTER)
    return record


def record_status(job, state, message='', activation=None, active=None, incomplete=None):
    path = status_path(job)
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    with tempfile.NamedTemporaryFile(mode='w', dir=STATUS_ROOT, delete=False) as output:
        record = {'state': state, 'message': message}
        if activation is not None:
            record['activation'] = activation
        if active is not None:
            record['active'] = active
        if incomplete:
            record['incomplete'] = incomplete
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


def installed_order(installation=None):
    """The installed release as (major, minor, ..., build); None when it cannot be read."""
    try:
        text = ((installation or INSTALLATION) / 'cyberpanel_version.py').read_text()
        version = re.search(r"^VERSION = '([0-9]{1,4}(?:\.[0-9]{1,4}){1,3})'$", text, re.M).group(1)
        build = re.search(r'^BUILD = ([0-9]{1,5})$', text, re.M).group(1)
    except (OSError, AttributeError):
        return None
    return tuple(int(part) for part in version.split('.')) + (int(build),)


def refuse_older_release(branch, installed):
    """The upgrade page must not go back to an older release.

    Old upgraders know nothing of what newer ones set up, and those before
    3.0.7 remove the running installation before fetching their own.
    """
    validate_branch(branch)
    if branch == 'stable' or installed is None:
        return
    release = tuple(int(part) for part in re.match(r'v([0-9]+(?:\.[0-9]+)+)', branch).group(1).split('.'))
    if release < installed:
        raise ValueError('That release is older than the installed one. '
                         'Choose the installed release or a newer one.')


def from_github(action, what, attempts=3, pause=10, sleep=time.sleep):
    """`action()`, asked again after a short pause while GitHub does not answer.

    A longer outage ends the upgrade before anything was changed, with a
    message saying so instead of a git exit status.
    """
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise  # A missing file is not an outage.
            failure = 'HTTP %d' % error.code
        except subprocess.CalledProcessError as error:
            # git says "not our ref" or "Repository not found" when GitHub answered.
            said = [line.strip() for line in (error.stderr or '').splitlines() if line.strip()]
            if not said or not UNREACHABLE.search(said[-1]):
                raise
            failure = said[-1][:300]
        except subprocess.TimeoutExpired as error:
            failure = 'no answer within %d seconds' % error.timeout
        except (URLError, socket.timeout, ConnectionError) as error:
            failure = str(getattr(error, 'reason', error))[:300]
        if attempt < attempts:
            sleep(pause)
    raise RuntimeError('GitHub could not be reached for %s (%s). Nothing was changed on this server; '
                       'try again later.' % (what, failure))


def git_environment():
    return dict(os.environ, **GIT_ENVIRONMENT)


def resolve_release(branch):
    validate_branch(branch)
    ref = 'refs/heads/' + branch
    result = from_github(lambda: subprocess.run(
        ['git', 'ls-remote', '--exit-code', REPOSITORY, ref], check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30,
        env=git_environment()), 'the release ' + branch)
    match = re.fullmatch(r'([0-9a-f]{40})\s+' + re.escape(ref), result.stdout.strip())
    if not match:
        raise ValueError('Could not resolve the selected CyberPanel release.')
    return match.group(1)


def verified_source(directory, commit):
    """Read files of one exact commit.

    An upgrade nobody watches must run only what the signed release names.
    git names every object by its content, so a checkout of that commit
    cannot hold anything else, whatever the server sent.
    """
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid release commit.')

    def git(*arguments):
        return subprocess.run(['git', '-C', directory] + list(arguments), check=True, timeout=300,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, env=git_environment()).stdout.strip()

    git('init', '--quiet')
    from_github(lambda: git('fetch', '--quiet', '--depth', '1', REPOSITORY, commit), 'the signed release')
    git('checkout', '--quiet', '--detach', commit)
    if git('rev-parse', 'HEAD') != commit:
        raise RuntimeError('The fetched source is not the signed release commit.')

    def read(path):
        target = Path(directory) / path
        if target.is_symlink() or not target.is_file():
            raise ValueError('Missing release file: ' + path)
        return target.read_bytes()[:2 * 1024 * 1024 + 1]
    return read


def stage_release(stage, revision, read=None):
    def download(path):
        with urlopen('%s/%s/%s' % (RAW, revision, path), timeout=30) as response:
            return response.read(2 * 1024 * 1024 + 1)

    def fetch(path):
        if read is not None:
            content = read(path)
        else:
            content = from_github(lambda: download(path), path)
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


def readable_failure(text):
    """The upgrader's last words for the upgrade page.

    A Python traceback is reduced to its final line, which names the error, and
    an endless command line is cut in the middle so both of its ends stay.
    """
    marker = 'Traceback (most recent call last):'
    text = text.strip()
    if marker in text:
        before, _, trace = text.rpartition(marker)
        final = [line.strip() for line in trace.splitlines() if line.strip()]
        text = ' '.join(part for part in (before.strip()[-600:], final[-1] if final else '') if part)
    else:
        text = text[-2000:]
    if len(text) > 900:
        text = text[:500] + ' ... ' + text[-300:]
    return text


class Stopped(RuntimeError):
    """The upgrader was stopped before it finished."""


def written(paths):
    """A value that changes whenever the upgrader writes to one of its outputs."""
    seen = []
    for path in paths:
        try:
            info = os.fstat(path) if isinstance(path, int) else os.stat(str(path))
            seen.append((info.st_size, info.st_mtime_ns))
        except OSError:
            seen.append(None)
    return tuple(seen)


def end_session(process, grace=30):
    """Stop the upgrader and what it started in its session (a hung git or apt)."""
    for number, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 10)):
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass
    process.wait()


def supervise(process, outputs, job=None, clock=time.monotonic, wall=time.time, pause=5,
              idle_limit=IDLE_LIMIT, stop_after=STOP_AFTER, longest=LONGEST):
    """Wait for the upgrader; stop it after too long without output, or on request.

    An upgrade that hangs (GitHub accepting connections but sending nothing,
    a package manager waiting on a lock) otherwise holds the upgrade lock
    and the page's "running" state until the server restarts.
    """
    started = active = clock()
    seen = written(outputs)
    noted = None
    while True:
        try:
            return process.wait(timeout=pause)
        except subprocess.TimeoutExpired:
            pass
        now = clock()
        current = written(outputs)
        if current != seen:
            seen, active = current, now
        idle = now - active
        if job is not None and (noted is None or now - noted >= 15):
            record_status(job, 'running', active=wall() - idle)
            noted = now
        reason = None
        if idle >= idle_limit:
            reason = 'The upgrade wrote nothing for %d minutes and was stopped.' % (idle // 60)
        elif now - started >= longest:
            reason = 'The upgrade was still running after %d hours and was stopped.' % (longest // 3600)
        elif job is not None and stop_path(job).exists():
            try:
                stop_path(job).unlink()
            except OSError:
                pass
            if idle >= stop_after:
                reason = ('The upgrade was stopped from the panel after it wrote nothing for %d minutes.'
                          % (idle // 60))
        if reason:
            end_session(process)
            raise Stopped(reason)


def upgrade_staging(parent=None):
    """Names of the upgrader's staging directories (.cyberpanel-upgrade-*) beside the installation."""
    return {directory.name for directory in (parent or INSTALLATION.parent).glob('.cyberpanel-upgrade-*')}


def remove_upgrade_staging(known, parent=None):
    """A stopped upgrader cannot remove the source it was staging; remove what this run created."""
    for directory in (parent or INSTALLATION.parent).glob('.cyberpanel-upgrade-*'):
        if directory.name not in known and directory.is_dir() and not directory.is_symlink():
            shutil.rmtree(str(directory), ignore_errors=True)


def read_report(path):
    """The steps the upgrader reported as not completed; empty when it reported none."""
    try:
        with open(str(path)) as source:
            incomplete = json.load(source).get('incomplete', [])
    except (OSError, ValueError, AttributeError):
        return []
    if not isinstance(incomplete, list):
        return []
    return [str(step)[:600] for step in incomplete[:30]]


def run(branch, lock_fd=None, commit=None, job=None):
    """Upgrade to the branch's current commit or, with `commit`, to exactly that one.

    Returns the steps the upgrader reported as not completed.
    """
    validate_branch(branch)
    with tempfile.TemporaryDirectory(prefix='cyberpanel-soft-upgrade-') as directory:
        stage = Path(directory)
        environment = dict(os.environ, **GIT_ENVIRONMENT)
        if commit is None:
            stage_release(stage, resolve_release(branch))
        else:
            with tempfile.TemporaryDirectory(prefix='cyberpanel-release-') as checkout:
                stage_release(stage, commit, read=verified_source(checkout, commit))
            # The upgrader installs this commit and nothing newer on the branch.
            environment['CYBERPANEL_UPGRADE_COMMIT'] = commit
        report = stage / 'report.json'
        environment['CYBERPANEL_UPGRADE_REPORT'] = str(report)
        with tempfile.TemporaryFile() as errors, tempfile.TemporaryFile() as quiet:
            # The upgrade page's worker keeps the upgrader's output in its own
            # log; an unattended run has none, so it is collected here to see
            # that the upgrader is still working.
            try:
                output = None if stat.S_ISREG(os.fstat(1).st_mode) else quiet
            except OSError:
                output = quiet
            # The service manager can terminate the launcher independently.
            # The running upgrader must retain the same flock until it exits.
            inherited = (lock_fd,) if lock_fd is not None else ()
            staging = upgrade_staging()
            process = subprocess.Popen([sys.executable, '-u', str(stage / 'upgrade.py'),
                                        'SoftUpgrade,' + branch], cwd=stage, stdout=output, stderr=errors,
                                       pass_fds=inherited, env=environment, start_new_session=True)
            outputs = [(output or sys.stdout).fileno(), errors.fileno(), '/home/cyberpanel/upgrade_logs']
            try:
                returncode = supervise(process, outputs, job)
            except Stopped:
                remove_upgrade_staging(staging)
                raise
            finally:
                if job is not None:
                    try:
                        stop_path(job).unlink()
                    except OSError:
                        pass
            if returncode:
                errors.seek(max(0, errors.tell() - 16384))
                diagnostic = readable_failure(errors.read().decode('utf-8', errors='replace'))
                raise RuntimeError('Upgrade exited with code %s. %s' % (returncode, diagnostic))
        return read_report(report)


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
    try:
        refuse_older_release(branch, installed_order())
    except ValueError as error:
        record_status(job, 'failed', str(error))
        return 1
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


def kept_installations(parent=None):
    """Names of the .cyberpanel-previous-* directories beside the installation."""
    return {directory.name for directory in (parent or INSTALLATION.parent).glob('.cyberpanel-previous-*')}


def replaced_installation(known, parent=None):
    """The installation the current upgrade set aside, if it got that far.

    The upgrader keeps the tree it replaces in a new .cyberpanel-previous-*
    directory beside the installation. `known` names the directories that were
    there before this upgrade began; a tree of an earlier upgrade is never taken.
    """
    found = None
    for directory in (parent or INSTALLATION.parent).glob('.cyberpanel-previous-*'):
        try:
            info = directory.lstat()
            tree = directory / 'CyberCP'
            if (directory.name in known or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                    or tree.is_symlink() or not tree.is_dir()):
                continue
        except OSError:
            continue
        if found is not None:
            raise RuntimeError('More than one replaced installation was found.')
        found = tree
    return found


def restore_replaced_installation(known, installation=None):
    """Put back the installation a failed upgrade replaced. True when it was put back.

    The failed tree is kept beside it for inspection; the one of an earlier
    failure is removed first so they cannot pile up.
    """
    installation = installation or INSTALLATION
    previous = replaced_installation(known, installation.parent)
    if previous is None:
        return False
    for old in installation.parent.glob('.cyberpanel-failed-*'):
        if not old.is_symlink() and old.is_dir():
            shutil.rmtree(str(old), ignore_errors=True)
    failed = Path(tempfile.mkdtemp(prefix='.cyberpanel-failed-', dir=str(installation.parent))) / 'CyberCP'
    os.rename(str(installation), str(failed))
    try:
        os.rename(str(previous), str(installation))
    except OSError:
        os.rename(str(failed), str(installation))
        raise
    try:
        previous.parent.rmdir()
    except OSError:
        pass
    return True


def recover_from_failure(known, lock_fd, error):
    """After a failed upgrade, return to the replaced installation. Gives the message to report.

    A failure before the new source went live changed nothing here and the
    panel is left alone. After that point the server would otherwise keep new
    files under old running code, or a panel that does not start.
    """
    message = str(error)
    try:
        if not restore_replaced_installation(known):
            return message
    except Exception as failure:
        return '%s The previous version could not be put back: %s' % (message, failure)
    try:
        activate_panel_runtime(lock_fd)
    except Exception as failure:
        return ('%s The previous version was put back, but the panel did not restart cleanly: %s'
                % (message, failure))
    return message + ' The previous version was put back and the panel restarted.'


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
            known = kept_installations()
            try:
                incomplete = run(branch, lock_fd=lock.fileno(), job=job)
                activation = activate_panel_runtime(lock.fileno())
            except Exception as error:
                raise RuntimeError(recover_from_failure(known, lock.fileno(), error))
            record_status(job, 'complete', activation=activation, incomplete=incomplete)
            return 0
    except Exception as error:
        record_status(job, 'failed', str(error))
        print(str(error), file=sys.stderr)
        return 1


class Busy(RuntimeError):
    """Another upgrade holds the lock; nothing was started."""


def run_unattended(branch, commit, job):
    """An upgrade to one exact commit that the server started itself. Raises unless it completed."""
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    with (STATUS_ROOT / '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Busy('Another panel upgrade is in progress.')
        record_status(job, 'running')
        known = kept_installations()
        try:
            incomplete = run(branch, lock_fd=lock.fileno(), commit=commit, job=job)
            activation = activate_panel_runtime(lock.fileno())
        except Exception as error:
            # Nobody is watching: a server must not be left on a half-installed release.
            message = recover_from_failure(known, lock.fileno(), error)
            record_status(job, 'failed', message)
            raise RuntimeError(message)
        record_status(job, 'complete', activation=activation, incomplete=incomplete)
        return activation


def request_stop(job, clock=time.time):
    """Ask a running upgrade to stop; the answer is what the upgrade page shows.

    Only an upgrade that has written nothing for STOP_AFTER can be stopped: one
    that is still working may be in the middle of a package transaction.
    """
    status = read_status(job)
    if status.get('state') not in ('starting', 'running'):
        return {'stopped': 0, 'message': 'This upgrade is not running any more.'}
    idle = idle_seconds(status, clock)
    if idle is None or idle < STOP_AFTER:
        return {'stopped': 0, 'message': 'The upgrade is still writing to its log. It can be stopped once it '
                                         'has written nothing for %d minutes.' % (STOP_AFTER // 60)}
    descriptor = os.open(str(stop_path(job)), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    os.close(descriptor)
    return {'stopped': 1, 'message': 'The upgrade is being stopped. If it had already replaced the installed '
                                     'version, the previous one is put back.'}


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--status':
        print(json.dumps(read_status(sys.argv[2])))
    elif len(sys.argv) == 3 and sys.argv[1] == '--stop':
        print(json.dumps(request_stop(sys.argv[2])))
    elif len(sys.argv) == 4 and sys.argv[1] == '--worker':
        status_path(sys.argv[3])
        require_job_scope(sys.argv[3])
        worker_io(sys.argv[3])
        sys.exit(run_panel_job(sys.argv[2], sys.argv[3], require_admission=True))
    else:
        sys.exit(launch_panel_job(sys.argv[1], sys.argv[2]))
