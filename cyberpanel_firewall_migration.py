"""Explicit, backed-up CSF preservation for CyberPanel source upgrades."""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile

CSF_UPGRADE_MESSAGE = (
    'Upgrade stopped: CSF files were detected. Use --preserve-csf with the current '
    'upgrader to keep and verify the existing firewall, or complete a reviewed '
    'manual firewall migration. CSF has not been removed.'
)
CSF_PRESERVATION_VERSION = 1
STATE_ENV = 'CYBERPANEL_CSF_STATE'
ROOTS = ('/etc/csf', '/usr/local/csf', '/usr/sbin/csf', '/usr/sbin/lfd')
PLUGIN = '/usr/local/CyberCP/configservercsf'
REGISTRY = '/home/cyberpanel/plugins/configservercsf'


def preserving_csf():
    return bool(os.environ.get(STATE_ENV))


def _private_directory(directory):
    info = os.lstat(directory)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('CSF preservation state must be a private root-owned directory.')
    if os.path.realpath(directory) != os.path.abspath(directory):
        raise RuntimeError('CSF preservation state must not contain symlink components.')


def _run(command, allowed=(0,)):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if result.returncode not in allowed:
        raise RuntimeError('CSF preservation check failed: %s (exit %s)' %
                           (command[0], result.returncode))
    return result.stdout.strip()


def _service_state():
    return {unit: _run(['systemctl', 'show', unit, '--property=ActiveState',
                       '--property=UnitFileState', '--property=LoadState'])
            for unit in ('csf.service', 'lfd.service')}


def _tree(paths):
    result = {}
    def record(path):
        info = os.lstat(path)
        metadata = {'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}
        if os.path.islink(path):
            metadata['link'] = os.readlink(path)
        elif os.path.isfile(path):
            with open(path, 'rb') as source:
                metadata['sha256'] = hashlib.sha256(source.read()).hexdigest()
        elif os.path.isdir(path):
            metadata['directory'] = True
        result[path] = metadata
    for root in paths:
        if os.path.islink(root) or os.path.isfile(root):
            record(root)
        elif os.path.isdir(root):
            for directory, names, files in os.walk(root, followlinks=False):
                record(directory)
                names[:] = sorted(name for name in names if name != '__pycache__')
                for name in names:
                    if os.path.islink(os.path.join(directory, name)):
                        record(os.path.join(directory, name))
                for name in sorted(files):
                    if not name.endswith(('.pyc', '.pyo')):
                        record(os.path.join(directory, name))
    return result


def _check_link_coverage(files, roots):
    # A link alone is not a backup of its target. Standard CSF links point
    # within the captured installation; custom external targets need review.
    directories = [os.path.realpath(path) for path in roots
                   if os.path.isdir(path) and not os.path.islink(path)]
    regular_files = {os.path.realpath(path) for path in roots
                     if os.path.isfile(path) and not os.path.islink(path)}
    for path, metadata in files.items():
        if 'link' not in metadata:
            continue
        target = os.path.realpath(path)
        if target not in regular_files and not any(
                target == root or target.startswith(root + os.sep) for root in directories):
            raise RuntimeError('CSF link target is outside the recovery snapshot: ' + path)


def _rules():
    result = {}
    for name, command in (('ipv4', 'iptables-save'), ('ipv6', 'ip6tables-save'),
                          ('ipsets', 'ipset'), ('nft', 'nft')):
        executable = shutil.which(command)
        if not executable:
            if name == 'ipv4':
                raise RuntimeError('iptables-save is required to preserve CSF policy.')
            continue
        arguments = ['save'] if name == 'ipsets' else ['list', 'ruleset'] if name == 'nft' else []
        output = _run([executable] + arguments)
        result[name] = output + '\n'
    return result


def _normalized_rules(text):
    text = re.sub(r'\[[0-9]+:[0-9]+\]', '[0:0]', text)
    text = re.sub(r'counter packets [0-9]+ bytes [0-9]+', 'counter packets 0 bytes 0', text)
    # nft's expiration countdown changes while configured timeout policy does not.
    text = re.sub(r'\bexpires [0-9]+(?:[smhd]+[0-9]*)*', 'expires 0', text)
    lines = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        # ipset emits remaining member lifetimes on add lines. Keep the create
        # line's default timeout so a real policy change remains detectable.
        if line.startswith('add '):
            line = re.sub(r'\btimeout [0-9]+', 'timeout 0', line)
        lines.append(line)
    return '\n'.join(lines)


def _plugin_state():
    if not os.path.isdir(PLUGIN):
        return None
    if os.path.islink(PLUGIN) or not os.path.isfile(REGISTRY) or os.path.islink(REGISTRY):
        raise RuntimeError('Existing CSF panel integration needs a regular plugin registry entry before upgrading.')
    active = {}
    for name in ('settings.py', 'urls.py'):
        with open('/usr/local/CyberCP/CyberCP/' + name) as source:
            active[name] = 'configservercsf' in source.read()
    return {'files': _tree((PLUGIN,)), 'activation': active}


def prepare(directory):
    if os.geteuid() != 0:
        raise RuntimeError('CSF preservation must run as root.')
    _private_directory(directory)
    if os.path.lexists(os.path.join(directory, 'manifest.json')):
        raise RuntimeError('CSF preservation manifest already exists; do not overwrite a recovery snapshot.')
    if (os.path.islink('/etc/csf') or os.path.islink('/etc/csf/csf.conf')
            or not os.path.isfile('/etc/csf/csf.conf')):
        raise RuntimeError('A regular CSF configuration directory is required.')
    if not os.access('/usr/sbin/csf', os.X_OK):
        raise RuntimeError('The existing CSF executable is missing; no upgrade changes were made.')
    for unit in ('firewalld.service', 'ufw.service', 'imunify360.service'):
        if _run(['systemctl', 'is-active', unit], allowed=(0, 3, 4)) == 'active':
            raise RuntimeError('CSF preservation does not support an active competing firewall: ' + unit)
    roots = [path for path in ROOTS if os.path.lexists(path)]
    for unit in ('csf.service', 'lfd.service'):
        fragment = _run(['systemctl', 'show', unit, '--property=FragmentPath', '--value'])
        if fragment and os.path.isfile(fragment):
            roots.append(fragment)
    plugin = _plugin_state()
    if plugin is not None:
        roots.extend((PLUGIN, REGISTRY))
    files = _tree(roots)
    _check_link_coverage(files, roots)
    rules = _rules()
    manifest = {'version': 1, 'roots': roots, 'files': files, 'services': _service_state(),
                'plugin': plugin, 'csf_version': _run(['/usr/sbin/csf', '-v']),
                'rules': {name: hashlib.sha256(_normalized_rules(value).encode()).hexdigest()
                          for name, value in rules.items()}}
    previous = os.umask(0o077)
    try:
        with tarfile.open(os.path.join(directory, 'csf-files.tar.gz'), 'w:gz', dereference=False) as archive:
            for path in roots:
                archive.add(path, arcname=path.lstrip('/'), recursive=True)
        for name, value in rules.items():
            with open(os.path.join(directory, 'rules-' + name + '.txt'), 'w') as output:
                output.write(value)
        with open(os.path.join(directory, 'manifest.json'), 'x') as output:
            json.dump(manifest, output, sort_keys=True)
    finally:
        os.umask(previous)
    verify(directory)
    print('CSF configuration, policy and service snapshot saved to ' + directory)


def verify(directory):
    _private_directory(directory)
    path = os.path.join(directory, 'manifest.json')
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('CSF preservation manifest must be a private root-owned regular file.')
    with open(path) as source:
        manifest = json.load(source)
    if manifest.get('version') != 1:
        raise RuntimeError('Unsupported CSF preservation manifest version.')
    if _tree(manifest['roots']) != manifest['files']:
        raise RuntimeError('CSF configuration or executable files changed; recovery snapshot retained at ' + directory)
    if _service_state() != manifest['services']:
        raise RuntimeError('CSF/LFD service state changed; recovery snapshot retained at ' + directory)
    if _plugin_state() != manifest['plugin']:
        raise RuntimeError('CSF panel integration changed; recovery snapshot retained at ' + directory)
    actual = {name: hashlib.sha256(_normalized_rules(value).encode()).hexdigest()
              for name, value in _rules().items()}
    if actual != manifest['rules']:
        raise RuntimeError('Firewall policy changed during the upgrade; review the retained rule snapshots at ' + directory)
    return True


def requireCSFMigration():
    if preserving_csf():
        try:
            verify(os.environ[STATE_ENV])
            return
        except Exception as error:
            print(str(error), file=sys.stderr)
    elif os.path.lexists('/etc/csf'):
        print(CSF_UPGRADE_MESSAGE, file=sys.stderr)
    else:
        return
    raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'verify'))
    parser.add_argument('directory')
    args = parser.parse_args()
    try:
        (prepare if args.operation == 'prepare' else verify)(args.directory)
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
