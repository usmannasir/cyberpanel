"""The panel's web worker is built so background jobs can run between requests."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'install'))
import lswsgi_idle_lock  # noqa: E402

SOURCE_21 = '''#include "wsgi.h"

int main ( int argc, char *argv[] )
{
    int ret;
    wsgiInit();

    PyObject *app = NULL;
    PyGILState_STATE gstate;
    if (moduleName)
    {
        app = preload_module(moduleName, appName, progName);
        if (app)
        {
            gstate = PyGILState_Ensure();
        }
    }
    LSAPI_Init();
#if 1
    while ( LSAPI_Prefork_Accept_r ( &g_req ) >= 0 )
#else
    while ( LSAPI_Accept_r( &req ) >= 0 )
#endif
    {
        ret = wsgiAppHandler(&g_req, app);
    }
    return 0;
}
'''
SOURCE_22 = SOURCE_21.replace('    int ret;\n', '    int ret = 0;\n    int gil_held = 0;\n')


class SourceEditTests(unittest.TestCase):
    def test_lock_is_released_only_for_the_wait(self):
        for source, condition in ((SOURCE_21, 'app != NULL'), (SOURCE_22, 'gil_held')):
            result = lswsgi_idle_lock.patched(source)
            self.assertIn('    while ( wsgi_wait_for_request( %s ) >= 0 )\n' % condition, result)
            self.assertNotIn(lswsgi_idle_lock.WAIT, result)
            helper = result[result.index('static int wsgi_wait_for_request'):result.index('int main (')]
            self.assertLess(helper.index('PyEval_SaveThread()'), helper.index('LSAPI_Prefork_Accept_r(&g_req)'))
            self.assertLess(helper.index('LSAPI_Prefork_Accept_r(&g_req)'), helper.index('PyEval_RestoreThread(waiting)'))
            self.assertEqual(result, lswsgi_idle_lock.patched(result))

    def test_unexpected_source_is_refused(self):
        for source in ('', SOURCE_21.replace('&g_req ) >= 0', '&g_req ) > 0'),
                       SOURCE_21.replace('int main ( int argc', 'int main(int argc'),
                       SOURCE_21 + lswsgi_idle_lock.WAIT, SOURCE_21.replace('PyObject *app = NULL;', '')):
            with self.assertRaises(ValueError):
                lswsgi_idle_lock.patched(source)

    def test_file_is_edited_once_and_left_alone_when_unexpected(self):
        with tempfile.TemporaryDirectory() as directory:
            good, bad = Path(directory, 'main.c'), Path(directory, 'other.c')
            good.write_text(SOURCE_21)
            bad.write_text('int main(void) { return 0; }\n')
            script = str(ROOT / 'install' / 'lswsgi_idle_lock.py')
            self.assertEqual(0, subprocess.call([sys.executable, '-I', script, str(good)]))
            first = good.read_text()
            self.assertIn('wsgi_wait_for_request', first)
            self.assertEqual(0, subprocess.call([sys.executable, '-I', script, str(good)]))
            self.assertEqual(first, good.read_text())
            self.assertEqual(1, subprocess.call([sys.executable, '-I', script, str(bad)]))
            self.assertEqual('int main(void) { return 0; }\n', bad.read_text())
            self.assertEqual(1, subprocess.call([sys.executable, '-I', script, str(Path(directory, 'missing.c'))]))


class BuildSiteTests(unittest.TestCase):
    def between(self, text, start, edit, end):
        self.assertEqual(1, text.count(edit), edit)
        self.assertLess(text.index(start), text.index(edit))
        self.assertLess(text.index(edit), text.index(end, text.index(start)))

    def test_installer_upgrader_and_repair_script_edit_before_building(self):
        installer = (ROOT / 'install' / 'install.py').read_text()
        self.between(installer, 'os.chdir("wsgi-lsapi-2.1")', "lswsgi_idle_lock.apply('main.c')", 'command = "make"')
        upgrader = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        self.between(upgrader, 'cd wsgi-lsapi-2.1 || exit 1',
                     '"$runtime_python" -I /usr/local/CyberCP/install/lswsgi_idle_lock.py main.c',
                     'Run_Upgrade_Command make || exit 1')
        repair = (ROOT / 'fix_cyberpanel_install.sh').read_text()
        self.between(repair, '    cd wsgi-lsapi-2.1\n',
                     '/usr/local/CyberCP/bin/python -I /usr/local/CyberCP/install/lswsgi_idle_lock.py main.c',
                     '    make\n')

    def test_a_failed_edit_does_not_stop_the_build(self):
        upgrader = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        edit = upgrader.index('lswsgi_idle_lock.py main.c')
        self.assertNotIn('exit 1', upgrader[edit:upgrader.index('Run_Upgrade_Command env -u PYTHONHOME', edit)])


if __name__ == '__main__':
    unittest.main()
