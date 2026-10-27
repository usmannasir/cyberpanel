"""Atomic, checksum-pinned OLS support assets; never installs website PHP.

The caller owns stopping/starting OLS and must roll this transaction back if its
paired core/module transaction fails. No archive paths are extracted directly.
"""
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile


SECURITY_ASSETS_URL = 'https://cyberpanel.net/ols-security-assets-2.5.6-php8.3.36-x86_64.tar.gz'
SECURITY_ASSETS_SHA256 = '03b360647adc88cf210dfc73d00bbbc68a8a5005e13b45d2cf75d5a62bf27c31'


_EXACT = frozenset(('VERSION', 'admin/fcgi-bin/admin_php',
    'admin/cyberpanel-php/etc/php.ini', 'admin/cyberpanel-php/build.json',
    'admin/cyberpanel-php/licenses/php.txt', 'admin/cyberpanel-php/licenses/openssl.txt',
    'admin/cyberpanel-php/licenses/libxml2.txt', 'admin/misc/lsup.sh',
    'fcgi-bin/lsnode.js', 'fcgi-bin/lsnodesm.js',
    'lsns/bin/lscgctl', 'lsns/bin/lspkgctl', 'lsns/bin/lssetup', 'lsns/bin/lsnsctl'))
_RUNTIME = 'admin/fcgi-bin/admin_php'
_INI = 'admin/cyberpanel-php/etc/php.ini'
_PROBE = r'''<?php
$required=['openssl_encrypt','openssl_decrypt','openssl_random_pseudo_bytes',
'xml_parser_create','socket_create','session_start','posix_geteuid','ctype_digit'];
$missing=array_values(array_filter($required, function($name){return !function_exists($name);}));
$parser=xml_parser_create(); $xml=xml_parse($parser,'<test>ok</test>',true); xml_parser_free($parser);
$dom=class_exists('DOMDocument') ? new DOMDocument() : null;
$dom_ok=$dom && $dom->loadHTML('<table><tr><td>cp-admin-test</td></tr></table>')
    && $dom->getElementsByTagName('td')->item(0)->textContent==='cp-admin-test';
$key=random_bytes(32); $iv=random_bytes(16); $cipher=openssl_encrypt('cp-admin-test','aes-256-cbc',$key,0,$iv);
echo json_encode(['version'=>PHP_VERSION,'sapi'=>PHP_SAPI,'opcache'=>phpversion('Zend OPcache'),
'openssl'=>OPENSSL_VERSION_TEXT,'libxml'=>LIBXML_DOTTED_VERSION,'missing'=>$missing,
'xml'=>$xml,'dom'=>$dom_ok,'crypto'=>openssl_decrypt($cipher,'aes-256-cbc',$key,0,$iv)==='cp-admin-test',
'upload_progress'=>ini_get('session.upload_progress.enabled'),
'ini'=>php_ini_loaded_file(),'scanned'=>php_ini_scanned_files()]);
'''


def _allowed(path):
    parts = PurePosixPath(path).parts
    if not parts or path.startswith('/') or any(p in ('.', '..') for p in parts):
        return False
    if str(PurePosixPath(path)) != path or '\\' in path or '\x00' in path:
        return False
    if path in _EXACT:
        return True
    if path.startswith('admin/html/'):
        return PurePosixPath(path).suffix.lower() in (
            '.php', '.js', '.css', '.png', '.jpg', '.gif', '.svg', '.ico',
            '.woff', '.woff2', '.ttf', '.eot', '.map', '.txt', '.html', '.template')
    if path.startswith('add-ons/webcachemgr/'):
        return path == 'add-ons/webcachemgr/VERSION' or PurePosixPath(path).suffix in ('.php', '.js', '.css')
    return False


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _disable_fresh_webadmin(data):
    text = data.decode('utf-8')
    pattern = r'(?m)^([ \t]*)disableWebAdmin[ \t]+[^\r\n]*$'
    matches = list(re.finditer(pattern, text))
    if len(matches) > 1:
        raise RuntimeError('Ambiguous disableWebAdmin configuration')
    if matches:
        return re.sub(pattern, r'\1disableWebAdmin 1', text).encode('utf-8')
    return (text.rstrip() + '\n\ndisableWebAdmin 1\n').encode('utf-8')


class SecurityAssetsTransaction:
    """Prepare all bytes, validate PHP, then apply/rollback only approved paths."""

    def __init__(self, archive_path, expected_sha256, server_root='/usr/local/lsws', fresh_install=False):
        self.server_root = os.path.abspath(server_root)
        self.backup_dir = None
        self.touched = []
        self.created_dirs = []
        self.entries = []
        self._old = {}
        with open(archive_path, 'rb') as source:
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or '') or digest.hexdigest() != expected_sha256:
            raise RuntimeError('OLS security assets checksum mismatch')
        prepared = []
        with tarfile.open(archive_path, 'r:*') as archive:
            members = archive.getmembers()
            if len(members) > 5000 or sum(m.size for m in members) > 100 * 1024 * 1024:
                raise RuntimeError('OLS security assets archive exceeds limits')
            names = [m.name for m in members]
            if len(names) != len(set(names)) or any(not m.isfile() for m in members):
                raise RuntimeError('OLS security assets must contain unique regular files')
            if 'manifest.json' not in names:
                raise RuntimeError('OLS security assets manifest missing')
            manifest = json.load(archive.extractfile('manifest.json'))
            if manifest.get('release') != '2.5.6' or not isinstance(manifest.get('files'), list):
                raise RuntimeError('Unsupported OLS security assets manifest')
            seen = set()
            for item in manifest['files']:
                path = item.get('path', '')
                mode = item.get('mode')
                if not _allowed(path) or path in seen or mode not in (0o644, 0o755):
                    raise RuntimeError('Unapproved or duplicate OLS asset: ' + path)
                if 'existing_only' in item and not isinstance(item['existing_only'], bool):
                    raise RuntimeError('Invalid existing-only asset policy')
                seen.add(path)
                name = 'payload/' + path
                if name not in names:
                    raise RuntimeError('Missing OLS asset: ' + path)
                data = archive.extractfile(name).read()
                if _sha(data) != item.get('sha256'):
                    raise RuntimeError('OLS asset checksum mismatch: ' + path)
                if path == _INI:
                    ca_bundle = next((ca for ca in ('/etc/ssl/certs/ca-certificates.crt',
                        '/etc/pki/tls/certs/ca-bundle.crt', '/etc/ssl/cert.pem')
                        if os.path.isfile(ca) and os.path.getsize(ca) > 0), None)
                    if not ca_bundle:
                        raise RuntimeError('No system CA bundle for isolated WebAdmin PHP')
                    data += ('\nopenssl.cafile=\"' + ca_bundle + '\"\n').encode('utf-8')
                target = self._target(path)
                if item.get('existing_only'):
                    component = ('add-ons/webcachemgr' if path.startswith('add-ons/webcachemgr/')
                                 else 'lsns' if path.startswith('lsns/bin/') else None)
                    if component is None:
                        raise RuntimeError('Existing-only policy requires an optional component')
                    if not os.path.isdir(os.path.join(self.server_root, component)):
                        continue
                prepared.append((path, data, mode, target))
            if set(names) != {'manifest.json'} | {'payload/' + p for p in seen}:
                raise RuntimeError('Unlisted files in OLS security assets')
        if not {_RUNTIME, _INI}.issubset({p[0] for p in prepared}):
            raise RuntimeError('OLS security assets lack isolated WebAdmin runtime')
        if not fresh_install:
            config = self._target('conf/httpd_config.conf')
            with open(config, encoding='utf-8') as source:
                text = source.read()
            flags = re.findall(r'(?m)^[ \t]*disableWebAdmin[ \t]+([01])(?:[ \t]*(?:#.*)?)?$', text)
            if len(flags) > 1:
                raise RuntimeError('Ambiguous disableWebAdmin configuration')
            marker = self._target('admin/conf/enable_webadmin')
            if flags == ['0'] and not os.path.lexists(marker):
                # 1.9.4 adds this second gate; preserve the prior explicit setting.
                prepared.append(('admin/conf/enable_webadmin', b'', 0o644, marker))
        if fresh_install:
            target = self._target('conf/httpd_config.conf')
            with open(target, 'rb') as source:
                data = source.read()
            prepared.append(('conf/httpd_config.conf', _disable_fresh_webadmin(data),
                             stat.S_IMODE(os.stat(target).st_mode), target))
        try:
            self.backup_dir = tempfile.mkdtemp(prefix='.cyberpanel-security-backup-', dir=self.server_root)
            for index, (path, data, mode, target) in enumerate(prepared):
                old = None
                if os.path.lexists(target):
                    info = os.lstat(target)
                    if stat.S_ISLNK(info.st_mode):
                        if path != _RUNTIME:
                            raise RuntimeError('Linked OLS asset is unsupported: ' + path)
                        old = {'link': os.readlink(target), 'uid': info.st_uid, 'gid': info.st_gid}
                    elif stat.S_ISREG(info.st_mode):
                        saved = os.path.join(self.backup_dir, str(index) + '.old')
                        shutil.copy2(target, saved)
                        old = {'file': saved, 'uid': info.st_uid, 'gid': info.st_gid}
                    else:
                        raise RuntimeError('Non-file OLS asset: ' + path)
                staged = os.path.join(self.backup_dir, str(index) + '.new')
                with open(staged, 'wb') as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(staged, mode)
                if old and os.geteuid() == 0:
                    os.chown(staged, old['uid'], old['gid'])
                self.entries.append({'path': path, 'target': target, 'staged': staged, 'sha256': _sha(data)})
                self._old[path] = old
            self.verify(staged=True)
            with open(os.path.join(self.backup_dir, 'rollback.json'), 'w') as output:
                json.dump({'root': self.server_root, 'previous': self._old, 'entries': self.entries}, output, indent=2)
        except BaseException:
            if self.backup_dir:
                shutil.rmtree(self.backup_dir)
            raise

    def _target(self, path):
        pieces = list(PurePosixPath(path).parts)
        if pieces[:2] == ['admin', 'html']:
            html = os.path.join(self.server_root, 'admin', 'html')
            if os.path.islink(html):
                if os.readlink(html) not in ('html.open', './html.open'):
                    raise RuntimeError('Unrecognized WebAdmin document-root link')
                pieces[1] = 'html.open'
        current = self.server_root
        if os.path.islink(current) or not os.path.isdir(current):
            raise RuntimeError('Invalid OLS installation root')
        for piece in pieces[:-1]:
            current = os.path.join(current, piece)
            if os.path.islink(current) or (os.path.lexists(current) and not os.path.isdir(current)):
                raise RuntimeError('Unsafe OLS asset parent: ' + path)
        return os.path.join(self.server_root, *pieces)

    def verify(self, staged=False):
        files = {e['path']: e['staged'] if staged else e['target'] for e in self.entries}
        binary, ini = files[_RUNTIME], files[_INI]
        env = dict(os.environ)
        env.pop('PHPRC', None)
        env['PHP_INI_SCAN_DIR'] = ''
        with tempfile.TemporaryDirectory(prefix='php-check-', dir=self.backup_dir) as probe_dir:
            script = os.path.join(probe_dir, 'probe.php')
            with open(script, 'w') as output:
                output.write(_PROBE)
            result = subprocess.run([binary, '-c', ini, '-q', script], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, timeout=30)
            try:
                evidence = json.loads(result.stdout)
            except (ValueError, TypeError):
                raise RuntimeError('Isolated WebAdmin PHP probe failed')
            if (result.returncode or evidence.get('version') != '8.3.36'
                    or evidence.get('sapi') != 'litespeed' or evidence.get('opcache') is not False
                    or evidence.get('missing') or not evidence.get('xml') or not evidence.get('dom') or not evidence.get('crypto')
                    or evidence.get('upload_progress') not in ('0', '')
                    or evidence.get('scanned') not in (False, None, '')
                    or evidence.get('openssl') != 'OpenSSL 3.5.9 29 Sep 2026'
                    or evidence.get('libxml') != '2.15.3'):
                raise RuntimeError('Isolated WebAdmin PHP did not satisfy the security/runtime checks')
            for path, filename in files.items():
                if path.endswith('.php'):
                    check = subprocess.run([binary, '-c', ini, '-l', filename], env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                    if check.returncode:
                        raise RuntimeError('OLS PHP asset syntax check failed: ' + path)
        return evidence

    def apply(self):
        if self.touched:
            raise RuntimeError('OLS security assets transaction already applied')
        try:
            for entry in self.entries:
                target = self._target(entry['path'])
                if target != entry['target']:
                    raise RuntimeError('OLS asset target changed during staging')
                parent = os.path.dirname(target)
                missing = []
                while not os.path.exists(parent):
                    missing.append(parent)
                    parent = os.path.dirname(parent)
                for directory in reversed(missing):
                    os.mkdir(directory, 0o755)
                    self.created_dirs.append(directory)
                os.replace(entry['staged'], target)
                self.touched.append(entry)
            self.verify()
        except BaseException:
            self.rollback()
            raise

    def rollback(self):
        for entry in reversed(self.touched):
            target, old = entry['target'], self._old[entry['path']]
            if old is None:
                if os.path.lexists(target):
                    os.unlink(target)
            else:
                restored = os.path.join(self.backup_dir, 'restore')
                if os.path.lexists(restored):
                    os.unlink(restored)
                if 'link' in old:
                    os.symlink(old['link'], restored)
                    if os.geteuid() == 0:
                        os.lchown(restored, old['uid'], old['gid'])
                else:
                    shutil.copy2(old['file'], restored)
                    if os.geteuid() == 0:
                        os.chown(restored, old['uid'], old['gid'])
                os.replace(restored, target)
        self.touched.clear()
        for directory in reversed(self.created_dirs):
            os.rmdir(directory)
        self.created_dirs.clear()


def restore_security_assets(backup_dir, server_root='/usr/local/lsws'):
    """Restore the persisted asset half of a paired core rollback.

    The root-owned backup is retained. The caller must stop OLS first and validate
    its restored core/modules/configuration before restarting the service.
    """
    root = os.path.abspath(server_root)
    backup = os.path.abspath(backup_dir)
    if (os.path.dirname(backup) != root or not os.path.basename(backup).startswith('.cyberpanel-security-backup-')
            or os.path.islink(backup) or not os.path.isdir(backup)):
        raise RuntimeError('Invalid OLS security rollback directory')
    filename = os.path.join(backup, 'rollback.json')
    if os.path.islink(filename):
        raise RuntimeError('Linked OLS security rollback manifest')
    with open(filename) as source:
        saved = json.load(source)
    if saved.get('root') != root:
        raise RuntimeError('OLS security rollback belongs to another installation')
    tx = SecurityAssetsTransaction.__new__(SecurityAssetsTransaction)
    tx.server_root = root
    tx.backup_dir = backup
    tx.created_dirs = []
    tx.entries = saved['entries']
    tx.touched = list(tx.entries)
    tx._old = saved['previous']
    paths = [entry['path'] for entry in tx.entries]
    if len(paths) != len(set(paths)) or set(paths) != set(tx._old):
        raise RuntimeError('Invalid OLS security rollback entries')
    for index, entry in enumerate(tx.entries):
        path = entry['path']
        if (not _allowed(path) and path not in ('conf/httpd_config.conf', 'admin/conf/enable_webadmin')) or tx._target(path) != entry['target']:
            raise RuntimeError('Unapproved OLS security rollback target')
        old = tx._old[path]
        if old is not None:
            if 'link' in old:
                if path != _RUNTIME or 'file' in old:
                    raise RuntimeError('Unapproved linked OLS rollback target')
            elif 'file' in old:
                expected = os.path.join(backup, str(index) + '.old')
                if old['file'] != expected or os.path.islink(expected) or not os.path.isfile(expected):
                    raise RuntimeError('Invalid OLS security saved file')
            else:
                raise RuntimeError('Invalid OLS security rollback state')
    tx.rollback()
    return True
