"""Step-by-step status of a fresh installation.

cyberpanel.sh starts a run, names it and records its own steps in
/var/log/cyberpanel/install_events.log. While this installer works it adds
the lines for its part to the same file, so that a program following the
installation (the install page on cyberpanel.net) can show where it is
without reading the terminal output:

    <unix seconds> <run id> <step> <state>

cyberpanel.sh marks "web_server" as running before it starts install.py and
passes the name of the run in the environment. Without that name nothing is
written, so install.py run by hand leaves the file alone.

A step that is still running when the installer stops is closed as failed by
cyberpanel.sh, which sees the exit status. This module never writes "failed".
"""
import os
import re
import time

EVENTS_FILE = '/var/log/cyberpanel/install_events.log'
RUN_ID_VARIABLE = 'CP_INSTALL_RUN_ID'

# The steps of this installer, in the order it goes through them.
STEPS = ('web_server', 'php', 'database', 'ftp', 'dns', 'email', 'panel')

_RUN_ID = re.compile(r'[0-9a-f]{32}')

# cyberpanel.sh has already recorded this one as running.
_running = STEPS[0]


def _write(step, state):
    run_id = os.environ.get(RUN_ID_VARIABLE, '')
    if not _RUN_ID.fullmatch(run_id):
        return
    line = '%d %s %s %s\n' % (int(time.time()), run_id, step, state)
    try:
        # One short write on a descriptor opened for appending: the shell
        # installer appends to the same file in the same way.
        descriptor = os.open(EVENTS_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(descriptor, line.encode('ascii'))
        finally:
            os.close(descriptor)
    except OSError:
        # Status reporting must never stop an installation.
        pass


def step(name, enabled=True):
    """Start a step, or record that it is left out.

    The step that was running is closed as done first. Starting the step
    that is already running changes nothing.
    """
    global _running
    if name not in STEPS or name == _running:
        return
    finish()
    if enabled:
        _write(name, 'running')
        _running = name
    else:
        _write(name, 'skipped')


def finish():
    """Close the step that is running as done."""
    global _running
    if _running is not None:
        _write(_running, 'done')
        _running = None
