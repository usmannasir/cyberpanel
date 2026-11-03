"""Opt-in test of the public upgrade's OLS stage with a real isolated daemon.

CP_OLS_NATIVE_SERVICE_ROOT, STAGE, CONTROLLER and IMAGE select the old
2.5.6 fixture, pinned release artifacts, vendor controller and Docker image.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'CP_OLS_NATIVE_SERVICE_'


def checksum(path):
    with path.open('rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def snapshot(path):
    if not os.path.lexists(str(path)):
        return None
    info = path.lstat()
    content = os.readlink(str(path)) if path.is_symlink() else checksum(path)
    return info.st_mode, info.st_uid, info.st_gid, content


def request(query=''):
    for _ in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18088/' + query, timeout=3) as reply:
                return reply.status, reply.read()
        except urllib.error.HTTPError as error:
            return error.code, None
        except OSError:
            time.sleep(0.25)
    raise RuntimeError('Native QA site did not respond')


def prepare():
    root = Path('/usr/local/lsws')
    subprocess.run(['cp', '-a', '/fixture/.', str(root)], check=True)
    for name in ('lswsctrl.open', 'lsws_env'):
        shutil.copy2('/controller/' + name, str(root / 'bin' / name))
    (root / 'bin/lswsctrl').symlink_to('lswsctrl.open')
    for name in ('Example/html', 'share/autoindex', 'admin/tmp', 'tmp'):
        (root / name).mkdir(parents=True, exist_ok=True)
    subprocess.run(['groupadd', '-f', 'lsadm'], check=True)
    if subprocess.run(['id', 'lsadm'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        subprocess.run(['useradd', '-g', 'lsadm', 'lsadm'], check=True)
    (root / 'Example/html/index.html').write_text('public OLS fixture\n')
    admin = root / 'admin/conf/admin_config.conf'
    # Start with an old core and valid old-generation config.
    removed = ('throttleenabled', 'throttlemaxfailures', 'throttleblockwindow', 'throttlemaxbackoff',
               'loginhistoryretention', 'opsauditretainfiles', 'configautobackupretention')
    admin.write_text(''.join(line for line in admin.read_text().splitlines(True)
                             if not line.lstrip().lower().startswith(removed)))
    installed = Path('/usr/local/CyberCP/CyberCP')
    installed.mkdir(parents=True, exist_ok=True)
    (installed / '__init__.py').touch()
    (installed / 'settings.py').touch()
    Path('/home/cyberpanel').mkdir(parents=True, exist_ok=True)
    stage = Path('/tmp/staged-consumer')
    stage.mkdir()
    for name in ('upgrade', 'olsSecurityAssets', 'olsParserRecovery', 'olsStockClassifier',
                 'olsNativeValidation', 'olsServiceControl'):
        shutil.copy2('/src/plogical/' + name + '.py', str(stage))
    for name in ('cyberpanel_firewall_migration.py', 'cyberpanel_version.py', 'lscpd_binary.py'):
        shutil.copy2('/src/' + name, str(stage))
    (stage / 'MySQLdb.py').touch()
    os.chdir(str(stage))
    sys.path.insert(0, str(stage))
    os.environ['LSWS_HOME'] = str(root) + '/'
    return root


def transport(url, destination):
    name = url.rsplit('/', 1)[-1]
    files = {'openlitespeed-': 'openlitespeed', 'cyberpanel_ols-': 'cyberpanel_ols.so',
             'mod_security-': 'mod_security.so'}
    artifact = next((value for key, value in files.items() if name.startswith(key)), None)
    if artifact is None and name.endswith('.tar.gz'):
        artifact = 'security-assets.tar.gz'
    assert artifact, name
    shutil.copyfile(str(Path('/release') / artifact), destination)
    return True


def guest(mode):
    root = prepare()
    import upgrade
    from olsServiceControl import OLSService
    service = OLSService()
    expected_core = checksum(Path('/release/openlitespeed'))
    assert checksum(root / 'bin/openlitespeed') != expected_core
    with tarfile.open('/release/security-assets.tar.gz') as archive:
        paths = {entry['path'] for entry in json.load(archive.extractfile('manifest.json'))['files']}
    configs = ('conf/httpd_config.conf', 'admin/conf/admin_config.conf')
    paths.update(configs + ('bin/openlitespeed', 'modules/cyberpanel_ols.so', 'modules/mod_security.so'))
    original = {p: snapshot(root / p) for p in paths}
    running = mode != 'stopped'
    if running:
        subprocess.run([str(root / 'bin/lswsctrl'), 'start'], check=True)
        assert service.state() and request() == (200, b'public OLS fixture\n')
        assert request('?test=attack')[0] == 403
    else:
        assert service.state() is None

    class NextStage(BaseException):
        pass

    def next_stage():
        raise NextStage()
    upgrade.Upgrade.downloadCustomBinary = staticmethod(transport)
    upgrade.Upgrade.updateRepoURL = staticmethod(next_stage)
    injected = []
    if mode == 'rollback':
        original_loader = upgrade.load_ols_diagnostic_helper

        def load(filename):
            module = original_loader(filename)
            if filename == 'olsServiceControl.py':
                actual_change = module.OLSService.change

                def change(self, action, previous_state):
                    state = actual_change(self, action, previous_state)
                    if action == 'start' and not injected and checksum(root / 'bin/openlitespeed') == expected_core:
                        injected.append(True)
                        raise RuntimeError('injected verification failure after real candidate start')
                    return state
                module.OLSService.change = change
            return module
        upgrade.load_ols_diagnostic_helper = load

    success = False
    try:
        upgrade.Upgrade.upgrade('SoftUpgrade,v3.0.8')
    except NextStage:
        success = True
    except upgrade.OLSUpgradeFailure:
        pass
    assert success == (mode != 'rollback')
    if success:
        assert checksum(root / 'bin/openlitespeed') == expected_core
    else:
        assert injected and all(snapshot(root / p) == content for p, content in original.items())
    if running:
        assert service.state() and request() == (200, b'public OLS fixture\n')
        assert request('?test=attack')[0] == 403
    else:
        assert service.state() is None
    assert all(snapshot(root / p) == original[p] for p in configs)
    print('NATIVE_OLS_TRANSACTION_' + mode.upper() + '=PASS')


@unittest.skipUnless(all(os.environ.get(PREFIX + key) for key in ('ROOT', 'STAGE', 'CONTROLLER', 'IMAGE')),
                     'requires native service fixture, artifacts, controller and runtime image')
class NativeServiceTests(unittest.TestCase):
    def test_public_ols_upgrade_stage(self):
        for mode in os.environ.get(PREFIX + 'MODES', 'running,stopped,rollback').split(','):
            self.assertIn(mode, ('running', 'stopped', 'rollback'))
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=os.environ.get('CP_OLS_NATIVE_SCRATCH_BASE')) as scratch:
                command = ['docker', 'run', '--rm', '--init', '--privileged', '--cgroupns=private', '--network', 'none',
                           '--tmpfs', '/usr/local/lsws:exec', '--tmpfs', '/tmp:exec', '-v', '%s:/src:ro' % ROOT,
                           '-v', '%s:/var/tmp' % scratch]
                for key, target in [('ROOT', 'fixture'), ('STAGE', 'release'), ('CONTROLLER', 'controller')]:
                    command.extend(['-v', '%s:/%s:ro' % (Path(os.environ[PREFIX + key]).resolve(), target)])
                command.extend(['--entrypoint', 'python3', os.environ[PREFIX + 'IMAGE'], '-B',
                                '/src/install/test_ols_native_service_transaction.py', '--guest', mode])
                result = subprocess.run(command, capture_output=True, text=True, timeout=220)
                self.assertEqual(0, result.returncode, result.stdout[-4200:] + result.stderr[-2600:])
                self.assertIn('NATIVE_OLS_TRANSACTION_' + mode.upper() + '=PASS', result.stdout)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--guest':
        guest(sys.argv[2])
    else:
        unittest.main()
