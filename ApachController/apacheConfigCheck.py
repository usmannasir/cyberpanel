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
import locale
import os
from pathlib import Path
import pwd
import re
import signal
import subprocess

from plogical.websiteSuspension import atomic_write

# PHP-FPM reads *.conf only. A pool file that carries this ending is kept
# beside the others and not read.
DISABLED_SUFFIX = '.disabled-by-cyberpanel'
# What is put before a SuexecUserGroup line that Apache cannot load.
DISABLED_LINE = '# Disabled by CyberPanel, this system account does not exist: '
# What closes a virtual host whose account is missing; see close_virtual_host.
CLOSED_BEGIN = '# BEGIN CyberPanel: website closed, its system account does not exist'
CLOSED_END = '# END CyberPanel: website closed, its system account does not exist'
CLOSED_BLOCK = (CLOSED_BEGIN,
                '<IfModule mod_rewrite.c>', '    RewriteEngine On', '    RewriteRule ^ - [F]', '</IfModule>',
                '<Location "/">', '    Require all denied', '</Location>',
                CLOSED_END)
# What is put before a line that lets the website's own files configure Apache.
CLOSED_LINE = '# Disabled by CyberPanel while the website is closed: '
OVERRIDE_LINE = re.compile(r'[ \t]*(AllowOverride(?:List)?)[ \t]', re.IGNORECASE)
VHOST_OPEN = re.compile(r'[ \t]*<VirtualHost[ \t>]', re.IGNORECASE)
VHOST_CLOSE = re.compile(r'[ \t]*</VirtualHost[ \t]*>', re.IGNORECASE)
# How long output is still read after a command was ended at its time limit.
AFTER_END = 10

SUEXEC_LINE = re.compile(r'^[ \t]*SuexecUserGroup[ \t]+(\S+)[ \t]+(\S+)', re.IGNORECASE | re.MULTILINE)
POOL_ACCOUNT_LINE = re.compile(r'^[ \t]*(user|group)[ \t]*=[ \t]*(\S+)', re.MULTILINE)
# A name as it stands in the account files. Anything else in a configuration
# (an id, #id, $pool, ${VARIABLE}) is resolved by the service itself.
LITERAL_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]*')

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
    """The literal names among (user, group) pairs that no system account has."""
    unknown = []
    for index, lookup in ((0, getpwnam), (1, getgrnam)):
        for pair in pairs:
            name = pair[index]
            if not name or LITERAL_NAME.fullmatch(name) is None or name in unknown:
                continue
            try:
                lookup(name)
            except KeyError:
                unknown.append(name)
    return unknown


def installed_family(exists=os.path.exists):
    """True on the RPM family, False on the Debian family, None where Apache is not installed.

    Installed means the server and the program that controls it. Removing
    the Debian apache2 package leaves the apache2 binary of apache2-bin
    behind without apache2ctl.
    """
    if exists('/usr/sbin/httpd'):
        return True
    if exists('/usr/sbin/apache2') and exists('/usr/sbin/apache2ctl'):
        return False
    return None


def config_test_command(rpm_family):
    """The command with which Apache checks its whole configuration without starting."""
    return ['/usr/sbin/httpd', '-t'] if rpm_family else ['/usr/sbin/apache2ctl', '-t']


def bounded_run(command, timeout):
    """Run a command and return (exit status, what it wrote), within a time limit.

    The command gets a process group of its own, and the whole group is
    ended at the limit: apache2ctl is a shell that starts apache2, and a
    wait on their shared output would otherwise outlast the limit. The
    output is text whatever bytes it holds.
    """
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        output = process.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            process.communicate(timeout=AFTER_END)
        except subprocess.TimeoutExpired:
            # Something that left the group still holds the output. It is
            # not waited for.
            process.kill()
            process.stdout.close()
            try:
                process.wait(timeout=AFTER_END)
            except subprocess.TimeoutExpired:
                pass
        raise
    # Whatever the locale and whatever bytes the command wrote.
    return process.returncode, (output or b'').decode('utf-8', errors='replace')


def config_test(command, run=bounded_run, timeout=120):
    """Run Apache's configuration test. Returns (passed, what Apache said)."""
    try:
        status, output = run(command, timeout)
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        return False, '%s could not be run: %s' % (command[0], error)
    return status == 0, output.strip()


def said(output, limit=600):
    """The end of a command's output as one line, for a status message."""
    text = ' '.join(str(output or '').split())
    return text[-limit:] if text else 'no message'


def replace_file(path, text):
    """Give an existing file new content in one step, with the owner and mode it has."""
    atomic_write(Path(path), text.encode('utf-8', errors='surrogateescape'), os.stat(path))


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


def unrelated_failure(paths, before, after):
    """True when Apache's test failed before the change already and does not name a changed file now."""
    return not before[0] and not any(path in after[1] for path in paths)


def refusal(paths, before, after):
    """What to report when Apache's test fails after a change to the files in paths.

    before and after are the results of the test. A failure that was there
    before, and that does not name one of the changed files, is not this
    change's doing and is reported as such.
    """
    if unrelated_failure(paths, before, after):
        return ('Apache already refused its configuration before this change, so nothing was changed. '
                'Correct this first: %s' % said(after[1]))
    return 'Apache refused this configuration, so it was not put in place: %s' % said(after[1])


def apply_change(paths, change, test, restart, keep_beside_other_failure=False):
    """Change Apache's configuration only if Apache accepts the result.

    paths    the files the change creates or rewrites
    change   makes the change; returns None, or a text saying why it could not
    test     returns (passed, output) of Apache's configuration test
    restart  restarts Apache; returns None, or a text saying why it is not running

    Returns (1, 'None'), or (0, reason). After a refusal every file holds
    what it held before and Apache was not restarted with the refused
    configuration, so the websites it was serving are still served.

    With keep_beside_other_failure, for an administrator's own edit, a
    change is kept when Apache refused its configuration before it already
    and does not name the changed files now: several faulty files could
    otherwise never be corrected one after the other. Apache cannot start
    in that state and is not restarted; the result is (2, why).
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
        if keep_beside_other_failure and unrelated_failure(paths, before, after):
            return 2, ('Apache was not restarted: it refused its configuration before this change already, '
                       'for a reason outside this file: %s' % said(after[1]))
        problem = refusal(paths, before, after)
    saved.restore()
    return 0, problem


class UnreadableBackends(ValueError):
    """An extprocessor block of a backend's name is not laid out as OpenLiteSpeed writes it."""


def _backend_blocks(lines, name):
    """The (first line, line after the last, address) of every "extprocessor name {" block.

    A block runs from its opening line to the line that holds nothing but
    the closing brace; a brace in a comment or in a value does not end it.
    """
    opening = re.compile(br'[ \t]*extprocessor[ \t]+' + re.escape(name) + br'(?![^ \t{\r\n])(.*)', re.DOTALL)
    blocks, number = [], 0
    while number < len(lines):
        found = opening.match(lines[number])
        number += 1
        if not found:
            continue
        if found.group(1).strip() != b'{':
            raise UnreadableBackends(name.decode('ascii', 'replace'))
        first, depth, address = number - 1, 1, b''
        while depth and number < len(lines):
            text = lines[number].strip()
            number += 1
            if text == b'}':
                depth -= 1
            elif text.endswith(b'{') and not text.startswith(b'#'):
                depth += 1
            elif depth == 1 and text.split()[:1] == [b'address'] and not address:
                address = b' '.join(text.split()[1:])
        if depth:
            raise UnreadableBackends(name.decode('ascii', 'replace'))
        blocks.append((first, number, address))
    return blocks


def with_proxy_backends(data, *definitions):
    """OpenLiteSpeed's main configuration with each given proxy backend defined exactly once.

    data is the content of the file as bytes; every byte that is not part
    of a removed or added block stays as it is, line endings included. A
    definition is an "extprocessor NAME { ... }" block as the panel writes
    it. The first block of that name whose address is the definition's
    stays where it is, with whatever else an administrator set in it; every
    other block of the name is removed, and the definition is added when no
    block had the address.

    Returns (content, removed), where removed lists the (name, address) of
    removed blocks that had another address. A configuration that is
    already right comes back unchanged. UnreadableBackends is raised, and
    nothing is to be written, when a block of one of the names cannot be
    told from its surroundings.
    """
    def plain(address):
        return address[len(b'http://'):] if address.startswith(b'http://') else address

    newline = b'\r\n' if b'\r\n' in data else b'\n'
    removed = []
    for definition in definitions:
        wanted = definition.encode('ascii').splitlines(True)
        name = wanted[0].split()[1]
        right = _backend_blocks(wanted, name)[0][2]
        lines = data.splitlines(True)
        kept, drop = False, set()
        for first, after, address in _backend_blocks(lines, name):
            if not kept and plain(address) == plain(right):
                kept = True
                continue
            drop.update(range(first, after))
            if plain(address) != plain(right):
                removed.append((name.decode('ascii'), address.decode('utf-8', errors='replace')))
        data = b''.join(line for number, line in enumerate(lines) if number not in drop)
        if not kept:
            if data and not data.endswith((b'\n', b'\r')):
                data += newline
            data += newline.join(definition.encode('ascii').splitlines()) + newline
    return data, removed


def correct_proxy_backends(path, definitions, log=lambda message: None):
    """Give OpenLiteSpeed's main configuration one right definition of each Apache backend.

    For the worker that puts a website on the Apache backend. The file is
    read and written as bytes and replaced in one step with the owner and
    mode it has. A file whose blocks cannot be told apart is left as it is.
    Returns True when the file was changed.
    """
    with open(path, 'rb') as source:
        data = source.read()
        metadata = os.fstat(source.fileno())
    try:
        updated, removed = with_proxy_backends(data, *definitions)
        # What was made must itself read as right, or nothing is written.
        if with_proxy_backends(updated, *definitions) != (updated, []):
            raise UnreadableBackends('result')
    except UnreadableBackends as error:
        log('The Apache backends in %s were left as they are: the extprocessor block %s is not laid out '
            'as expected.' % (path, error))
        return False
    for name, address in removed:
        log('Removed the extprocessor %s block with the address %s from %s: Apache listens for that '
            'backend on another port.' % (name, address or 'none', path))
    if updated == data:
        return False
    atomic_write(Path(path), updated, metadata)
    return True


def correct_proxy_backends_on_upgrade(path, definitions, apply, running, log=lambda message: None):
    """The same correction as an upgrade step, through the upgrade's checked change of OpenLiteSpeed.

    apply({path: (before, after)}) validates the configuration with the
    change, activates it and puts the file back when OpenLiteSpeed refuses
    it; it takes and compares the file as text. It is used only when that
    text is the file byte for byte (no carriage returns, nothing the
    locale cannot decode); another file is left for the worker above, which
    keeps every byte, and the log says so. running() tells whether
    OpenLiteSpeed runs.

    A change that was refused and fully undone is logged and the upgrade
    goes on. A failure that left the file changed or OpenLiteSpeed stopped
    is raised to the caller as it came.
    """
    with open(path, 'rb') as source:
        data = source.read()
    if b'extprocessor apachebackend' not in data and b'extprocessor proxyApacheBackendSSL' not in data:
        return 'not needed'
    try:
        updated, removed = with_proxy_backends(data, *definitions)
    except UnreadableBackends as error:
        log('The Apache backends in %s were left as they are: the extprocessor block %s is not laid out '
            'as expected.' % (path, error))
        return 'left'
    if updated == data:
        return 'not needed'
    # The text apply() will read from the file, and what it would write back.
    encoding = locale.getpreferredencoding(False)
    try:
        with open(path, 'r') as source:
            before = source.read()
        exact = before.encode(encoding) == data
        after = updated.decode(encoding) if exact else None
    except UnicodeError:
        exact = False
    if not exact:
        log('The Apache backends in %s were not corrected by the upgrade: the file has line endings or '
            'characters its checked change would not keep. They are corrected when the next website is '
            'put on the Apache backend.' % path)
        return 'left'
    was_running = running()
    try:
        apply({path: (before, after)})
    except Exception as error:
        with open(path, 'rb') as source:
            undone = source.read() == data
        if not undone or running() != was_running:
            raise
        log('WARNING: The Apache backends of OpenLiteSpeed were not corrected; the configuration is as it '
            'was: %s' % error)
        return 'refused'
    for name, address in removed:
        log('Removed the extprocessor %s block with the address %s from %s: Apache listens for that '
            'backend on another port.' % (name, address or 'none', path))
    log('The Apache backends of OpenLiteSpeed are now defined once each, on the ports Apache listens on.')
    return 'corrected'


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


def _lines(path):
    with open(path, 'rb') as source:
        return source.read().decode('utf-8', errors='surrogateescape').splitlines(True)


def close_virtual_host(path, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Close a virtual host whose SuexecUserGroup line names a missing account.

    The line becomes a comment, so that Apache can start. Without it Apache
    would serve the website, and run what its files ask for, as Apache's own
    user, which can read the files of the other websites. Every VirtualHost
    block that had such a line is therefore closed, in a way the website's
    own files cannot undo:

    - A RewriteRule in the virtual host itself, placed first in the block,
      forbids every request. Rules of the virtual host run when the URL is
      mapped to a file, before Apache walks the directories and reads any
      .htaccess, so a refused request never reaches the website's files.
    - Every AllowOverride and AllowOverrideList line of the block is set to
      None. .htaccess files are then not read at all, also where the rewrite
      module is not loaded, and with them go the <If> sections and handlers
      a file could bring: Apache merges <If> after <Location>, so a denial
      in <Location> alone could be lifted from an .htaccess.
    - With no .htaccess read, the <Location> denial is the last word of the
      remaining configuration.

    The virtual host stays under its own name, so its domain is not answered
    by the virtual host of another website either. reopen_virtual_host()
    undoes all of it exactly.
    """
    lines = _lines(path)

    def unknown(line):
        return unknown_accounts(vhost_accounts(line), getpwnam, getgrnam)

    # The block each line belongs to: the number of its <VirtualHost> line,
    # or None outside every block.
    block, blocks, closed = None, [], set()
    for number, line in enumerate(lines):
        if VHOST_OPEN.match(line):
            block = number
        blocks.append(block)
        if unknown(line):
            closed.add(block)
        if VHOST_CLOSE.match(line):
            block = None

    result = []
    for number, line in enumerate(lines):
        indent = line[:len(line) - len(line.lstrip())]
        ending = '\r\n' if line.endswith('\r\n') else '\n'
        text = line.lstrip().rstrip('\r\n')
        if blocks[number] not in closed:
            result.append(line)
        elif unknown(line):
            result.append(indent + DISABLED_LINE + text + ending)
            if blocks[number] is None:
                result.extend(indent + part + ending for part in CLOSED_BLOCK)
        elif OVERRIDE_LINE.match(line):
            directive = OVERRIDE_LINE.match(line).group(1)
            result.append(indent + CLOSED_LINE + text + ending)
            result.extend(indent + part + ending for part in (CLOSED_BEGIN, directive + ' None', CLOSED_END))
        else:
            result.append(line)
            if number == blocks[number]:
                result.extend(indent + '    ' + part + ending for part in CLOSED_BLOCK)
    replace_file(path, ''.join(result))


def reopen_virtual_host(path, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Undo close_virtual_host() once every account the virtual host names exists.

    Returns True when the virtual host was closed and is open again, False
    when it was not closed or an account is still missing.
    """
    try:
        lines = _lines(path)
    except FileNotFoundError:
        return False
    restored, closed, inside = [], False, False
    for line in lines:
        text = line.strip()
        if text == CLOSED_BEGIN:
            closed = inside = True
        elif text == CLOSED_END:
            inside = False
        elif inside:
            continue
        elif text.startswith(DISABLED_LINE) or text.startswith(CLOSED_LINE):
            closed = True
            restored.append(line.replace(DISABLED_LINE if text.startswith(DISABLED_LINE) else CLOSED_LINE, '', 1))
        else:
            restored.append(line)
    if not closed or inside or unknown_accounts(vhost_accounts(''.join(restored)), getpwnam, getgrnam):
        return False
    replace_file(path, ''.join(restored))
    return True


def files_naming_unknown_accounts(folder, accounts_of, panel_names, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """The *.conf files of a folder that name a missing account, as (path, names, is the panel's).

    The panel writes the virtual host and the pool of a website or child
    domain as an ordinary file called after the domain; panel_names holds
    those file names. Every other file belongs to the administrator or the
    distribution, whatever it contains.
    """
    found = []
    for path in sorted(glob.glob(os.path.join(folder, '*.conf'))):
        try:
            with open(path, errors='replace') as source:
                names = unknown_accounts(accounts_of(source.read()), getpwnam, getgrnam)
        except OSError:
            continue
        if names:
            found.append((path, names, os.path.basename(path) in panel_names and not os.path.islink(path)
                          and os.path.isfile(path)))
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
    try:
        return bounded_run(list(command), 120)[0] == 0
    except (OSError, subprocess.SubprocessError):
        return False


def ols_running():
    """True when the OpenLiteSpeed service is active."""
    return _succeeds('systemctl', 'is-active', '--quiet', 'lsws')


def repair(domains, log=lambda message: None, rpm_family=None, vhost_folder=None, pool_folders=None, test=None,
           succeeds=_succeeds, getpwnam=pwd.getpwnam, getgrnam=grp.getgrnam):
    """Upgrade step for a server whose Apache backend is down because of a missing system account.

    domains are the websites and child domains the panel knows. A line that
    names an account which does not exist can never be loaded, and while it
    is there nothing else is either. Only the files the panel wrote for
    those domains are changed: such a pool is set aside (its content is kept
    beside it) and such a virtual host is closed (see close_virtual_host).
    A service is then started again if it is enabled; one that an
    administrator disabled stays as it is. Everything else is reported and
    left alone: no account is created, no other file is touched, and a
    configuration that fails for another reason is not changed. Returns
    what was done.
    """
    if rpm_family is None:
        rpm_family = installed_family()
        if rpm_family is None:
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
    panel_names = set(domain + '.conf' for domain in domains)

    def start(unit, action, what):
        """True when the unit runs again, False when it did not start, None when it is left stopped."""
        if not succeeds('systemctl', 'is-enabled', '--quiet', '--', unit):
            log('%s is not enabled on this server, so it was not started.' % what)
            return None
        if succeeds('systemctl', action, '--', unit):
            return True
        log('WARNING: %s did not start; see "systemctl status %s".' % (what, unit))
        return False

    done = []

    for folder in pool_folders:
        changed = False
        for path, names, panel_file in files_naming_unknown_accounts(folder, pool_accounts, panel_names,
                                                                     getpwnam, getgrnam):
            if not panel_file:
                log('WARNING: The PHP-FPM pool %s names the missing system account %s; PHP-FPM cannot '
                    'start with it. It is not a file of the panel and was left as it is.'
                    % (path, ', '.join(names)))
                continue
            log('The PHP-FPM pool %s names the missing system account %s, which keeps PHP-FPM from '
                'starting for every website of that PHP version. It was moved to %s.'
                % (path, ', '.join(names), set_pool_aside(path)))
            done.append(path)
            changed = True
        unit = fpm_unit(folder)
        if changed and unit is not None:
            start(unit, 'reload-or-restart', unit)

    passed, output = test()
    if passed:
        return 'repaired' if done else 'not needed'

    closed = False
    for path, names, panel_file in files_naming_unknown_accounts(vhost_folder, vhost_accounts, panel_names,
                                                                 getpwnam, getgrnam):
        if not panel_file:
            log('WARNING: The Apache virtual host %s names the missing system account %s; Apache cannot '
                'start with it. It is not a file of the panel and was left as it is.' % (path, ', '.join(names)))
            continue
        close_virtual_host(path, getpwnam, getgrnam)
        log('The Apache virtual host %s names the missing system account %s, which keeps Apache from '
            'starting for every website. The website was closed: the SuexecUserGroup line is now a '
            'comment and Apache refuses every request to it. To open it again, create the account, '
            'then change the PHP version of the website in the panel (choosing the version it has '
            'will do): that writes its pool again and reopens the virtual host.' % (path, ', '.join(names)))
        done.append(path)
        closed = True

    if closed:
        passed, output = test()
    if not passed:
        log('WARNING: Apache refuses its configuration, so websites on the Apache backend cannot be '
            'served until it is corrected. The upgrade did not change what Apache reports: %s' % said(output))
        return 'failed'
    started = start(service, 'restart', 'Apache')
    if started is False:
        return 'failed'
    if started:
        log('Apache accepts its configuration again and was restarted.')
    return 'repaired'
