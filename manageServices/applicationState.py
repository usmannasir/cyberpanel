"""What is true about a one-click service of the Applications page.

The page shows what is on the server when it is opened: whether the service's
program is present and whether its systemd unit is active. The installer
leaves a marker file under /home/cyberpanel, but a marker outlives a failed
installation and a removal done by hand, so it is never read to decide what
the page shows. It is written only after the program and the running unit
have both been seen, and taken away whenever that is not so.

This module imports nothing from the panel, so the installer (root) and the
page (the panel's own account) share one definition of "installed".
"""
import os
import re
import subprocess

INSTALLED = 'Installed'
STOPPED = 'Stopped'
NOT_INSTALLED = 'Not-Installed'

APPLICATIONS = {
    'Redis': {
        'marker': '/home/cyberpanel/redis',
        'program': '/usr/bin/redis-server',
        'unit': 'redis',
        'debian_unit': 'redis-server',
    },
    'Elasticsearch': {
        'marker': '/home/cyberpanel/elasticsearch',
        'program': '/usr/share/elasticsearch/bin/elasticsearch',
        'unit': 'elasticsearch',
        'debian_unit': 'elasticsearch',
    },
}

# apt and dpkg stop at once when another package operation holds their lock.
LOCK_HELD = re.compile(
    r'Could not get lock|Unable to acquire the dpkg frontend lock|Unable to lock '
    r'|lock was locked by another process|is locked by another process', re.I)
ERROR_LINE = re.compile(r'\s*(E:|Error:|dpkg: error)', re.I)

LOCK_REASON = ('The package manager is busy with another installation or update (its lock is held). '
               'Wait for that to finish, then try again.')


def unit_name(name, debian):
    return APPLICATIONS[name]['debian_unit' if debian else 'unit']


def program_present(name, exists=os.path.exists):
    return bool(exists(APPLICATIONS[name]['program']))


def is_active(reply):
    """Whether the reply of `systemctl is-active UNIT` says the unit is running."""
    return str(reply or '').strip() == 'active'


def state(name, debian, unit_reply, exists=os.path.exists):
    """What the page shows for an application.

    unit_reply(unit) returns what `systemctl is-active` printed for the unit;
    it is only asked when the program is on the server.
    """
    if not program_present(name, exists):
        return NOT_INSTALLED
    if is_active(unit_reply(unit_name(name, debian))):
        return INSTALLED
    return STOPPED


def failure_reason(output):
    """Why the package manager did not do what it was asked, in a sentence for the administrator."""
    output = output or ''
    if LOCK_HELD.search(output):
        return LOCK_REASON
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    errors = [line for line in lines if ERROR_LINE.match(line)] or lines[-1:]
    if not errors:
        return 'The package manager gave no reason.'
    return 'The package manager reported: %s' % ' '.join(errors[-3:])


def run_logged(command, log):
    """Run a shell command and copy what it prints to the log file while it runs.

    Returns (exit status, output). The output is copied as bytes, so a
    package manager that prints in another encoding cannot stop the copy.
    """
    process = subprocess.Popen(command, shell=True, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    collected = []
    while True:
        chunk = process.stdout.read1(4096)
        if not chunk:
            break
        os.write(log.fileno(), chunk)
        collected.append(chunk)
    process.stdout.close()
    return process.wait(), b''.join(collected).decode('utf-8', 'replace')


def remember(name):
    with open(APPLICATIONS[name]['marker'], 'a'):
        pass


def forget(name):
    try:
        os.remove(APPLICATIONS[name]['marker'])
    except OSError:
        pass


def install(name, package_command, debian, log, configure=None, run=run_logged, exists=os.path.exists):
    """Install an application's package, start its service and say what is true afterwards.

    Returns (True, message) only when the program is present and the unit is
    active; the marker is written in that case alone. The verdict follows
    what is on the server, not what the package manager returned: a status of
    0 with no program is a failure, and a program that was already there is
    started even when the package manager could not run.
    """
    status, output = run(package_command, log)
    if not program_present(name, exists):
        forget(name)
        return False, '%s was not installed. %s' % (name, failure_reason(output))

    if configure is not None:
        configure()

    unit = unit_name(name, debian)
    run('systemctl enable %s' % unit, log)
    run('systemctl start %s' % unit, log)
    if not is_active(run('systemctl is-active %s' % unit, log)[1]):
        forget(name)
        return False, ('%s is installed, but its service (%s) is not running. Run "journalctl -u %s" '
                       'for the reason, then use Start service on this page.' % (name, unit, unit))

    remember(name)
    if status != 0:
        return True, ('%s is installed and running, but the package manager ended with an error. %s'
                      % (name, failure_reason(output)))
    return True, '%s successfully installed.' % name


def record(name, debian, log, run=run_logged, exists=os.path.exists):
    """Make the marker say what is on the server now."""
    if program_present(name, exists) and is_active(run('systemctl is-active %s' % unit_name(name, debian), log)[1]):
        remember(name)
    else:
        forget(name)


def remove(name, package_command, debian, log, run=run_logged, exists=os.path.exists):
    """Remove an application's package and say what is true afterwards.

    Returns (True, message) only when the program is gone.
    """
    status, output = run(package_command, log)
    if program_present(name, exists):
        record(name, debian, log, run, exists)
        return False, '%s was not removed. %s' % (name, failure_reason(output))
    forget(name)
    return True, '%s successfully removed.' % name
