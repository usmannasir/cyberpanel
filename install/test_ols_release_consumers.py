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
        self.assertEqual(set(install), {'ubuntu20', 'ubuntu', 'ubuntu26', 'rhel8', 'rhel9', 'rhel10'})
        modsec = load_modsec().MODSEC_COMPATIBLE
        self.assertEqual(set(modsec), set(install))
        for platform, config in install.items():
            with self.subTest(platform=platform):
                self.assertEqual(modsec[platform]['url'], config['modsec_url'])
                self.assertEqual(modsec[platform]['sha256'], config['sha256']['modsec'])
                self.assertEqual(modsec[platform]['core_sha256'], config['sha256']['binary'])

    def test_modsecurity_detects_native_abis_and_refuses_unsupported_versions(self):
        detect = load_modsec().detectPlatform
        cases = [('ubuntu', '22.04', 'ubuntu'), ('ubuntu', '24.04', 'ubuntu'),
                 ('ubuntu', '26.04', 'ubuntu26'), ('ubuntu', '20.04', 'ubuntu20'),
                 ('ubuntu', '18.04', None), ('ubuntu', '20.10', None),
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

    def test_upgrade_aborts_on_failed_or_inconclusive_runtime_probe(self):
        verify = load_method(ROOT / 'plogical/upgrade.py', 'Upgrade', 'checkGlibcCompat')
        verify.__globals__['subprocess'] = subprocess
        for code, output in ((1, 'not a dynamic executable'), (0, ''),
                             (0, 'libfoo.so => not found'), (1, 'libc.so => /lib/libc.so')):
            result = SimpleNamespace(returncode=code, stdout=output, stderr='')
            with self.subTest(code=code, output=output), mock.patch.object(subprocess, 'run', return_value=result):
                self.assertFalse(verify('candidate'))
        with mock.patch.object(subprocess, 'run', side_effect=OSError('ldd unavailable')):
            self.assertFalse(verify('candidate'))

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

    def test_modsecurity_refuses_an_older_custom_core_even_with_matching_api_marker(self):
        target = load_modsec()
        with mock.patch.object(builtins, 'open', return_value=io.BytesIO(b'old-core cyberpanel_lsi_api_abi_v1')), \
             mock.patch.object(subprocess, 'call') as download:
            self.assertFalse(target.downloadCompatibleModSec('ubuntu'))
        download.assert_not_called()

    def test_verified_modsecurity_is_installed_only_when_dependencies_resolve(self):
        for mismatch, missing, accepted in [(False, False, True), (True, False, False), (False, True, False)]:
            with self.subTest(mismatch=mismatch, missing=missing), tempfile.TemporaryDirectory() as directory:
                target = load_modsec()
                target.MODSEC_COMPATIBLE['ubuntu']['sha256'] = hashlib.sha256(b'module').hexdigest()
                target.MODSEC_COMPATIBLE['ubuntu']['core_sha256'] = hashlib.sha256(b'core cyberpanel_lsi_api_abi_v1').hexdigest()
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
    admin = '/usr/local/lsws/admin/fcgi-bin/admin_php'

    def __init__(self, directory, source, class_name, failure=None, module=True, waf=True):
        self.root = Path(directory)
        self.failure = failure
        self.active = True
        self.commands = []
        self.downloads = []
        self.start_bundles = []
        self.old = {self.core: b'old-core', self.admin: b'old-admin'}
        if module:
            self.old[self.module] = b'old-module'
        if waf:
            self.old[self.waf] = b'old-waf'
        for name, data in self.old.items():
            target = self.path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.active_bytes = b'old-core'
        payloads = {'binary': b'new-core', 'module': b'new-module', 'modsec': b'new-waf', 'assets': b'verified-assets'}
        config = binary_configs(source, class_name)['ubuntu']
        self.by_url = {config[key]: kind for key, kind in
                       [('url', 'binary'), ('module_url', 'module'), ('modsec_url', 'modsec')]}
        fixture_digests = {config['sha256'][kind]: hashlib.sha256(data).hexdigest()
                           for kind, data in payloads.items() if kind != 'assets'}
        fake_os = SimpleNamespace(
            path=SimpleNamespace(exists=lambda p: self.path(p).exists(),
                                 lexists=lambda p: os.path.lexists(self.path(p)),
                                 samefile=self.samefile, join=os.path.join,
                                 dirname=os.path.dirname, basename=os.path.basename),
            makedirs=lambda p, **kw: os.makedirs(self.path(p), **kw),
            fsync=os.fsync, chmod=lambda p, mode: os.chmod(self.path(p), mode),
            lstat=lambda p: os.lstat(self.path(p)),
            chown=lambda p, uid, gid, **kw: os.chown(self.path(p), uid, gid, **kw),
            replace=self.replace, remove=lambda p: os.remove(self.path(p)))
        fake_temp = SimpleNamespace(
            TemporaryDirectory=lambda **kw: tempfile.TemporaryDirectory(dir=self.root),
            mkdtemp=lambda **kw: tempfile.mkdtemp(prefix=kw['prefix'], dir=self.path(kw['dir'])))
        real_import = builtins.__import__

        fixture = self
        assets_url = 'https://fixture.invalid/security-assets.tar.gz'
        self.by_url[assets_url] = 'assets'

        class FixtureService:
            def __init__(self, *args, **kwargs):
                self.unit = None

            def prepare_state(self):
                state = self.state()
                self.verify_mapped_bundle(state)
                return state

            def state(self):
                fixture.run(['lswsctrl', 'status'])
                if fixture.active and not fixture.samefile('/proc/123/exe', fixture.core):
                    raise RuntimeError('Fixture master differs from the installed binary')
                return (123, '1', None) if fixture.active else None

            def settled_state(self):
                return self.state()

            def verify_mapped_bundle(self, state):
                pass  # Real mapped-image verification runs in the native controller fixture.

            def change(self, action, expected):
                if self.state() != expected:
                    raise RuntimeError('Fixture service changed')
                result = fixture.run(['lswsctrl', action])
                if result.returncode or bool(self.state()) != (action == 'start'):
                    raise RuntimeError('Fixture controller failed: ' + action)
                return self.state()

        class AssetTransaction:
            # The helper's native PHP/archive tests live in test_ols_security_assets.
            # This fixture checks consumer sequencing and shared rollback behavior.
            def __init__(self, archive, digest, **kwargs):
                if class_name == 'Upgrade' and kwargs.get('webadmin_policy') != 'preserve':
                    raise AssertionError('The upgrader must explicitly preserve the WebAdmin gate')
                if fixture.failure == 'asset-validation':
                    raise RuntimeError('injected asset validation failure')
                self.backup_dir = tempfile.mkdtemp(dir=fixture.root)
                (Path(self.backup_dir) / 'rollback.json').write_text('{"previous":{},"entries":[]}')
                self.applied = False
                self.touched = []

            def apply(self):
                if fixture.active:
                    raise AssertionError('Assets must be replaced only while OLS is stopped')
                fixture.path(fixture.admin).write_bytes(b'new-admin')
                self.applied = True
                self.touched.append(fixture.admin)
                if fixture.failure == 'asset-apply':
                    raise RuntimeError('injected asset write failure')

            def rollback(self):
                if self.applied:
                    if fixture.active:
                        raise AssertionError('Assets must be restored only while OLS is stopped')
                    fixture.path(fixture.admin).write_bytes(fixture.old[fixture.admin])
                    self.applied = False

        def restore_assets(backup_dir, **kwargs):
            if fixture.active:
                raise AssertionError('Persisted asset restore must follow service stop')
            fixture.path(fixture.admin).write_bytes(fixture.old[fixture.admin])

        def imports(name, *args, **kwargs):
            if name == 'plogical.olsSecurityAssets':
                return SimpleNamespace(SecurityAssetsTransaction=AssetTransaction,
                    SECURITY_ASSETS_URL=assets_url, SECURITY_ASSETS_SHA256='a' * 64,
                    restore_security_assets=restore_assets)
            if name == 'tempfile':
                return fake_temp
            if name == 'time':
                return SimpleNamespace(sleep=lambda seconds: None)
            return real_import(name, *args, **kwargs)

        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and
                    n.name in ('installCustomOLSBinaries', 'verifyChecksum', 'checkGlibcCompat', 'copyOLSBackup', 'rollbackOLSBinary')]
        namespace = dict(os=fake_os, re=__import__('re'), tempfile=fake_temp, shutil=SimpleNamespace(copy2=self.copy2,
                                               move=lambda src, dst: shutil.move(self.path(src), self.path(dst))),
                         subprocess=SimpleNamespace(run=self.run, PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL),
                         time=SimpleNamespace(sleep=lambda seconds: None), logging=mock.Mock(),
                         OLSUpgradeFailure=RuntimeError,
                         load_ols_diagnostic_helper=lambda name: SimpleNamespace(
                             validate=lambda binary: self.run([binary, '-t']), OLSService=FixtureService,
                             original_record=lambda path: None, bundle_records=lambda *args: ({}, {}),
                             verify_originals=lambda *args: None, verify_installed=lambda *args: None, recovery_hint=lambda *args: ''),
                         load_ols_security_assets=lambda: imports('plogical.olsSecurityAssets'),
                         open=lambda p, *a, **kw: open(self.path(p), *a, **kw),
                         __builtins__=dict(vars(builtins), __import__=imports))
        helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_ols_configuration']
        exec(compile(ast.fix_missing_locations(ast.Module(body=helpers + [cls], type_ignores=[])),
                     str(source), 'exec'), namespace)
        target_class = namespace[class_name]
        target_class.stdOut = staticmethod(mock.Mock())
        target = target_class() if class_name == 'InstallCyberPanel' else target_class
        target.detectArchitecture = lambda: True
        target.detectPlatform = lambda: 'ubuntu'

        def download(url, destination):
            kind = self.by_url[url]
            self.downloads.append(kind)
            if self.failure == 'missing-assets' and kind == 'assets':
                return False
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

    def copy2(self, source, destination, **kwargs):
        if self.failure == 'partial-restore' and str(source).endswith('mod_security.so.backup') and str(destination).endswith('.restore'):
            raise OSError('injected WAF restoration failure')
        if self.failure == 'backup' and str(destination).endswith('mod_security.so.backup'):
            raise OSError('injected backup failure')
        return shutil.copy2(self.path(source), self.path(destination), **kwargs)

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
            self.start_bundles.append(self.bundle())
            data = self.path(self.core).read_bytes()
            self.active = not ((self.failure in ('startup', 'partial-restore') and data == b'new-core') or self.failure == 'rollback-start')
            self.active_bytes = data
            code = 0 if self.active else 1
        elif args[-1] == '-t':
            code = 2 if self.failure == 'config' and self.path(self.core).read_bytes() == b'new-core' else 0
            stdout = '[ERROR] injected candidate configuration failure' if code else ''
        elif args[-1] == '-v':
            if self.failure == 'unexpected-start':
                self.active = True
                self.active_bytes = self.path(self.core).read_bytes()
            if self.failure == 'version-timeout':
                raise subprocess.TimeoutExpired(args, 10)
            stdout = 'OpenLiteSpeed/2.5.5'
        else:
            raise AssertionError('Unexpected command: ' + repr(args))
        return SimpleNamespace(returncode=code, stdout=stdout, stderr='')

    def bundle(self):
        return {p: self.path(p).read_bytes() for p in (self.core, self.module, self.waf, self.admin)
                if self.path(p).exists()}


class BundleTransactionTests(unittest.TestCase):
    def test_upgrade_candidate_invalid_config_restores_before_start(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade', failure='config')
            self.assertFalse(fixture.call())
            self.assertEqual(fixture.bundle(), fixture.old)
            self.assertTrue(fixture.active)
            self.assertEqual(fixture.start_bundles, [fixture.old])

    consumers = [('install/installCyberPanel.py', 'InstallCyberPanel'),
                 ('plogical/upgrade.py', 'Upgrade')]

    def test_required_download_integrity_and_abi_failures_do_not_touch_bundle_or_service(self):
        for source, cls in self.consumers:
            for failure in ('corrupt-waf', 'missing-module', 'missing-waf', 'waf-abi', 'missing-assets', 'asset-validation'):
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
            for module in (False, True):
                with self.subTest(consumer=cls, existing_module=module), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, 'startup', module=module, waf=False)
                    self.assertFalse(f.call())
                    self.assertEqual(f.start_bundles[0][f.waf], b'new-waf')
                    self.assertNotIn(f.waf, f.start_bundles[-1])
                    self.assertEqual(f.bundle(), f.old)
                    self.assertTrue(f.active)
                    self.assertEqual(f.active_bytes, b'old-core')

    def test_write_and_version_failures_restore_bundle_and_service(self):
        for source, cls in self.consumers:
            for failure in ('module-write', 'version-timeout', 'asset-apply'):
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

    def test_cannot_stop_an_unrequested_live_service_or_roll_back_under_it(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade', 'unexpected-start')
            f.active = False
            self.assertFalse(f.call())
            self.assertTrue(f.active)
            self.assertEqual(f.path(f.core).read_bytes(), b'new-core')
            self.assertFalse(any(args[-1] in ('stop', 'start') for args in f.commands))

    def test_incomplete_persisted_receipt_is_refused_before_stopping_service(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade')
            backup = f.path('/usr/local/lsws/backup-legacy-test')
            backup.mkdir()
            (backup / 'openlitespeed.backup').write_bytes(b'old-core')
            self.assertFalse(f.rollback(str(backup), f.core, f.module))
            self.assertTrue(f.active)
            self.assertFalse(any(args[-1] in ('stop', 'start') for args in f.commands))

    def test_partial_restore_never_restarts_the_old_core(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade', 'partial-restore')
            self.assertFalse(f.call())
            self.assertFalse(f.active)
            self.assertEqual(len(f.start_bundles), 1)
            self.assertNotEqual(f.bundle(), f.old)

    def test_persisted_rollback_of_stopped_install_remains_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade')
            f.active = False
            self.assertTrue(f.call())
            backup = next(f.path('/usr/local/lsws').glob('backup-*'))
            self.assertTrue(f.rollback(str(backup), f.core, f.module))
            self.assertFalse(f.active)
            self.assertEqual(f.start_bundles, [])
            self.assertEqual(f.bundle(), f.old)

    def test_upgrade_rollback_preserves_package_owned_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade', 'startup')
            path = f.path(f.module)
            old_name = path.name + '.vendor'
            path.rename(path.with_name(old_name))
            path.symlink_to(old_name)
            self.assertFalse(f.call())
            self.assertEqual(os.readlink(path), old_name)
            self.assertEqual(f.bundle(), f.old)
            self.assertTrue(f.active)

    def test_persisted_rollback_restores_assets_and_reports_restart_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade')
            self.assertTrue(f.call())
            backup = next(f.path('/usr/local/lsws').glob('backup-*'))
            self.assertTrue((backup / 'security_assets_backup.json').is_file())
            f.failure = 'rollback-start'
            self.assertFalse(f.rollback(str(backup), f.core, f.module))
            self.assertEqual(f.bundle(), f.old)
            self.assertFalse(f.active)

    def test_persisted_rollback_does_not_replace_files_if_stop_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            f = BundleFixture(directory, ROOT / 'plogical/upgrade.py', 'Upgrade')
            self.assertTrue(f.call())
            installed = f.bundle()
            backup = next(f.path('/usr/local/lsws').glob('backup-*'))
            f.failure = 'stop'
            self.assertFalse(f.rollback(str(backup), f.core, f.module))
            self.assertEqual(f.bundle(), installed)
            self.assertTrue(f.active)

    def test_success_installs_the_complete_required_bundle(self):
        for source, cls in self.consumers:
            for waf in (False, True):
                with self.subTest(consumer=cls, existing_waf=waf), tempfile.TemporaryDirectory() as directory:
                    f = BundleFixture(directory, ROOT / source, cls, waf=waf)
                    self.assertTrue(f.call())
                    if cls == 'InstallCyberPanel':
                        cleanup = load_method(ROOT / 'install/install.py',
                                              'preFlightsChecks', 'modSecPreReqs')
                        cleanup.__globals__['is_el10_release'] = lambda: False
                        cleanup(SimpleNamespace(server_root_path=str(f.path('/usr/local/lsws'))))
                    expected = {f.core: b'new-core', f.module: b'new-module', f.waf: b'new-waf', f.admin: b'new-admin'}
                    self.assertIn('modsec', f.downloads)
                    self.assertEqual(f.bundle(), expected)
                    self.assertTrue(f.active)
                    self.assertEqual(f.active_bytes, b'new-core')


if __name__ == '__main__':
    unittest.main()
