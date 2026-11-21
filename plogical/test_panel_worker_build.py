"""An upgrade started from the panel rebuilds the web worker without risking the installed one."""
import hashlib
import io
import os
import stat
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import panelWorkerBuild  # noqa: E402

MAIN = '''int main ( int argc, char *argv[] )
{
    PyObject *app = NULL;
    while ( LSAPI_Prefork_Accept_r ( &g_req ) >= 0 )
    {
    }
    return 0;
}
'''
# Stands in for make: records what it was given and writes the "worker".
MAKE = '''#!/bin/sh
cp main.c "$RECEIPT.main"
env > "$RECEIPT.env"
[ -z "$FAIL_BUILD" ] || { echo 'compiler stopped'; exit 2; }
printf '#!/bin/sh\\necho "%s"\\nexit 1\\n' "${WORKER_SAYS-lswsgi version 2.1.0}" > lswsgi
chmod 755 lswsgi
'''


def archive(entries):
    """entries: name -> text, or name -> a prepared TarInfo."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as output:
        for name, value in entries.items():
            if isinstance(value, tarfile.TarInfo):
                output.addfile(value)
                continue
            data = value.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            output.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def source(main=MAIN):
    return archive({'wsgi-lsapi-2.1/main.c': main, 'wsgi-lsapi-2.1/configure.py': 'print("Done.")\n'})


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.bin = base / 'bin'
        self.bin.mkdir()
        self.worker = self.bin / 'lswsgi'
        self.worker.write_text('installed worker\n')
        self.worker.chmod(0o755)
        tools = base / 'tools'
        tools.mkdir()
        (tools / 'make').write_text(MAKE)
        (tools / 'make').chmod(0o755)
        self.receipt = base / 'receipt'
        environment = {'PATH': '%s:%s' % (tools, os.environ['PATH']), 'RECEIPT': str(self.receipt),
                       'PYTHONHOME': '/usr', 'PYTHONPATH': '/nowhere'}
        patcher = mock.patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)

    def rebuild(self, content=None):
        return panelWorkerBuild.rebuild(
            python=sys.executable, worker=str(self.worker),
            edit=str(ROOT / 'install' / 'lswsgi_idle_lock.py'),
            fetch=lambda: source() if content is None else content)

    def assert_untouched(self):
        self.assertEqual('installed worker\n', self.worker.read_text())
        self.assertEqual(['lswsgi'], os.listdir(str(self.bin)))

    def test_worker_is_replaced_by_a_build_of_the_edited_source(self):
        if os.geteuid() == 0:
            os.chown(str(self.worker), 12345, 12346)
        result = self.rebuild()
        self.assertIn('lswsgi version 2.1.0', self.worker.read_text())
        self.assertEqual(['lswsgi'], os.listdir(str(self.bin)))
        info = self.worker.stat()
        self.assertEqual(0o755, stat.S_IMODE(info.st_mode))
        if os.geteuid() == 0:
            self.assertEqual((12345, 12346), (info.st_uid, info.st_gid))
        self.assertEqual({'state': 'rebuilt', 'sha256': hashlib.sha256(self.worker.read_bytes()).hexdigest()}, result)
        self.assertIn('wsgi_wait_for_request( app != NULL )', Path(str(self.receipt) + '.main').read_text())
        build_environment = Path(str(self.receipt) + '.env').read_text()
        self.assertNotIn('PYTHONHOME=', build_environment)
        self.assertNotIn('PYTHONPATH=', build_environment)

    def test_a_first_worker_is_installed_where_none_exists(self):
        self.worker.unlink()
        self.rebuild()
        self.assertEqual(0o755, stat.S_IMODE(self.worker.stat().st_mode))

    def test_failed_build_keeps_the_installed_worker(self):
        with mock.patch.dict(os.environ, {'FAIL_BUILD': '1'}):
            with self.assertRaisesRegex(RuntimeError, 'make ended with status 2: compiler stopped'):
                self.rebuild()
        self.assert_untouched()

    def test_unexpected_source_is_not_built(self):
        with self.assertRaisesRegex(RuntimeError, 'not the one this release expects'):
            self.rebuild(source('int main(void) { return 0; }\n'))
        self.assertFalse(Path(str(self.receipt) + '.main').exists())
        self.assert_untouched()

    def test_a_build_that_does_not_start_is_not_installed(self):
        with mock.patch.dict(os.environ, {'WORKER_SAYS': 'error while loading shared libraries'}):
            with self.assertRaisesRegex(RuntimeError, 'did not start'):
                self.rebuild()
        self.assert_untouched()

    def test_failed_download_keeps_the_installed_worker(self):
        def unavailable():
            raise OSError('network is unreachable')
        with self.assertRaises(OSError):
            panelWorkerBuild.rebuild(python=sys.executable, worker=str(self.worker), edit='unused', fetch=unavailable)
        self.assert_untouched()


class SourceArchiveTests(unittest.TestCase):
    def special(self, name, kind, target=''):
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = target
        return info

    def test_only_plain_files_inside_the_source_directory_are_written(self):
        refused = {
            'parent': {'wsgi-lsapi-2.1/../escaped': 'x'},
            'absolute': {'/tmp/cyberpanel-worker-test-escaped': 'x'},
            'other directory': {'elsewhere/main.c': 'x'},
            'symbolic link': {'wsgi-lsapi-2.1/link': self.special('wsgi-lsapi-2.1/link', tarfile.SYMTYPE, '/etc')},
            'hard link': {'wsgi-lsapi-2.1/link': self.special('wsgi-lsapi-2.1/link', tarfile.LNKTYPE, 'wsgi-lsapi-2.1/main.c')},
            'device': {'wsgi-lsapi-2.1/device': self.special('wsgi-lsapi-2.1/device', tarfile.CHRTYPE)},
        }
        for label, entries in refused.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as outer:
                target = Path(outer, 'build')
                target.mkdir()
                with self.assertRaisesRegex(RuntimeError, 'unexpected (path|entry) in the worker source'):
                    panelWorkerBuild.unpack(archive(entries), str(target))
                self.assertEqual(['build'], os.listdir(outer))
                self.assertEqual([], [str(path) for path in target.rglob('*') if not path.is_dir()])
        self.assertFalse(os.path.exists('/tmp/cyberpanel-worker-test-escaped'))

    def test_source_larger_than_expected_is_refused(self):
        with tempfile.TemporaryDirectory() as target:
            with self.assertRaisesRegex(RuntimeError, 'larger than expected'):
                panelWorkerBuild.unpack(source(), target, limit=10)

    def test_plain_source_is_written(self):
        with tempfile.TemporaryDirectory() as target:
            panelWorkerBuild.unpack(source(), target)
            self.assertEqual(MAIN, Path(target, 'wsgi-lsapi-2.1', 'main.c').read_text())


class DownloadTests(unittest.TestCase):
    class Response(io.BytesIO):
        def __init__(self, data, url):
            super().__init__(data)
            self.url = url

        def geturl(self):
            return self.url

    def fetch(self, data, url):
        with mock.patch.object(panelWorkerBuild, 'urlopen', return_value=self.Response(data, url)) as opened:
            try:
                return panelWorkerBuild.download(limit=8)
            finally:
                self.assertEqual(panelWorkerBuild.SOURCE, opened.call_args[0][0].full_url)

    def test_source_is_taken_over_https_within_the_size_limit(self):
        self.assertTrue(panelWorkerBuild.SOURCE.startswith('https://www.litespeedtech.com/'))
        self.assertEqual(b'12345678', self.fetch(b'12345678', panelWorkerBuild.SOURCE))
        with self.assertRaisesRegex(RuntimeError, 'larger than expected'):
            self.fetch(b'123456789', panelWorkerBuild.SOURCE)
        with self.assertRaisesRegex(RuntimeError, 'not served over HTTPS'):
            self.fetch(b'1234', 'http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz')


class UpgraderTests(unittest.TestCase):
    def test_panel_started_upgrade_rebuilds_the_worker_and_survives_a_failure(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        call = 'rebuild_panel_worker()'
        self.assertEqual(1, upgrader.count(call))
        position = upgrader.index(call)
        # The new source, which carries the build helper, is installed first.
        self.assertLess(upgrader.index('Upgrade.downloadAndUpgrade('), position)
        self.assertLess(position, upgrader.index('Upgrade.stdOut("Upgrade Completed.")'))
        block = upgrader[upgrader.rindex('\n        if Upgrade.SoftUpgrade:\n', 0, position):
                         upgrader.index('\n        if Upgrade.SoftUpgrade == 0:\n', position)]
        self.assertIn('            try:\n                from plogical.panelWorkerBuild import rebuild as rebuild_panel_worker\n', block)
        self.assertIn('            except Exception as error:\n                Upgrade.stdOut(\'WARNING: The panel web worker was not rebuilt', block)
        self.assertNotIn('raise', block)

    def test_helper_runs_on_the_oldest_supported_python(self):
        import ast
        ast.parse((ROOT / 'plogical' / 'panelWorkerBuild.py').read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
