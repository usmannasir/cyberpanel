"""Launch a panel-initiated upgrade with the selected release's own Python helpers."""
import ast
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
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


def record_status(job, state, message=''):
    path = status_path(job)
    STATUS_ROOT.mkdir(exist_ok=True, mode=0o755)
    with tempfile.NamedTemporaryFile(mode='w', dir=STATUS_ROOT, delete=False) as output:
        record = {'state': state, 'message': message}
        if state in ('starting', 'running'):
            record['pid'] = os.getpid()
            record['start_ticks'] = live_start_ticks(Path('/proc/self/stat').read_text())
        json.dump(record, output)
        os.chmod(output.name, 0o600)
    os.replace(output.name, path)


def resolve_release(branch):
    if not re.fullmatch(r'stable|v[0-9]+(?:\.[0-9]+)+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?', branch):
        raise ValueError('Select a stable CyberPanel release branch.')
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
            fetch(path)


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


def run_panel_job(branch, job):
    record_status(job, 'starting')
    try:
        with (STATUS_ROOT / '.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Another panel upgrade is in progress.')
            record_status(job, 'running')
            run(branch, lock_fd=lock.fileno())
            record_status(job, 'complete')
            return 0
    except Exception as error:
        record_status(job, 'failed', str(error))
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--status':
        print(json.dumps(read_status(sys.argv[2])))
    else:
        sys.exit(run_panel_job(sys.argv[1], sys.argv[2]))
