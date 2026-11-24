"""Keep this server's CyberPanel up to date without an administrator present.

    autoUpdate.py run               the hourly timer's entry
    autoUpdate.py check             look for a release now; installs nothing
    autoUpdate.py status            settings and state as JSON, for the panel page
    autoUpdate.py configure HEX     save settings (hex of their JSON text), switch the timer
    autoUpdate.py schedule          write the timer units (installer and upgrader)
    autoUpdate.py install JOB       internal: the upgrade itself, in its own scope

Off unless an administrator turns it on. A release is installed only when
CyberPanel signed it (plogical/releaseManifest.py), it names a commit this
server does not have, the waiting time set by the publisher has passed and it
is the hour the administrator chose. One attempt is made per release; a failure
is reported and left for a person.
"""
import fcntl
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # The timer runs this file in Python's isolated mode, which leaves the
    # installation out of the import path.
    sys.path.insert(0, str(ROOT))

from plogical import releaseManifest  # noqa: E402

SETTINGS = Path('/etc/cyberpanel/auto-update.json')
STATE = Path('/var/lib/cyberpanel-auto-update')
UNITS = Path('/etc/systemd/system')
INSTALLATION = Path('/usr/local/CyberCP')
PYTHON = '/usr/local/CyberCP/bin/python'
SYSTEMCTL = '/usr/bin/systemctl'
SYSTEMD_RUN = '/usr/bin/systemd-run'
SERVICE = 'cyberpanel-auto-update.service'
TIMER = 'cyberpanel-auto-update.timer'
MODES = ('off', 'notify', 'install')
DEFAULTS = {'mode': 'off', 'hour': 3, 'email': ''}
CHECK_EVERY = 6 * 3600
MINIMUM_FREE = 3 * 1024 ** 3
BUSY = 3

SERVICE_UNIT = '''[Unit]
Description=CyberPanel automatic update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
Environment=HOME=/root LANG=C.UTF-8 PYTHONIOENCODING=utf-8
ExecStart=%s -I %s run
TimeoutStartSec=5h
''' % (PYTHON, INSTALLATION / 'plogical' / 'autoUpdate.py')

TIMER_UNIT = '''[Unit]
Description=Hourly check for the CyberPanel automatic update

[Timer]
OnCalendar=hourly
RandomizedDelaySec=900

[Install]
WantedBy=timers.target
'''


def checked_settings(values):
    """The settings as stored, or ValueError naming what is wrong."""
    if not isinstance(values, dict) or sorted(values) != sorted(DEFAULTS):
        raise ValueError('Unexpected settings.')
    mode, hour, email = values['mode'], values['hour'], values['email']
    if mode not in MODES:
        raise ValueError('Choose off, notify or install.')
    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError('Choose an hour from 0 to 23.')
    if not isinstance(email, str) or (email and not re.fullmatch(
            r'[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){1,8}', email)):
        raise ValueError('Enter one valid e-mail address, or none.')
    return {'mode': mode, 'hour': hour, 'email': email}


def write_private(path, text):
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(dir=str(path.parent), prefix='.' + path.name + '.')
    try:
        with os.fdopen(descriptor, 'w') as output:
            output.write(text)
            os.fchmod(output.fileno(), 0o600)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def spread_offset(identity, release):
    """Where in the publisher's spread window this server takes its turn, in seconds."""
    window = release['spread_hours'] * 3600
    if not window:
        return 0
    seed = hashlib.sha256((identity + release['commit']).encode()).hexdigest()
    return int(seed[:12], 16) % window


def label(release):
    return '%s.%s' % (release['version'], release['build'])


def named(release, current):
    """How a release is called in messages: a new version, or newer files of the installed one."""
    same = current and (release['version'], release['build']) == (current['version'], current['build'])
    return ('An update of version %s' if same else 'Version %s') % label(release)


def failed_summary(release, reason):
    return ('The automatic installation of version %s did not succeed: %s '
            'It will not be tried again. After checking the reason, the release can be installed '
            'from the Version Management page.' % (label(release), reason if reason.endswith('.') else reason + '.'))


def when(moment):
    return time.strftime('%d %b %Y %H:%M UTC', time.gmtime(moment))


class Updater:
    """One server's automatic update. Collaborators are replaceable for tests."""

    def __init__(self, settings=SETTINGS, state=STATE, installation=INSTALLATION, units=UNITS,
                 fetch=releaseManifest.fetch, verify=releaseManifest.verified, clock=time.time,
                 mail=None, upgrade=None, command=None, free=None):
        self.settings_path, self.state_directory = Path(settings), Path(state)
        self.installation, self.units = Path(installation), Path(units)
        self.fetch, self.verify, self.clock = fetch, verify, clock
        self.mail = mail or self.send_mail
        self.upgrade = upgrade or self.upgrade_in_scope
        self.command = command or self.system_command
        self.free = free or (lambda: shutil.disk_usage(str(self.installation.parent)).free)

    # ---- stored settings and state ------------------------------------------------

    def settings(self):
        """A missing or damaged settings file means off."""
        try:
            return checked_settings(json.loads(self.settings_path.read_text()))
        except (OSError, ValueError):
            return dict(DEFAULTS)

    def state(self):
        try:
            state = json.loads((self.state_directory / 'state.json').read_text())
            return state if isinstance(state, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_state(self, state):
        self.state_directory.mkdir(mode=0o700, exist_ok=True)
        write_private(self.state_directory / 'state.json', json.dumps(state, indent=1, sort_keys=True) + '\n')

    def lock(self):
        self.state_directory.mkdir(mode=0o700, exist_ok=True)
        handle = (self.state_directory / 'lock').open('a')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return None
        return handle

    # ---- what is installed, what is published --------------------------------------

    def git(self, *arguments):
        return subprocess.run(['git', '-C', str(self.installation)] + list(arguments), timeout=60,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True)

    def installed(self):
        from plogical import softUpgrade
        release = softUpgrade.installed_order(self.installation)
        commit = self.git('rev-parse', 'HEAD').stdout.strip()
        if release is None or not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise RuntimeError('The installed version cannot be read.')
        return {'version': '.'.join(str(part) for part in release[:-1]), 'build': release[-1], 'commit': commit}

    def contains(self, commit):
        """True when the installed source already includes that commit."""
        return self.git('merge-base', '--is-ancestor', commit, 'HEAD').returncode == 0

    def look(self, state):
        """Fetch and verify the published release; never moves back to an older one."""
        state['checked'] = int(self.clock())
        try:
            document = self.fetch()
        except Exception as error:
            state['error'] = 'The release information could not be fetched: %s' % str(error)[:200]
            return
        try:
            release = self.verify(document)
        except releaseManifest.Unavailable as error:
            state['error'] = str(error)
            return
        except Exception as error:
            state['error'] = 'The release information could not be verified: %s' % str(error)[:200]
            return
        known = state.get('release')
        if known and (release['sequence'] < known['sequence'] or (
                release['sequence'] == known['sequence'] and release != known)):
            state['error'] = 'Older release information was offered and ignored.'
            return
        state['error'] = ''
        state['release'] = release

    # ---- the decision ---------------------------------------------------------------

    def plan(self, settings, state, current, identity):
        """(action, summary, blocked). action is '', 'notify' or 'install'."""
        release = state.get('release')
        if not release:
            return '', state.get('error') or 'No release information yet.', ''
        name = named(release, current)
        if release['commit'] == current['commit'] or self.contains(release['commit']):
            return '', 'This server has the current release (%s).' % label(release), ''
        if releaseManifest.order(release['version'], release['build']) < releaseManifest.order(
                current['version'], current['build']):
            return '', 'This server runs a newer version than the published release.', ''
        if release['hold']:
            return '', 'CyberPanel has paused the automatic installation of version %s.' % label(release), ''
        if settings['mode'] == 'off':
            return '', '%s is available.' % name, ''
        if settings['mode'] == 'notify':
            return 'notify', '%s is available. It can be installed from the Version Management page.' % name, ''
        attempt = state.get('attempt') or {}
        if attempt.get('commit') == release['commit'] and attempt.get('result') != 'installed':
            return '', failed_summary(release, attempt.get('message') or 'it did not finish'), ''
        eligible = releaseManifest.published_time(release) + release['soak_hours'] * 3600 \
            + spread_offset(identity, release)
        now = self.clock()
        if now < eligible:
            return '', '%s will be installed automatically after %s, at %02d:00 server time.' % (
                name, when(eligible), settings['hour']), ''
        blocked = self.blocked()
        if blocked:
            return '', '%s cannot be installed automatically: %s' % (name, blocked), blocked
        if time.localtime(now).tm_hour != settings['hour']:
            return '', '%s will be installed automatically at %02d:00 server time.' % (
                name, settings['hour']), ''
        return 'install', '%s is being installed.' % name, ''

    def blocked(self):
        """A reason an installation cannot start now; these are not counted as attempts."""
        if os.path.lexists('/etc/csf'):
            return 'CSF is installed and needs the manual firewall migration first.'
        if self.free() < MINIMUM_FREE:
            return 'less than 3 GB of disk space is free.'
        return ''

    # ---- acting -----------------------------------------------------------------------

    def run(self, check_only=False):
        settings = self.settings()
        if settings['mode'] == 'off' and not check_only:
            return 0
        lock = self.lock()
        if lock is None:
            return 0
        with lock:
            state = self.state()
            self.finish_interrupted(state)
            due = self.clock() - state.get('checked', 0) >= CHECK_EVERY
            if check_only or due or time.localtime(self.clock()).tm_hour == settings['hour']:
                self.look(state)
            current = self.installed()
            action, summary, blocked = self.plan(settings, state, current, self.identity())
            state['summary'] = summary
            release = state.get('release') or {}
            if check_only:
                self.save_state(state)
                return 0
            if blocked and state.get('blocked') != [release.get('commit'), blocked]:
                state['blocked'] = [release.get('commit'), blocked]
                self.report(settings, 'needs attention', summary)
            if action == 'notify' and state.get('notified') != release['commit']:
                state['notified'] = release['commit']
                self.report(settings, 'version %s is available' % label(release), summary)
            self.save_state(state)
            if action == 'install':
                self.install(settings, state, release)
        return 0

    def finish_interrupted(self, state):
        attempt = state.get('attempt')
        if attempt and 'result' not in attempt:
            attempt.update(result='failed', finished=int(self.clock()),
                           message='the installation was interrupted before it finished')

    def install(self, settings, state, release):
        job = uuid.uuid4().hex
        state['attempt'] = {'commit': release['commit'], 'branch': release['branch'], 'job': job,
                            'started': int(self.clock())}
        self.save_state(state)
        status, message, incomplete = self.upgrade(job)
        if status == BUSY:
            # Somebody is upgrading from the panel right now; this was not an attempt.
            del state['attempt']
            state['summary'] = 'Another upgrade was running. Version %s stays scheduled.' % label(release)
            self.save_state(state)
            return
        attempt = state['attempt']
        attempt['finished'] = int(self.clock())
        try:
            commit = self.installed()['commit']
        except Exception:
            commit = ''
        if status == 0 and commit == release['commit']:
            attempt.update(result='installed', message='')
            state['summary'] = 'Version %s was installed automatically on %s.' % (label(release), when(attempt['finished']))
            subject = 'version %s was installed' % label(release)
            if incomplete:
                # Installed, but not a plain success: say which steps to look at.
                attempt['incomplete'] = incomplete
                state['summary'] += (' These steps did not complete; running the upgrade again from Version '
                                     'Management repeats them: ' + '; '.join(incomplete))
                subject += ', but some steps did not complete'
        else:
            attempt.update(result='failed', message=(message or 'the upgrade ended with status %s' % status)[:1000])
            state['summary'] = failed_summary(release, attempt['message'])
            subject = 'version %s could NOT be installed' % label(release)
        self.save_state(state)
        self.report(settings, subject, state['summary'])

    def upgrade_in_scope(self, job):
        """Run the upgrade as the panel's own upgrade page does: in an independent scope.

        Gives the exit status, the failure message and the steps that did not complete.
        """
        from plogical import softUpgrade
        result = subprocess.run([SYSTEMD_RUN, '--scope', '--quiet', '--slice=system.slice',
                                 '--unit=cyberpanel-auto-update-' + job, '--',
                                 sys.executable, '-I', str(Path(__file__).resolve()), 'install', job],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == BUSY:
            return BUSY, '', []
        record = softUpgrade.read_status(job)
        incomplete = record.get('incomplete') if result.returncode == 0 else None
        return (result.returncode, record.get('message', '') if result.returncode else '',
                [str(step) for step in incomplete] if isinstance(incomplete, list) else [])

    def install_job(self, job):
        """The upgrade to the one commit recorded for this job. Runs inside the scope."""
        from plogical import softUpgrade
        attempt = self.state().get('attempt') or {}
        if not re.fullmatch(r'[0-9a-f]{32}', job) or attempt.get('job') != job or 'result' in attempt:
            return 1
        try:
            softUpgrade.run_unattended(attempt['branch'], attempt['commit'], job)
        except softUpgrade.Busy:
            return BUSY
        except Exception:
            return 1
        return 0

    # ---- telling the administrator --------------------------------------------------

    def identity(self):
        try:
            return Path('/etc/machine-id').read_text().strip() or socket.gethostname()
        except OSError:
            return socket.gethostname()

    def report(self, settings, subject, text):
        if settings['email']:
            try:
                self.mail(settings['email'], 'CyberPanel automatic update on %s: %s' % (socket.gethostname(), subject), text)
            except Exception:
                pass

    def send_mail(self, recipient, subject, text):
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        sender = 'root@%s' % socket.gethostname()
        message = 'From: %s\nTo: %s\nSubject: %s\n\n%s\n\nServer: %s\nAutomatic updates are set on the Version Management page of the panel.\n' % (
            sender, recipient, subject, text, socket.gethostname())
        CyberCPLogFileWriter.SendEmail(sender, [recipient], message)

    # ---- settings, timer, status --------------------------------------------------------

    def system_command(self, *arguments):
        return subprocess.run(list(arguments), timeout=60, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)

    def schedule(self):
        """Write the units and make the timer match the stored mode."""
        for name, content in ((SERVICE, SERVICE_UNIT), (TIMER, TIMER_UNIT)):
            path = self.units / name
            try:
                unchanged = path.read_text() == content
            except OSError:
                unchanged = False
            if not unchanged:
                write_private(path, content)
                os.chmod(str(path), 0o644)
        self.command(SYSTEMCTL, 'daemon-reload')
        if self.settings()['mode'] == 'off':
            self.command(SYSTEMCTL, 'disable', '--now', TIMER)
        else:
            self.command(SYSTEMCTL, 'enable', '--now', TIMER)

    def configure(self, values):
        values = checked_settings(values)
        self.settings_path.parent.mkdir(mode=0o755, exist_ok=True)
        write_private(self.settings_path, json.dumps(values, sort_keys=True) + '\n')
        self.schedule()
        return values

    def status(self):
        state = self.state()
        settings = self.settings()
        try:
            current = self.installed()
        except Exception:
            current = None
        timer = self.command(SYSTEMCTL, 'is-active', TIMER).stdout.strip()
        checked = state.get('checked')
        return {'settings': settings, 'installed': current, 'release': state.get('release'),
                'checked': checked, 'error': state.get('error', ''),
                # In the server's own time, like the update hour.
                'checked_text': time.strftime('%d %b %Y %H:%M %Z', time.localtime(checked)) if checked else '',
                'summary': state.get('summary', ''), 'attempt': state.get('attempt'),
                'timer': timer, 'server_time': time.strftime('%H:%M'), 'timezone': time.strftime('%Z')}


def main(arguments):
    if os.geteuid() != 0:
        print('Run as root.', file=sys.stderr)
        return 1
    updater = Updater()
    if arguments == ['run']:
        return updater.run()
    if arguments == ['check']:
        updater.run(check_only=True)
        print(json.dumps(updater.status()))
        return 0
    if arguments == ['status']:
        print(json.dumps(updater.status()))
        return 0
    if arguments == ['schedule']:
        updater.schedule()
        return 0
    if len(arguments) == 2 and arguments[0] == 'configure' and re.fullmatch(r'(?:[0-9a-f]{2}){2,600}', arguments[1]):
        try:
            values = updater.configure(json.loads(bytes.fromhex(arguments[1]).decode('utf-8')))
        except ValueError as error:
            print(json.dumps({'error': str(error)}))
            return 1
        if values['mode'] != 'off':
            # Show the administrator what will happen without waiting for the timer.
            try:
                updater.run(check_only=True)
            except Exception:
                pass
        print(json.dumps(updater.status()))
        return 0
    if len(arguments) == 2 and arguments[0] == 'install':
        return updater.install_job(arguments[1])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
