"""Independent website/domain suspension with rollback on failed activation."""
import collections
import contextlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata

START = '# Website Suspension Configuration'
END = '# End Website Suspension Configuration'
DISABLED_START = '# CyberPanel original rewrite during suspension'
DISABLED_END = '# End CyberPanel original rewrite during suspension'
SUSPENSION = r'''# Website Suspension Configuration
rewrite {
    enable 1
    autoLoadHtaccess 0
    rules <<<END_rules
RewriteEngine On
RewriteCond %{REQUEST_URI} !^/cyberpanel_suspension_page\.html$
RewriteRule ^ /cyberpanel_suspension_page.html [L]
END_rules
}
context /cyberpanel_suspension_page.html {
  location /usr/local/CyberCP/websiteFunctions/suspension.html
  accessible 1
  allowBrowse 1
}
# End Website Suspension Configuration
'''


def validate_domain(domain):
    # Never allow a caller-controlled path or shell fragment to reach a vhost.
    if (not isinstance(domain, str) or len(domain) > 253 or
            not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', domain) or
            any(not label or len(label) > 63 or label.startswith('-') or
                label.endswith('-') for label in domain.split('.'))):
        raise ValueError('Invalid domain name.')
    return domain


def validate_stored_domain(domain):
    """Check the stored name of an existing website before it names a path.

    validate_domain is the rule for a new name. Earlier releases stored names
    it refuses today (an underscore, letters outside ASCII), and such a
    website stays manageable. The name of a row that exists is therefore
    refused only when it cannot be one component of a path: empty, '.' or
    '..', a leading hyphen, a slash, white space or a control character.
    """
    if (not isinstance(domain, str) or domain in ('', '.', '..') or
            domain.startswith('-') or '/' in domain or
            any(letter.isspace() or unicodedata.category(letter) == 'Cc' for letter in domain)):
        raise ValueError('Invalid domain name.')
    return domain


def normalize_action(action):
    # The existing public API/CLI also uses Unsuspend and UnSuspend.
    if isinstance(action, str):
        normalized = {'suspend': 'Suspend', 'unsuspend': 'Un-Suspend',
                      'un-suspend': 'Un-Suspend'}.get(action.lower())
        if normalized:
            return normalized
    raise ValueError('Invalid suspension action.')


@contextlib.contextmanager
def suspension_lock(server_root='/usr/local/lsws'):
    """Share ordering with child provisioning, which may activate a vhost."""
    import fcntl
    with (Path(server_root) / 'conf' / '.cyberpanel-suspension.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


class _ConfigBlocks:
    """Count configuration braces without interpreting heredoc rule content."""
    def __init__(self):
        self.heredoc = None

    def delta(self, line):
        if self.heredoc:
            if line.strip() == self.heredoc:
                self.heredoc = None
            return 0
        code = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\#.*''', '', line)
        heredoc = re.search(r'<<<\s*([A-Za-z0-9_]+)', code)
        if heredoc:
            self.heredoc = heredoc.group(1)
            code = code[:heredoc.start()]
        braces = re.findall(r'(?<!\\)[{}]', code)
        return braces.count('{') - braces.count('}')


def _restore(content):
    content = re.sub(r'^' + re.escape(START) + r'\n.*?^' + re.escape(END) +
                     r'\r?\n?', '', content, flags=re.M | re.S)
    pattern = (r'^' + re.escape(DISABLED_START) + r'\n(.*?)^' +
               re.escape(DISABLED_END) + r'\n')
    content = re.sub(pattern, lambda m: ''.join(line[1:] for line in
                     m.group(1).splitlines(keepends=True)), content, flags=re.M | re.S)
    # Earlier releases did not write an end marker around the commented
    # rewrite. Stop at its closing brace rather than uncommenting unrelated
    # comments following it.
    lines = content.splitlines(keepends=True)
    output = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != '# Commented out during suspension':
            output.append(lines[index])
            index += 1
            continue
        index += 1
        balance = 0
        started = False
        parser = _ConfigBlocks()
        while index < len(lines) and lines[index].startswith('#'):
            line = lines[index][1:]
            output.append(line)
            delta = parser.delta(line)
            started = started or delta > 0
            balance += delta
            index += 1
            if started and balance == 0:
                break
    return ''.join(output)


def render_suspension(content, suspended):
    """Preserve existing rules, including multiline/nested rewrite contents."""
    original = _restore(content)
    if not suspended:
        return original
    lines = original.splitlines(keepends=True)
    output = []
    depth = 0
    parser = _ConfigBlocks()
    index = 0
    while index < len(lines):
        line = lines[index]
        if depth == 0 and re.match(r'^\s*rewrite\s*\{', line, re.I):
            block = []
            balance = 0
            block_parser = _ConfigBlocks()
            while index < len(lines):
                entry = lines[index]
                block.append(entry)
                balance += block_parser.delta(entry)
                index += 1
                if balance == 0:
                    break
            if balance:
                raise ValueError('Unclosed root context/rewrite block; suspension was not applied.')
            if not block[-1].endswith('\n'):
                # Without a trailing newline the end marker cannot be parsed.
                raise ValueError('Root rewrite block must end with a newline.')
            output.append(DISABLED_START + '\n')
            output.extend('#' + entry for entry in block)
            output.append(DISABLED_END + '\n')
            continue
        output.append(line)
        depth += parser.delta(line)
        index += 1
    # Earlier versions created suspension.html only when missing. Preserve an
    # operator's customized page; ship the fallback under a different filename
    # so a source upgrade does not overwrite that customization.
    legacy_page = Path('/usr/local/CyberCP/websiteFunctions/suspension.html')
    suspension = SUSPENSION if legacy_page.is_file() else SUSPENSION.replace(
        'location /usr/local/CyberCP/websiteFunctions/suspension.html',
        'location /usr/local/CyberCP/websiteFunctions/suspension-default.html')
    return suspension + ''.join(output)


def atomic_write(path, content, metadata):
    fd, temporary = tempfile.mkstemp(prefix='.cyberpanel-suspend-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(metadata.st_mode))
        if hasattr(os, 'chown'):
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class VhostUpdate:
    """Retain originals until both configuration activation and DB commit pass.

    `check()` returns what the web server's configuration test reports, and
    `check(before)` raises when it reports an error that `before` lacks.
    `check(before, changed)` also names the websites whose files were edited:
    True for one that was suspended, False for one that was restored, and
    None for one that was suspended already and stays so.
    """
    def __init__(self, server_root, check, reload):
        self.root = Path(server_root).resolve()
        self.check = check
        self.reload = reload
        self.originals = []
        self.before = None

    def apply(self, changes):
        staged = []
        changed = {}
        for domain, suspended in changes:
            validate_domain(domain)
            path = self.root / 'conf' / 'vhosts' / domain / 'vhost.conf'
            if path.is_symlink() or path.parent.is_symlink() or self.root not in path.resolve().parents:
                raise ValueError('Unsafe virtual-host configuration path.')
            metadata = path.stat()
            original = path.read_bytes()
            text = original.decode('utf-8')
            updated = render_suspension(text, suspended).encode('utf-8')
            if updated != original:
                staged.append((path, original, updated, metadata))
                # A file that an earlier release suspended in its own form is
                # written again in the present one. The website was suspended
                # and stays so: that is neither a suspension nor a restore.
                held = suspended and render_suspension(text, False) != text
                changed[domain] = None if held else bool(suspended)
        if staged and self.before is None:
            # What the test reports now is what the server already runs with.
            self.before = self.check()
        for path, original, updated, metadata in staged:
            self.originals.append((path, original, metadata))
            atomic_write(path, updated, metadata)
        if staged:
            self.check(self.before, changed)
            self.reload()

    def rollback(self):
        for path, original, metadata in reversed(self.originals):
            atomic_write(path, original, metadata)
        if self.originals:
            # The restored files are judged as the change was, so that what
            # the test reported before the change does not block the recovery.
            self.check(self.before)
            self.reload()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            try:
                self.rollback()
            except Exception as rollback_error:
                raise RuntimeError('Suspension failed and automatic recovery failed: %s; original error: %s' %
                                   (rollback_error, exc_value)) from rollback_error
        return False


def _run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return result.returncode, result.stdout.decode('utf-8', errors='replace')


def _checked(command):
    status, output = _run(command)
    if status:
        raise RuntimeError('Web server configuration activation failed: ' + output[-2000:])


# After a path: `:25` (also behind a closing quote) or `(25)`.
_FILE_LINE = r'''[^\s:,;()\[\]'"]*['"]?)(?::[0-9]+(?![0-9])|\([0-9]+\))'''
_LINE_WORD = re.compile(r'\b(line)[ :#]*[0-9]+', re.I)


def _comparable(line, classifier, changed):
    """An error line without what differs between two runs over the same fault.

    Time and process ID differ in every run. Suspension also moves the lines
    of the files it edits, so a line number is dropped where it belongs to one
    of those files and nowhere else: after a path in that website's directory,
    and after the word "line" in a message about that website.
    """
    line = classifier._STAMP.sub(r'\1 ', line)
    website = classifier.site_scope(line)
    for domain in changed:
        directory = '/conf/vhosts/%s/' % domain
        if website == 'website ' + domain or directory in line:
            line = re.sub('(' + re.escape(directory) + _FILE_LINE, r'\1', line)
            line = _LINE_WORD.sub(r'\1', line)
    return line


def config_errors_added(before, after, changed=None):
    """Why a change must be undone, judged by the web server's configuration test.

    `before` and `after` are the (exit status, output) of the test on either
    side of the change. OpenLiteSpeed ends the test with 1 after warnings and
    with 2 after any error. A fresh installation already warns about its stock
    Example virtual host, and a server with an error in one website keeps
    running, so a test that must be clean would refuse every change on such a
    server. Only what the change added counts: an error line that was not
    there before, or an exit status that became an error status without one.

    `changed` names the websites whose files the change edited, with False for
    a website that was restored. A change that only restores websites differs
    from the state before it by nothing but the text it puts back, and that
    text is each website's own configuration from before it was suspended. Its
    rewrite rules were commented out meanwhile, so an error in them was not
    reported and returns with them, in a message that need not name the
    website: OpenLiteSpeed reports a faulty rule under `[(null)] [REWRITE]`.
    Refusing such a change would keep the website, and a parent with its other
    children, suspended for good. A restore is therefore undone only for
    damage: a fatal message that was not there before, or a test that ends
    with another status than 0, 1 or 2. A change that suspends any website,
    and the files put back after a failure, keep the strict rule.

    None marks a website that was suspended already and stays so, its file
    only written again in the present form. Restoring a parent does that to a
    child that is suspended on its own. It does not make the restore a
    suspension; on its own it is judged by the strict rule.
    """
    from plogical import olsStockClassifier
    changed = changed or {}
    restore = False in changed.values() and True not in changed.values()

    def errors(output):
        # The upgrader's rule for an error line, with no website excused.
        return olsStockClassifier.blocking_errors(output, {})

    known = collections.Counter(_comparable(line, olsStockClassifier, changed) for line in errors(before[1]))
    added = []
    for line in errors(after[1]):
        key = _comparable(line, olsStockClassifier, changed)
        if known[key]:
            known[key] -= 1
        else:
            added.append(line)
    if restore:
        refused = [line for line in added if '[FATAL]' in line]
        explained = after[0] in (0, 1, 2) or after[0] == before[0]
    else:
        refused = added
        explained = after[0] in (0, 1) or after[0] == before[0]
    if not refused and not explained:
        refused.append('The configuration test ended with status %s; before the change it ended with %s. %s'
                       % (after[0], before[0], after[1].strip()[-1500:]))
    return refused


def config_check(command, before=None, changed=None):
    """Run the web server's configuration test and return (exit status, output).

    Given the result from before a change, raise when the change added an
    error; config_errors_added describes `changed`. Without it, raise only
    when the test gave no result, which leaves nothing to compare a change
    with.
    """
    try:
        state = _run(command)
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError('The web server configuration test could not be run: %s' % error) from error
    if before is None:
        if state[0] not in (0, 1, 2):
            raise RuntimeError('The web server configuration test gave no result (exit status %s): %s'
                               % (state[0], state[1][-2000:]))
        return state
    added = config_errors_added(before, state, changed)
    if added:
        raise RuntimeError('Web server configuration activation failed: ' + '\n'.join(added)[:2000])
    return state


def server_update(server_root, activate=True):
    """A VhostUpdate for the installed web server.

    With `activate` false the caller restarts the server itself after its own
    remaining steps; the configuration is still tested here.
    """
    root = Path(server_root)
    binary = root / 'bin' / 'openlitespeed'
    if not binary.exists():
        binary = root / 'bin' / 'lshttpd'

    def reload():
        if activate:
            _checked([str(root / 'bin' / 'lswsctrl'), 'restart'])
    return VhostUpdate(root, lambda *state: config_check([str(binary), '-t'], *state), reload)


def change_suspension(user_id, domain, action):
    """Runs through the existing privileged command service, with fresh ACLs."""
    action = normalize_action(action)
    validate_domain(domain)
    from django.db import transaction
    from loginSystem.models import Administrator
    from websiteFunctions.models import Websites, ChildDomains
    from plogical.acl import ACLManager
    acl = ACLManager.loadedACL(user_id)
    if ACLManager.currentContextPermission(acl, 'suspendWebsite') == 0:
        raise ValueError('You do not have permission to suspend domains.')
    admin = Administrator.objects.get(pk=user_id)
    if ACLManager.checkOwnership(domain, admin, acl) != 1:
        raise ValueError('You do not own this domain.')
    root = Path('/usr/local/lsws')
    with suspension_lock(root):
        # Provisioning can hold the lock while issuing certificates. Re-read
        # permission/account state after waiting rather than using a stale ACL.
        acl = ACLManager.loadedACL(user_id)
        if ACLManager.currentContextPermission(acl, 'suspendWebsite') == 0:
            raise ValueError('You do not have permission to suspend domains.')
        admin = Administrator.objects.get(pk=user_id)
        with server_update(root) as update:
            # Lock the parent first in both flows, so child and parent operations
            # cannot race to overwrite an independently suspended child's state.
            child = ChildDomains.objects.filter(domain=domain).first()
            parent_id = child.master_id if child else Websites.objects.get(domain=domain).pk
            with transaction.atomic():
                parent = Websites.objects.select_for_update().get(pk=parent_id)
                if ACLManager.checkOwnership(domain, admin, acl) != 1:
                    raise ValueError('Domain ownership changed; please retry.')
                new_state = int(action == 'Un-Suspend')
                if child:
                    target = ChildDomains.objects.select_for_update().get(pk=child.pk, master=parent)
                    changes = [(target.domain, not (parent.state and new_state))]
                else:
                    target = parent
                    children = list(ChildDomains.objects.select_for_update().filter(master=parent))
                    changes = [(parent.domain, not new_state)]
                    changes.extend((item.domain, not (new_state and item.state)) for item in children)
                update.apply(changes)
                target.state = new_state
                target.save(update_fields=['state'])
            return {'websiteStatus': 1, 'error_message': 'None',
                    'state': 'Active' if (parent.state and target.state) else 'Suspended',
                    'independentState': target.state,
                    'parentSuspended': bool(child and not parent.state)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--action', type=normalize_action, choices=('Suspend', 'Un-Suspend'), required=True)
    args = parser.parse_args()
    sys.path.insert(0, '/usr/local/CyberCP')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    import django
    django.setup()
    try:
        print(json.dumps(change_suspension(args.user_id, args.domain, args.action)))
    except Exception as error:
        print(json.dumps({'websiteStatus': 0, 'error_message': str(error)}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
