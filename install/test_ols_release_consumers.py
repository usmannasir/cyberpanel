import ast
import builtins
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from test_custom_ols_platforms import ROOT, binary_configs, load_method


def load_modsec():
    path = ROOT / 'plogical' / 'modSec.py'
    tree = ast.parse(path.read_text())
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'modSec')
    selected = []
    for node in original.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MODSEC_COMPATIBLE' for t in node.targets):
            selected.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in ('detectPlatform', 'downloadCompatibleModSec'):
            selected.append(node)
    names = [n.name for n in selected if isinstance(n, ast.FunctionDef)]
    if len(names) != len(set(names)):
        raise AssertionError('A release consumer is shadowed by a duplicate method')
    original.body = selected
    module = ast.fix_missing_locations(ast.Module(body=[original], type_ignores=[]))
    namespace = dict(os=os, tempfile=tempfile, subprocess=subprocess, shutil=shutil, logging=mock.Mock())
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['modSec']


class ReleaseConsumerTests(unittest.TestCase):
    def test_every_installer_and_modsecurity_action_selects_the_same_artifacts(self):
        install = binary_configs(ROOT / 'install/installCyberPanel.py', 'InstallCyberPanel')
        upgrade = binary_configs(ROOT / 'plogical/upgrade.py', 'Upgrade')
        self.assertEqual(install, upgrade)
        self.assertEqual(set(install), {'ubuntu', 'ubuntu26', 'rhel8', 'rhel9', 'rhel10'})
        modsec = load_modsec().MODSEC_COMPATIBLE
        self.assertEqual(set(modsec), set(install))
        for platform, config in install.items():
            with self.subTest(platform=platform):
                self.assertEqual(modsec[platform]['url'], config['modsec_url'])
                self.assertEqual(modsec[platform]['sha256'], config['sha256']['modsec'])

    def test_modsecurity_detects_native_abis_and_refuses_unsupported_versions(self):
        detect = load_modsec().detectPlatform
        cases = [('ubuntu', '22.04', 'ubuntu'), ('ubuntu', '24.04', 'ubuntu'),
                 ('ubuntu', '26.04', 'ubuntu26'), ('ubuntu', '20.04', None),
                 ('almalinux', '10.1', 'rhel10'), ('rocky', '9', 'rhel9'),
                 ('rhel', '8.10', 'rhel8'), ('debian', '12', 'ubuntu'),
                 ('debian', '10', None), ('alpine', '3.22', None)]
        for name, version, expected in cases:
            with self.subTest(name=name, version=version):
                content = 'ID="%s"\nVERSION_ID="%s"\n' % (name, version)
                with mock.patch.object(builtins, 'open', mock.mock_open(read_data=content)):
                    self.assertEqual(detect(), expected)
        with mock.patch.object(builtins, 'open', side_effect=OSError('missing')):
            self.assertIsNone(detect())

    def test_checksum_verifiers_fail_closed_and_accept_only_matching_bytes(self):
        with tempfile.NamedTemporaryFile() as artifact:
            artifact.write(b'verified binary')
            artifact.flush()
            digest = hashlib.sha256(b'verified binary').hexdigest()
            for path, class_name, static in [('install/installCyberPanel.py', 'InstallCyberPanel', False),
                                             ('plogical/upgrade.py', 'Upgrade', True)]:
                verify = load_method(ROOT / path, class_name, 'verifyChecksum')
                for expected, accepted in [(digest, True), (digest.upper(), True), ('0' * 64, False),
                                           (None, False), ('', False), ('PENDING_CORE_2_5_4_UBUNTU', False)]:
                    with self.subTest(path=path, expected=expected):
                        args = (artifact.name, expected)
                        self.assertEqual(verify(*args) if static else verify(None, *args), accepted)

    def test_modsecurity_refuses_unpublished_hash_without_downloading(self):
        target = load_modsec()
        target.MODSEC_COMPATIBLE['ubuntu']['sha256'] = 'PENDING_MODSEC_2_5_4_UBUNTU'
        with mock.patch.object(subprocess, 'call') as download, \
             mock.patch.object(builtins, 'open') as opening:
            self.assertFalse(target.downloadCompatibleModSec('ubuntu'))
        download.assert_not_called()
        opening.assert_not_called()

    def test_modsecurity_refuses_stock_core_before_any_download(self):
        target = load_modsec()
        target.MODSEC_COMPATIBLE['ubuntu']['sha256'] = hashlib.sha256(b'module').hexdigest()
        with mock.patch.object(builtins, 'open', return_value=io.BytesIO(b'stock core')), \
             mock.patch.object(subprocess, 'call') as download:
            self.assertFalse(target.downloadCompatibleModSec('ubuntu'))
        download.assert_not_called()

    def test_verified_modsecurity_is_installed_only_when_dependencies_resolve(self):
        for mismatch, missing, accepted in [(False, False, True), (True, False, False), (False, True, False)]:
            with self.subTest(mismatch=mismatch, missing=missing), tempfile.TemporaryDirectory() as directory:
                target = load_modsec()
                target.MODSEC_COMPATIBLE['ubuntu']['sha256'] = hashlib.sha256(b'module').hexdigest()
                real_open = builtins.open
                real_temp = tempfile.TemporaryDirectory

                def opening(path, *args, **kwargs):
                    if str(path) == '/usr/local/lsws/bin/openlitespeed':
                        return io.BytesIO(b'core cyberpanel_lsi_api_abi_v1')
                    return real_open(path, *args, **kwargs)

                def download(args):
                    Path(args[-1]).write_bytes(b'wrong' if mismatch else b'module')
                    return 0

                result = SimpleNamespace(returncode=0, stdout='libcrypto => not found' if missing else 'libcrypto => /lib/libcrypto.so', stderr='')
                with mock.patch.object(builtins, 'open', side_effect=opening), \
                     mock.patch.object(tempfile, 'TemporaryDirectory', side_effect=lambda **kw: real_temp(dir=directory)), \
                     mock.patch.object(subprocess, 'call', side_effect=download), \
                     mock.patch.object(subprocess, 'run', return_value=result), \
                     mock.patch.object(os.path, 'exists', return_value=False), \
                     mock.patch.object(os, 'replace') as replace:
                    self.assertEqual(target.downloadCompatibleModSec('ubuntu'), accepted)
                self.assertEqual(replace.call_count, int(accepted))

class BundleFixture:
    """Run the real consumer method against an isolated filesystem and service."""
    core = '/usr/local/lsws/bin/openlitespeed'
    module = '/usr/local/lsws/modules/cyberpanel_ols.so'
    waf = '/usr/local/lsws/modules/mod_security.so'

    def __init__(self, directory, source, class_name, failure=None, module=True, waf=True):
        self.root = Path(directory)
        self.failure = failure
        self.active = True
        self.commands = []
        self.downloads = []
        self.old = {self.core: b'old-core'}
        if module:
            self.old[self.module] = b'old-module'
        if waf:
            self.old[self.waf] = b'old-waf'
        for name, data in self.old.items():
            target = self.path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.active_bytes = b'old-core'
        payloads = {'binary': b'new-core', 'module': b'new-module', 'modsec': b'new-waf'}
        config = binary_configs(source, class_name)['ubuntu']
        self.by_url = {config[key]: kind for key, kind in
                       [('url', 'binary'), ('module_url', 'module'), ('modsec_url', 'modsec')]}
        fixture_digests = {config['sha256'][kind]: hashlib.sha256(data).hexdigest()
                           for kind, data in payloads.items()}
        fake_os = SimpleNamespace(
            path=SimpleNamespace(exists=lambda p: self.path(p).exists(),
                                 samefile=self.samefile, join=os.path.join,
                                 dirname=os.path.dirname, basename=os.path.basename),
            makedirs=lambda p, **kw: os.makedirs(self.path(p), **kw),
            chmod=lambda p, mode: os.chmod(self.path(p), mode),
            replace=self.replace, remove=lambda p: os.remove(self.path(p)))
        fake_temp = SimpleNamespace(
            TemporaryDirectory=lambda **kw: tempfile.TemporaryDirectory(dir=self.root),
            mkdtemp=lambda **kw: tempfile.mkdtemp(prefix=kw['prefix'], dir=self.path(kw['dir'])))
        real_import = builtins.__import__

        def imports(name, *args, **kwargs):
            if name == 'tempfile':
                return fake_temp
            if name == 'time':
                return SimpleNamespace(sleep=lambda seconds: None)
            return real_import(name, *args, **kwargs)

        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and
                    n.name in ('installCustomOLSBinaries', 'verifyChecksum', 'checkGlibcCompat', 'rollbackOLSBinary')]
        namespace = dict(os=fake_os, re=__import__('re'), shutil=SimpleNamespace(copy2=self.copy2,
                                               move=lambda src, dst: shutil.move(self.path(src), self.path(dst))),
                         subprocess=SimpleNamespace(run=self.run, PIPE=subprocess.PIPE),
                         time=SimpleNamespace(sleep=lambda seconds: None), logging=mock.Mock(),
                         open=lambda p, *a, **kw: open(self.path(p), *a, **kw),
                         __builtins__=dict(vars(builtins), __import__=imports))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                     str(source), 'exec'), namespace)
        target_class = namespace[class_name]
        target_class.stdOut = staticmethod(mock.Mock())
        target = target_class() if class_name == 'InstallCyberPanel' else target_class
        target.detectArchitecture = lambda: True
        target.detectPlatform = lambda: 'ubuntu'

        def download(url, destination):
            kind = self.by_url[url]
            self.downloads.append(kind)
            if self.failure in ('missing-module', 'missing-waf') and kind == (
                    'module' if self.failure == 'missing-module' else 'modsec'):
                return False
            self.path(destination).parent.mkdir(parents=True, exist_ok=True)
            self.path(destination).write_bytes(b'corrupted' if self.failure == 'corrupt-waf'
                                              and kind == 'modsec' else payloads[kind])
            return True

        target.downloadCustomBinary = download
        verify = target.verifyChecksum
        target.verifyChecksum = lambda path, published: verify(path, fixture_digests[published])
        self.call = target.installCustomOLSBinaries
        self.rollback = getattr(target, 'rollbackOLSBinary', None)

    def path(self, path):
        path = Path(path)
        if (str(path).startswith('/usr/local/lsws') or
                str(path) in ('/tmp/openlitespeed-custom', '/tmp/cyberpanel_ols.so', '/tmp/mod_security.so')):
            return self.root / str(path).lstrip('/')
        return path

    def samefile(self, proc, target):
        return (self.active and self.failure != 'unrelated-process' and
                self.path(target).read_bytes() == self.active_bytes)

    def copy2(self, source, destination):
        if self.failure == 'backup' and str(destination).endswith('mod_security.so.backup'):
            raise OSError('injected backup failure')
        return shutil.copy2(self.path(source), self.path(destination))

    def replace(self, source, destination):
        if self.failure == 'module-write' and str(source).endswith('module.new'):
            raise OSError('injected module replacement failure')
        return os.replace(self.path(source), self.path(destination))

    def run(self, args, **kwargs):
        self.commands.append(tuple(args))
        stdout, code = '', 0
        if args[0] == 'ldd':
            stdout = 'libmissing.so => not found' if self.failure == 'waf-abi' and args[1].endswith('/modsec') else 'libc.so => /lib/libc.so'
        elif args[0] == 'pgrep':
            code = 0 if self.active else 1
        elif args[-1] == 'status':
            stdout = 'litespeed is running with PID 123.' if self.active else '[ERROR] litespeed is not running.'
        elif args[-1] == 'stop':
            if self.failure == 'stop':
                code = 1
            else:
                self.active = False
        elif args[-1] == 'start':
            data = self.path(self.core).read_bytes()
            self.active = not (self.failure == 'startup' and data == b'new-core')
            self.active_bytes = data
            code = 0 if self.active else 1
        elif args[-1] == '-v':
            if self.failure == 'version-timeout':
                raise subprocess.TimeoutExpired(args, 10)
            stdout = 'OpenLiteSpeed/2.5.5'
        else:
            raise AssertionError('Unexpected command: ' + repr(args))
        return SimpleNamespace(returncode=code, stdout=stdout, stderr='')

    def bundle(self):
        return {p: self.path(p).read_bytes() for p in (self.core, self.module, self.waf)
                if self.path(p).exists()}


class BundleTransactionTests(unittest.TestCase):
    consumers = [('install/installCyberPanel.py', 'InstallCyberPanel'),
                 ('plogical/upgrade.py', 'Upgrade')]

    def test_required_download_integrity_and_abi_failures_do_not_touch_bundle_or_service(self):
        for source, cls in self.consumers:
            for failure in ('corrupt-waf', 'missing-module', 'missing-waf', 'waf-abi'):
                with self.subTest(consumer=cls, failure=failure), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, failure)
                    self.assertFalse(f.call())
                    self.assertEqual(f.bundle(), f.old)
                    self.assertTrue(f.active)
                    self.assertFalse(any(args[-1] in ('stop', 'start') for args in f.commands))

    def test_backup_failure_aborts_before_service_stop_or_any_replacement(self):
        for source, cls in self.consumers:
            with self.subTest(consumer=cls), tempfile.TemporaryDirectory() as directory:
                f = BundleFixture(directory, ROOT / source, cls, 'backup')
                self.assertFalse(f.call())
                self.assertEqual(f.bundle(), f.old)
                self.assertTrue(f.active)
                self.assertFalse(any(args[-1] in ('stop', 'start') for args in f.commands))

    def test_start_failure_restores_all_previous_bundle_files_and_service(self):
        for source, cls in self.consumers:
            with self.subTest(consumer=cls), tempfile.TemporaryDirectory() as directory:
                f = BundleFixture(directory, ROOT / source, cls, 'startup')
                self.assertFalse(f.call())
                self.assertEqual(f.bundle(), f.old)
                self.assertTrue(f.active)
                self.assertEqual(f.active_bytes, b'old-core')

    def test_rollback_removes_modules_that_did_not_previously_exist(self):
        for source, cls in self.consumers:
            with self.subTest(consumer=cls), tempfile.TemporaryDirectory() as directory:
                f = BundleFixture(directory, ROOT / source, cls, 'startup', module=False, waf=False)
                self.assertFalse(f.call())
                self.assertEqual(f.bundle(), f.old)
                self.assertTrue(f.active)

    def test_write_and_version_failures_restore_bundle_and_service(self):
        for source, cls in self.consumers:
            for failure in ('module-write', 'version-timeout'):
                with self.subTest(consumer=cls, failure=failure), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, failure)
                    self.assertFalse(f.call())
                    self.assertEqual(f.bundle(), f.old)
                    self.assertTrue(f.active)

    def test_unrelated_process_and_failed_stop_cannot_allow_bundle_replacement(self):
        for source, cls in self.consumers:
            for failure in ('unrelated-process', 'stop'):
                with self.subTest(consumer=cls, failure=failure), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, failure)
                    self.assertFalse(f.call())
                    self.assertEqual(f.bundle(), f.old)
                    self.assertTrue(f.active)

    def test_legacy_fallback_restores_files_and_honors_explicit_absence_markers(self):
        for had_module, had_waf in ((False, False), (True, True)):
            with self.subTest(module=had_module, waf=had_waf), tempfile.TemporaryDirectory() as directory:
                f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade',
                                  module=had_module, waf=had_waf)
                backup = f.path('/usr/local/lsws/backup-legacy-test')
                backup.mkdir()
                for target, name in ((f.core, 'openlitespeed.backup'),
                                     (f.module, 'cyberpanel_ols.so.backup'),
                                     (f.waf, 'mod_security.so.backup')):
                    if target in f.old:
                        (backup / name).write_bytes(f.old[target])
                    else:
                        (backup / (name + '.absent')).touch()
                    f.path(target).parent.mkdir(parents=True, exist_ok=True)
                    f.path(target).write_bytes(b'new-file')
                f.active_bytes = b'new-file'
                self.assertTrue(f.rollback(str(backup), f.core, f.module))
                self.assertEqual(f.bundle(), f.old)
                self.assertTrue(f.active)
                self.assertEqual(f.active_bytes, b'old-core')

    def test_success_installs_the_complete_required_bundle(self):
        for source, cls in self.consumers:
            for waf in (False, True):
                with self.subTest(consumer=cls, existing_waf=waf), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, waf=waf)
                    self.assertTrue(f.call())
                    expected = {f.core: b'new-core', f.module: b'new-module'}
                    if waf or cls == 'InstallCyberPanel':
                        expected[f.waf] = b'new-waf'
                        self.assertIn('modsec', f.downloads)
                    else:
                        self.assertNotIn('modsec', f.downloads)
                    self.assertEqual(f.bundle(), expected)
                    self.assertTrue(f.active)
                    self.assertEqual(f.active_bytes, b'new-core')


if __name__ == '__main__':
    unittest.main()
