"""Install the terminal unit without overriding an operator's service policy."""
import os
import shutil
import subprocess
import sys

SERVICE = 'fastapi_ssh_server.service'
# The interpreter named in the unit's ExecStart. A fresh installation creates
# it after install.py has finished, and an upgrade may rebuild it.
INTERPRETER = '/usr/local/CyberCP/bin/python'


def plan_terminal_start(load, enabled, active, interpreter_ready, start_stopped=False):
    """Decide whether the Web Terminal has to be started. Pure: returns (outcome, commands).

    Only a unit the administrator left enabled is ever started. A failed unit
    is cleared and started; a unit that is merely stopped is started only when
    start_stopped is set, which is the end of a fresh installation.
    """
    if load == 'masked' or enabled.startswith('masked'):
        return 'masked', []
    if load != 'loaded':
        return 'not-loaded', []
    if enabled != 'enabled':
        return 'not-enabled', []
    if active == 'failed':
        if not interpreter_ready:
            return 'not-ready', []
        return 'started', [['systemctl', 'reset-failed', SERVICE], ['systemctl', 'start', SERVICE]]
    if active == 'inactive':
        if not start_stopped:
            return 'stopped', []
        if not interpreter_ready:
            return 'not-ready', []
        return 'started', [['systemctl', 'start', SERVICE]]
    # active, or systemd is already changing its state
    return 'unchanged', []


def _systemctl(command):
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def start_terminal_service(*, start_stopped=False, interpreter=INTERPRETER, run=_systemctl):
    """Start the enabled Web Terminal once its interpreter exists; see plan_terminal_start."""
    shown = run(['systemctl', 'show', '--property=LoadState', '--property=UnitFileState',
                 '--property=ActiveState', SERVICE])
    if shown.returncode != 0:
        raise RuntimeError('Cannot determine Web Terminal service state: '
                           + (shown.stderr or shown.stdout or '').strip())
    state = dict(line.split('=', 1) for line in shown.stdout.splitlines() if '=' in line)
    ready = os.path.isfile(interpreter) and os.access(interpreter, os.X_OK)
    outcome, commands = plan_terminal_start(state.get('LoadState', ''), state.get('UnitFileState', ''),
                                            state.get('ActiveState', ''), ready, start_stopped)
    for command in commands:
        result = run(command)
        if result.returncode != 0:
            raise RuntimeError('%s failed: %s' % (' '.join(command),
                                                  (result.stderr or result.stdout or '').strip()))
    return outcome


def configure_terminal_service(*, fresh_install=False,
                               source='/usr/local/CyberCP/fastapi_ssh_server.service',
                               target='/etc/systemd/system/fastapi_ssh_server.service',
                               interpreter=INTERPRETER):
    service = SERVICE
    load = subprocess.run(['systemctl', 'show', '--property=LoadState', '--value', service],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, check=True).stdout.strip()
    if load == 'masked' or (os.path.islink(target) and os.path.realpath(target) == '/dev/null'):
        return 'masked'
    if load not in ('loaded', 'not-found'):
        raise RuntimeError('Cannot determine Web Terminal service state: ' + load)
    present = load == 'loaded' or os.path.lexists(target)
    if not present and not fresh_install:
        return 'absent'
    active = subprocess.run(['systemctl', 'is-active', '--quiet', service],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True).returncode == 0
    shutil.copy2(source, target)
    subprocess.run(['systemctl', 'daemon-reload'], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if not present and fresh_install:
        # Enabled here, started by the installer once the interpreter exists
        # ("terminalService.py start-installed"). If it already exists, start now.
        subprocess.run(['systemctl', 'enable', service],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
        start_terminal_service(start_stopped=True, interpreter=interpreter)
        return 'enabled'
    if active:
        subprocess.run(['systemctl', 'restart', service],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
        return 'restarted'
    # A stopped unit stays stopped; an enabled unit left in failed state is started again.
    if start_terminal_service(interpreter=interpreter) == 'started':
        return 'started'
    return 'inactive'


def main(arguments, interpreter=INTERPRETER, run=_systemctl):
    """start-installed: end of a fresh installation. repair: end of an upgrade."""
    if arguments not in (['start-installed'], ['repair']):
        sys.stderr.write('usage: terminalService.py start-installed|repair\n')
        return 2
    try:
        outcome = start_terminal_service(start_stopped=arguments[0] == 'start-installed',
                                         interpreter=interpreter, run=run)
    except Exception as error:
        sys.stderr.write('Web Terminal service: %s\n' % error)
        return 1
    print('Web Terminal service: ' + outcome)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
