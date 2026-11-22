"""Install the terminal unit without overriding an operator's service policy."""
import os
import shutil
import subprocess
import sys
import time

SERVICE = 'fastapi_ssh_server.service'
# The interpreter named in the unit's ExecStart. A fresh installation creates
# it after install.py has finished, and an upgrade may rebuild it.
INTERPRETER = '/usr/local/CyberCP/bin/python'
PROPERTIES = ('LoadState', 'UnitFileState', 'ActiveState', 'Result', 'ExecMainCode',
              'ExecMainStatus', 'NRestarts')
# A started unit is looked at once a second, this many times, before it is called running.
SETTLE_CHECKS = 5


def main_process_not_executed(state):
    """Whether the unit failed because systemd could not execute its main process.

    That is exit status 203 (EXEC) of a process that exited by itself. It is
    what a start before the interpreter existed leaves behind, and it cannot
    be the end of a session that was running: a stop that timed out, a crash
    or a kill for memory all report something else.
    """
    return (state.get('Result') in ('exit-code', 'start-limit-hit')
            and state.get('ExecMainCode') == '1' and state.get('ExecMainStatus') == '203')


def plan_terminal_start(state, interpreter_ready, start_stopped=False):
    """Decide whether the Web Terminal has to be started. Pure: returns (outcome, commands).

    state holds the unit's systemd properties (PROPERTIES). Only a unit the
    administrator left enabled is ever started. At the end of a fresh
    installation (start_stopped) it is started whether stopped or failed.
    Otherwise a stopped unit stays stopped, and a failed unit is cleared and
    started only if its main process could not be executed; any other failure
    may be the administrator's doing and is left for the administrator.
    """
    load, enabled, active = (state.get(name, '') for name in PROPERTIES[:3])
    if load == 'masked' or enabled.startswith('masked'):
        return 'masked', []
    if load != 'loaded':
        return 'not-loaded', []
    if enabled != 'enabled':
        return 'not-enabled', []
    if active == 'failed':
        if not start_stopped and not main_process_not_executed(state):
            return 'failed', []
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


def _state(run):
    shown = run(['systemctl', 'show'] + ['--property=' + name for name in PROPERTIES] + [SERVICE])
    if shown.returncode != 0:
        raise RuntimeError('Cannot determine Web Terminal service state: '
                           + (shown.stderr or shown.stdout or '').strip())
    return dict(line.split('=', 1) for line in shown.stdout.splitlines() if '=' in line)


def _running(state):
    """Active, and not because systemd has just restarted it after it died."""
    return state.get('ActiveState') == 'active' and state.get('NRestarts', '0') in ('', '0')


def _described(state):
    return ', '.join('%s=%s' % (name, state.get(name, '')) for name in PROPERTIES[2:])


def start_terminal_service(*, start_stopped=False, interpreter=INTERPRETER, run=_systemctl):
    """Apply plan_terminal_start. Returns (outcome, note); the note is for the administrator.

    'started' means the unit was started and was still running SETTLE_CHECKS
    seconds later; 'not-running' means it was started and did not stay up.
    """
    state = _state(run)
    ready = os.path.isfile(interpreter) and os.access(interpreter, os.X_OK)
    outcome, commands = plan_terminal_start(state, ready, start_stopped)
    if outcome == 'failed':
        return outcome, ('Web Terminal service is enabled but in failed state (%s). It was left as it is, '
                         'because this is not the failure of a start before its interpreter existed. '
                         'To run it: systemctl reset-failed %s && systemctl start %s. '
                         'To keep it off: systemctl disable %s.' % (_described(state), SERVICE, SERVICE, SERVICE))
    for command in commands:
        result = run(command)
        if result.returncode != 0:
            raise RuntimeError('%s failed: %s' % (' '.join(command),
                                                  (result.stderr or result.stdout or '').strip()))
    if commands:
        for _ in range(SETTLE_CHECKS):
            time.sleep(1)
            state = _state(run)
            if not _running(state):
                return 'not-running', ('Web Terminal service was started but did not stay running (%s). '
                                       'See: journalctl -u %s' % (_described(state), SERVICE))
    return outcome, ''


def configure_terminal_service(*, fresh_install=False,
                               source='/usr/local/CyberCP/fastapi_ssh_server.service',
                               target='/etc/systemd/system/fastapi_ssh_server.service',
                               interpreter=INTERPRETER):
    """Install the unit file. Returns (outcome, note); the note is for the administrator."""
    service = SERVICE
    load = subprocess.run(['systemctl', 'show', '--property=LoadState', '--value', service],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, check=True).stdout.strip()
    if load == 'masked' or (os.path.islink(target) and os.path.realpath(target) == '/dev/null'):
        return 'masked', ''
    if load not in ('loaded', 'not-found'):
        raise RuntimeError('Cannot determine Web Terminal service state: ' + load)
    present = load == 'loaded' or os.path.lexists(target)
    if not present and not fresh_install:
        return 'absent', ''
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
        return 'enabled', start_terminal_service(start_stopped=True, interpreter=interpreter)[1]
    if active:
        subprocess.run(['systemctl', 'restart', service],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
        return 'restarted', ''
    # A stopped unit stays stopped. An enabled unit whose main process could
    # not be executed is started again; any other failed unit is reported.
    outcome, note = start_terminal_service(interpreter=interpreter)
    if outcome in ('started', 'not-running', 'failed'):
        return outcome, note
    return 'inactive', ''


def main(arguments, interpreter=INTERPRETER, run=_systemctl):
    """start-installed: end of a fresh installation. repair: end of an upgrade."""
    if arguments not in (['start-installed'], ['repair']):
        sys.stderr.write('usage: terminalService.py start-installed|repair\n')
        return 2
    try:
        outcome, note = start_terminal_service(start_stopped=arguments[0] == 'start-installed',
                                               interpreter=interpreter, run=run)
    except Exception as error:
        sys.stderr.write('Web Terminal service: %s\n' % error)
        return 1
    print('Web Terminal service: ' + outcome)
    if note:
        print(note)
    return 1 if outcome == 'not-running' else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
