"""Bring the panel's own runtime up to the release during an upgrade started from the panel.

A command-line upgrade installs the release's Python requirements and the
panel server (lscpd) in cyberpanel_upgrade.sh. An upgrade started from the
Version Management page runs only the Python upgrader, so a server upgraded
there kept the packages and the server binary it was installed with. An x86
server with glibc 2.25 or later installed before 20 Oct 2026, for instance,
still ran lscpd 0.3.1, which ends large phpMyAdmin exports early.

Both steps leave a server that is already up to date alone: they then change
nothing and need no network.
"""
import hashlib
import json
import os
import subprocess
import time

ROOT = '/usr/local/CyberCP'
PYTHON = ROOT + '/bin/python'
SERVER = '/usr/local/lscp/bin/lscpd'
SYSTEMCTL = '/usr/bin/systemctl'

# Run by the panel's own interpreter: prints the lines of a requirements file
# it does not satisfy. Python 3.6 (AlmaLinux 8) has no importlib.metadata.
CHECK = r'''
import json, re, sys

def key(name):
    return re.sub(r'[-_.]+', '-', name or '').lower()

installed = {}
try:
    from importlib.metadata import distributions
    found = [(item.metadata['Name'], item.version) for item in distributions()]
except ImportError:
    import pkg_resources
    found = [(item.project_name, item.version) for item in pkg_resources.working_set]
for name, version in found:
    # The first one on the path is the one an import loads.
    installed.setdefault(key(name), version)
try:
    from packaging.markers import Marker
    from packaging.specifiers import SpecifierSet
except ImportError:
    Marker = SpecifierSet = None

unmet = []
with open(sys.argv[1], encoding='utf-8') as source:
    for raw in source:
        line = raw.split('#', 1)[0].strip()
        if not line or line.startswith('-'):
            continue
        requirement, _, marker = line.partition(';')
        match = re.match(r'([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$', requirement.strip())
        try:
            if marker.strip() and Marker is not None and not Marker(marker.strip()).evaluate():
                continue
            have = installed.get(key(match.group(1))) if match else None
            wanted = match.group(3).strip() if match else ''
            if have is None:
                met = False
            elif not wanted:
                met = True
            elif SpecifierSet is not None:
                met = SpecifierSet(wanted).contains(have, prereleases=True)
            else:
                met = not wanted.startswith('==') or wanted[2:].strip() == have
        except Exception:
            met = False
        if not met:
            unmet.append(line)
print(json.dumps(unmet))
'''


def requirements_name(os_release='/etc/os-release'):
    """The requirements file cyberpanel_upgrade.sh installs on this system."""
    version = ''
    with open(os_release) as source:
        for line in source:
            if 'VERSION_ID' in line:
                version = line.split('=', 1)[-1].strip().replace('"', '')
                break
    # As Download_Requirement: the first two characters of VERSION_ID without dots.
    return 'requirments.txt' if version[:2].replace('.', '') in ('22', '24', '26', '9', '10') \
        else 'requirments-old.txt'


def clean_environment():
    # The panel service sets PYTHONHOME for its worker; these commands must not inherit it.
    environment = {name: value for name, value in os.environ.items()
                   if name not in ('PYTHONHOME', 'PYTHONPATH')}
    environment['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    return environment


def unmet_requirements(requirements, python=PYTHON, timeout=180):
    result = subprocess.run([python, '-I', '-c', CHECK, requirements], env=clean_environment(),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('the Python requirements of the release could not be checked: '
                           + result.stderr.strip()[-300:])
    unmet = json.loads(result.stdout)
    if not isinstance(unmet, list) or not all(isinstance(line, str) for line in unmet):
        raise RuntimeError('the Python requirements check gave an unexpected answer')
    return unmet


def install_requirements(root=ROOT, python=PYTHON, name=None, log=print, run=subprocess.run):
    """Install what the release requires and the panel's interpreter lacks; raise when pip fails.

    pip runs only when something is missing or at another version, so an
    upgrade whose requirements did not change does not depend on PyPI.
    """
    requirements = os.path.join(root, name or requirements_name())
    if not os.path.isfile(requirements):
        raise RuntimeError('the release has no %s' % os.path.basename(requirements))
    missing = unmet_requirements(requirements, python)
    if not missing:
        return {'state': 'current', 'file': os.path.basename(requirements)}
    log('Installing the Python requirements of this release that the panel lacks: ' + ', '.join(missing))
    # pip's own output goes to the upgrade output, so the launcher sees it working.
    result = run([python, '-m', 'pip', 'install', '--default-timeout=120', '--retries=3',
                  '-r', requirements], env=clean_environment(), stdin=subprocess.DEVNULL, timeout=3600)
    if result.returncode:
        raise RuntimeError('pip ended with status %d while installing %s'
                           % (result.returncode, ', '.join(missing)))
    # pip is the authority on what it installed: a line this check still reads
    # as unmet after pip succeeded is reported, not made an upgrade failure.
    return {'state': 'installed', 'file': os.path.basename(requirements), 'installed': missing,
            'unconfirmed': unmet_requirements(requirements, python)}


def digest(path):
    with open(path, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def restart_panel():
    subprocess.run([SYSTEMCTL, 'restart', 'lscpd'], check=True, timeout=90,
                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def wait_for_panel(probe=None, timeout=90, clock=time.monotonic, sleep=time.sleep):
    """Wait until the panel returns its login page over its own certificate."""
    if probe is None:
        from plogical.softUpgrade import probe_panel as probe
    deadline = clock() + timeout
    while True:
        try:
            return probe()
        except Exception as error:
            if clock() >= deadline:
                raise RuntimeError('the panel did not answer: %s' % error)
        sleep(1)


def install_panel_server(selection, install, root=ROOT, server=SERVER,
                         restart=restart_panel, ready=wait_for_panel):
    """Run the panel on the release's server binary for this host, or raise.

    `install(source, destination)` copies an executable atomically. The
    panel is restarted at once: the launcher of every release since 3.0.9
    checks that the running panel is the installed executable. If the panel
    does not answer on the new binary, the previous one is put back.
    """
    source = os.path.join(root, selection)
    wanted = digest(source)
    try:
        current = digest(server)
    except FileNotFoundError:
        current = None
    if current == wanted:
        return {'state': 'current', 'binary': selection}
    previous = None
    if current is not None:
        previous = os.path.join(os.path.dirname(server), '.' + os.path.basename(server) + '.previous')
        install(server, previous)
    try:
        install(source, server)
        try:
            restart()
            ready()
        except Exception as error:
            if previous is None:
                raise RuntimeError('the panel did not start on %s: %s' % (selection, error))
            install(previous, server)
            try:
                restart()
                ready()
            except Exception as second:
                raise RuntimeError('the panel did not start on %s (%s), nor on the previous binary '
                                   'that was put back (%s)' % (selection, error, second))
            raise RuntimeError('the panel did not start on %s (%s); the previous binary was put back '
                               'and the panel runs on it' % (selection, error))
    finally:
        if previous is not None and os.path.exists(previous):
            os.unlink(previous)
    return {'state': 'replaced', 'binary': selection, 'sha256': wanted}
