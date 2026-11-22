"""Keep one website's virtual host from stopping Apache for every website.

Apache reads every virtual host when it starts. One that it refuses keeps it
from starting at all, and every website on the Apache backend then answers
503 through OpenLiteSpeed. The usual refusal is a SuexecUserGroup line that
names a system account which does not exist ("bad user name"). PHP-FPM
treats a pool whose user does not exist the same way, for every website of
that PHP version.

Nothing here loads Django or the panel: the functions are given the commands
and the account lookups they use, so the workers, the upgrade and the tests
run the same code.
"""
import glob
import grp
import os
from pathlib import Path
import pwd
import re
import subprocess

from plogical.websiteSuspension import atomic_write

# PHP-FPM reads *.conf only. A pool file that carries this ending is kept
# beside the others and not read.
DISABLED_SUFFIX = '.disabled-by-cyberpanel'
# What is put before a SuexecUserGroup line that Apache cannot load.
DISABLED_LINE = '# Disabled by CyberPanel, this system account does not exist: '

SUEXEC_LINE = re.compile(r'^[ \t]*SuexecUserGroup[ \t]+(\S+)[ \t]+(\S+)', re.IGNORECASE | re.MULTILINE)
POOL_ACCOUNT_LINE = re.compile(r'^[ \t]*(user|group)[ \t]*=[ \t]*(\S+)', re.MULTILINE)

DEB_VHOSTS = '/etc/apache2/sites-enabled/'
RPM_VHOSTS = '/etc/httpd/conf.d/'
DEB_POOLS = ('/etc/php/*/fpm/pool.d/',)
RPM_POOLS = ('/etc/opt/remi/php*/php-fpm.d/', '/opt/remi/php*/root/etc/php-fpm.d/')


def account_problem(user, group=None, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Why the system account a website runs as cannot be used, or None when it can.

    The virtual host and the pool name the user and a group of the same
    name. Apache and PHP-FPM look both up when they start.
    """
    for kind, name, lookup in (('user', user, getpwnam), ('group', user if group is None else group, getgrnam)):
        if not isinstance(name, str) or not name:
            return 'The website has no system %s.' % kind
        try:
            lookup(name)
        except KeyError:
            return 'The system %s %s does not exist on this server.' % (kind, name)
    return None


def vhost_accounts(text):
    """The (user, group) of every SuexecUserGroup line of a virtual host file."""
    return [(found.group(1).strip('"\''), found.group(2).strip('"\'')) for found in SUEXEC_LINE.finditer(text)]


def pool_accounts(text):
    """The (user, group) a PHP-FPM pool file runs its workers as; None for a line it does not have."""
    named = {}
    for found in POOL_ACCOUNT_LINE.finditer(text):
        named.setdefault(found.group(1), found.group(2).strip('"\''))
    if not named:
        return []
    return [(named.get('user'), named.get('group'))]


def unknown_accounts(pairs, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """The names among (user, group) pairs that no system account has.

    A number is an id, which Apache (as #id) and PHP-FPM accept without a
    lookup, and is never reported.
    """
    unknown = []
    for index, lookup in ((0, getpwnam), (1, getgrnam)):
        for pair in pairs:
            name = pair[index]
            if not name or name.lstrip('#').isdigit() or name in unknown:
                continue
            try:
                lookup(name)
            except KeyError:
                unknown.append(name)
    return unknown


def config_test_command(rpm_family):
    """The command with which Apache checks its whole configuration without starting."""
    return ['/usr/sbin/httpd', '-t'] if rpm_family else ['/usr/sbin/apache2ctl', '-t']


def config_test(command, run=subprocess.run, timeout=120):
    """Run Apache's configuration test. Returns (passed, what Apache said)."""
    try:
        result = run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     universal_newlines=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return False, '%s could not be run: %s' % (command[0], error)
    return result.returncode == 0, (result.stdout or '').strip()


def said(output, limit=600):
    """The end of a command's output as one line, for a status message."""
    text = ' '.join(str(output or '').split())
    return text[-limit:] if text else 'no message'


class SavedFiles:
    """What some files held before a change, to put back exactly when the change is refused."""

    def __init__(self, paths):
        self.saved = []
        for path in paths:
            try:
                with open(path, 'rb') as source:
                    self.saved.append((path, source.read(), os.fstat(source.fileno())))
            except FileNotFoundError:
                self.saved.append((path, None, None))

    def restore(self):
        for path, content, metadata in self.saved:
            if content is not None:
                atomic_write(Path(path), content, metadata)
                continue
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


def refusal(paths, before, after):
    """What to report when Apache's test fails after a change to the files in paths.

    before and after are the results of the test. A failure that was there
    before, and that does not name one of the changed files, is not this
    change's doing and is reported as such.
    """
    if before[0] or any(path in after[1] for path in paths):
        return 'Apache refused this configuration, so it was not put in place: %s' % said(after[1])
    return ('Apache already refused its configuration before this change, so nothing was changed. '
            'Correct this first: %s' % said(after[1]))


def apply_change(paths, change, test, restart):
    """Change Apache's configuration only if Apache accepts the result.

    paths    the files the change creates or rewrites
    change   makes the change; returns None, or a text saying why it could not
    test     returns (passed, output) of Apache's configuration test
    restart  restarts Apache; returns None, or a text saying why it is not running

    Returns (1, 'None'), or (0, reason). After a refusal every file holds
    what it held before and Apache was not restarted with the refused
    configuration, so the websites it was serving are still served.
    """
    before = test()
    saved = SavedFiles(paths)
    try:
        problem = change()
    except Exception as error:
        problem = str(error) or error.__class__.__name__
    if problem is None:
        after = test()
        if after[0]:
            problem = restart()
            if problem is None:
                return 1, 'None'
            saved.restore()
            if before[0]:
                # Apache comes back with what it was running before.
                restart()
            return 0, problem
        problem = refusal(paths, before, after)
    saved.restore()
    return 0, problem


def set_pool_aside(path):
    """Take a pool file out of what PHP-FPM reads and keep its content beside it."""
    os.replace(path, path + DISABLED_SUFFIX)
    return path + DISABLED_SUFFIX


def pools_set_aside(name, rpm_family):
    """The files set_pool_aside() left for the pool called name (the domain plus .conf)."""
    found = []
    for folder in RPM_POOLS if rpm_family else DEB_POOLS:
        found.extend(glob.glob(folder + glob.escape(name + DISABLED_SUFFIX)))
    return found


def comment_out_unknown_accounts(path, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Turn the SuexecUserGroup lines of a virtual host that name a missing account into comments.

    The virtual host stays in place under its own name, so its domain is not
    answered by the virtual host of another website. PHP reaches PHP-FPM
    through the socket named in the file and does not use this line.
    """
    with open(path, 'rb') as source:
        content = source.read()
        metadata = os.fstat(source.fileno())
    lines = content.decode('utf-8', errors='surrogateescape').splitlines(True)
    for index, line in enumerate(lines):
        if unknown_accounts(vhost_accounts(line), getpwnam, getgrnam):
            lines[index] = line[:len(line) - len(line.lstrip())] + DISABLED_LINE + line.lstrip()
    atomic_write(Path(path), ''.join(lines).encode('utf-8', errors='surrogateescape'), metadata)


def files_naming_unknown_accounts(folder, accounts_of, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """The *.conf files of a folder that name a missing account, as (path, names, is the panel's kind).

    The panel writes a website's virtual host and pool as an ordinary file
    named after the domain. A link (Debian's own sites-enabled entries) and
    PHP-FPM's www.conf belong to the administrator or the distribution.
    """
    found = []
    for path in sorted(glob.glob(os.path.join(folder, '*.conf'))):
        try:
            with open(path, errors='replace') as source:
                names = unknown_accounts(accounts_of(source.read()), getpwnam, getgrnam)
        except OSError:
            continue
        if names:
            found.append((path, names, not os.path.islink(path) and os.path.basename(path) != 'www.conf'))
    return found


def fpm_unit(pool_folder):
    """The PHP-FPM service that reads a pool folder, or None for a folder of another layout."""
    found = re.search(r'/etc/php/(\d+)\.(\d+)/fpm/pool\.d', pool_folder)
    if found:
        return 'php%s.%s-fpm' % found.groups()
    found = re.search(r'/remi/php(\d+)/', pool_folder)
    if found:
        return 'php%s-php-fpm' % found.group(1)
    return None


def _succeeds(*command):
    return subprocess.call(list(command), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def repair(log=lambda message: None, rpm_family=None, vhost_folder=None, pool_folders=None, test=None,
           succeeds=_succeeds, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Upgrade step for a server whose Apache backend is down because of a missing system account.

    A line that names an account which does not exist can never be loaded,
    and while it is there nothing else is either. In the files the panel
    wrote, such a pool is set aside (its content is kept beside it), such a
    SuexecUserGroup line becomes a comment, and the service is started
    again. Everything else is reported and left alone: no account is
    created, no file of the administrator or the distribution is touched,
    and a configuration that fails for another reason is not changed.
    Returns what was done.
    """
    if rpm_family is None:
        if os.path.exists('/usr/sbin/httpd'):
            rpm_family = True
        elif os.path.exists('/usr/sbin/apache2'):
            rpm_family = False
        else:
            return 'not installed'
    service = 'httpd' if rpm_family else 'apache2'
    if vhost_folder is None:
        vhost_folder = RPM_VHOSTS if rpm_family else DEB_VHOSTS
    if pool_folders is None:
        pool_folders = [folder for pattern in (RPM_POOLS if rpm_family else DEB_POOLS)
                        for folder in sorted(glob.glob(pattern))]
    if test is None:
        def test():
            return config_test(config_test_command(rpm_family))

    done = []

    for folder in pool_folders:
        changed = False
        for path, names, panel_file in files_naming_unknown_accounts(folder, pool_accounts, getpwnam, getgrnam):
            if not panel_file:
                log('WARNING: The PHP-FPM pool %s names the missing system account %s; PHP-FPM cannot '
                    'start with it. It was left as it is.' % (path, ', '.join(names)))
                continue
            log('The PHP-FPM pool %s names the missing system account %s, which keeps PHP-FPM from '
                'starting for every website of that PHP version. It was moved to %s.'
                % (path, ', '.join(names), set_pool_aside(path)))
            done.append(path)
            changed = True
        unit = fpm_unit(folder)
        if changed and unit is not None and not succeeds('systemctl', 'reload-or-restart', '--', unit):
            log('WARNING: %s did not start; see "systemctl status %s".' % (unit, unit))

    passed, output = test()
    if passed:
        return 'repaired' if done else 'not needed'

    corrected = False
    for path, names, panel_file in files_naming_unknown_accounts(vhost_folder, vhost_accounts, getpwnam, getgrnam):
        if not panel_file:
            log('WARNING: The Apache virtual host %s names the missing system account %s; Apache cannot '
                'start with it. It was left as it is.' % (path, ', '.join(names)))
            continue
        comment_out_unknown_accounts(path, getpwnam, getgrnam)
        log('The Apache virtual host %s names the missing system account %s, which keeps Apache from '
            'starting for every website. Its SuexecUserGroup line was turned into a comment. That '
            'website stays unavailable until its system account exists.' % (path, ', '.join(names)))
        done.append(path)
        corrected = True

    if corrected:
        passed, output = test()
    if not passed:
        log('WARNING: Apache refuses its configuration, so websites on the Apache backend cannot be '
            'served until it is corrected. The upgrade did not change what Apache reports: %s' % said(output))
        return 'failed'
    if not succeeds('systemctl', 'restart', service):
        log('WARNING: Apache accepts its configuration but did not start; see "systemctl status %s".' % service)
        return 'failed'
    log('Apache accepts its configuration again and was restarted.')
    return 'repaired'
