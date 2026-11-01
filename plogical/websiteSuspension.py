"""Independent website/domain suspension with rollback on failed activation."""
import contextlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

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
    """Retain originals until both configuration activation and DB commit pass."""
    def __init__(self, server_root, check, reload):
        self.root = Path(server_root).resolve()
        self.check = check
        self.reload = reload
        self.originals = []

    def apply(self, changes):
        staged = []
        for domain, suspended in changes:
            validate_domain(domain)
            path = self.root / 'conf' / 'vhosts' / domain / 'vhost.conf'
            if path.is_symlink() or path.parent.is_symlink() or self.root not in path.resolve().parents:
                raise ValueError('Unsafe virtual-host configuration path.')
            metadata = path.stat()
            original = path.read_bytes()
            updated = render_suspension(original.decode('utf-8'), suspended).encode('utf-8')
            if updated != original:
                staged.append((path, original, updated, metadata))
        for path, original, updated, metadata in staged:
            self.originals.append((path, original, metadata))
            atomic_write(path, updated, metadata)
        if staged:
            self.check()
            self.reload()

    def rollback(self):
        for path, original, metadata in reversed(self.originals):
            atomic_write(path, original, metadata)
        if self.originals:
            self.check()
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


def _checked(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Web server configuration activation failed: ' + result.stdout[-2000:])


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
    binary = root / 'bin' / 'openlitespeed'
    if not binary.exists():
        binary = root / 'bin' / 'lshttpd'
    with suspension_lock(root):
        # Provisioning can hold the lock while issuing certificates. Re-read
        # permission/account state after waiting rather than using a stale ACL.
        acl = ACLManager.loadedACL(user_id)
        if ACLManager.currentContextPermission(acl, 'suspendWebsite') == 0:
            raise ValueError('You do not have permission to suspend domains.')
        admin = Administrator.objects.get(pk=user_id)
        with VhostUpdate(root, lambda: _checked([str(binary), '-t']),
                         lambda: _checked([str(root / 'bin' / 'lswsctrl'), 'restart'])) as update:
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
