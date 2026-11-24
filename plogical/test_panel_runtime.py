"""An upgrade from the panel page installs the release's requirements and panel server binary."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import panelRuntime  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.base))

    def write(self, name, text):
        path = self.base / name
        path.write_text(text)
        return path


class RequirementsFileTests(Fixture):
    def test_the_file_is_the_one_the_command_line_upgrade_installs(self):
        for version, name in (('22.04', 'requirments.txt'), ('24.04', 'requirments.txt'),
                              ('26.04', 'requirments.txt'), ('9.4', 'requirments.txt'),
                              ('10.0', 'requirments.txt'), ('8.10', 'requirments-old.txt'),
                              ('20.04', 'requirments-old.txt'), ('12', 'requirments-old.txt')):
            release = self.write('os-release', 'NAME="X"\nVERSION_ID="%s"\nID=x\n' % version)
            with self.subTest(version):
                self.assertEqual(name, panelRuntime.requirements_name(str(release)))


class RequirementsCheckTests(Fixture):
    """Run with this interpreter, which has pip installed and no package named below."""

    def unmet(self, text):
        return panelRuntime.unmet_requirements(str(self.write('requirements.txt', text)), sys.executable)

    def test_installed_versions_are_compared_with_the_release(self):
        import pip
        have = pip.__version__
        self.assertEqual([], self.unmet('# comment\n\npip==%s\nPIP>=1  # case and comment\n' % have))
        self.assertEqual(['pip==0.0.1'], self.unmet('pip==0.0.1\n'))
        self.assertEqual(['cyberpanel-surely-absent==1.0', 'cyberpanel_surely_absent2'],
                         self.unmet('cyberpanel-surely-absent==1.0\ncyberpanel_surely_absent2\npip\n'))

    def test_a_line_for_another_python_is_left_out(self):
        try:
            import packaging.markers  # noqa: F401
        except ImportError:
            self.skipTest('packaging is not installed')
        self.assertEqual([], self.unmet('cyberpanel-surely-absent==1.0; python_version < "3"\n'))

    def test_a_check_that_cannot_run_is_an_error_not_an_empty_list(self):
        with self.assertRaisesRegex(RuntimeError, 'could not be checked'):
            panelRuntime.unmet_requirements(str(self.base / 'missing.txt'), sys.executable)


class InstallRequirementsTests(Fixture):
    def setUp(self):
        super().setUp()
        self.write('requirments.txt', 'Django==4.2.14\n')
        self.calls = []

    def install(self, answers, returncode=0):
        def run(command, **options):
            self.calls.append(command)
            return subprocess.CompletedProcess(command, returncode)
        with mock.patch.object(panelRuntime, 'unmet_requirements', side_effect=answers):
            return panelRuntime.install_requirements(root=str(self.base), python='/py', name='requirments.txt',
                                                     log=lambda text: None, run=run)

    def test_nothing_is_installed_when_the_panel_already_has_everything(self):
        self.assertEqual({'state': 'current', 'file': 'requirments.txt'}, self.install([[]]))
        self.assertEqual([], self.calls)

    def test_what_is_missing_is_installed_with_pip(self):
        result = self.install([['Django==4.2.14'], []])
        self.assertEqual('installed', result['state'])
        self.assertEqual(['Django==4.2.14'], result['installed'])
        self.assertEqual([], result['unconfirmed'])
        self.assertEqual(['/py', '-m', 'pip', 'install'], self.calls[0][:4])
        self.assertEqual(str(self.base / 'requirments.txt'), self.calls[0][-1])

    def test_a_pip_failure_ends_the_upgrade(self):
        with self.assertRaisesRegex(RuntimeError, 'pip ended with status 1 while installing Django==4.2.14'):
            self.install([['Django==4.2.14']], returncode=1)

    def test_pip_decides_when_the_check_still_disagrees(self):
        self.assertEqual(['Django==4.2.14'], self.install([['Django==4.2.14'], ['Django==4.2.14']])['unconfirmed'])

    def test_a_release_without_its_requirements_file_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, 'the release has no requirments-old.txt'):
            panelRuntime.install_requirements(root=str(self.base), name='requirments-old.txt')


class PanelServerTests(Fixture):
    def setUp(self):
        super().setUp()
        self.write('lscpd.0.4.0', 'new binary')
        self.server = self.base / 'bin' / 'lscpd'
        self.server.parent.mkdir()
        self.server.write_text('old binary')
        self.events = []

    def copy(self, source, destination):
        self.events.append(('install', Path(source).name, Path(destination).name))
        shutil.copyfile(source, destination)

    def switch(self, ready=None):
        return panelRuntime.install_panel_server(
            'lscpd.0.4.0', self.copy, root=str(self.base), server=str(self.server),
            restart=lambda: self.events.append(('restart', self.server.read_text())),
            ready=ready or (lambda: self.events.append(('ready', self.server.read_text()))))

    def test_a_server_on_the_releases_binary_is_left_alone(self):
        self.server.write_text('new binary')
        self.assertEqual({'state': 'current', 'binary': 'lscpd.0.4.0'}, self.switch())
        self.assertEqual([], self.events)

    def test_another_binary_is_replaced_and_the_panel_restarted_on_it(self):
        result = self.switch()
        self.assertEqual('replaced', result['state'])
        self.assertEqual('new binary', self.server.read_text())
        self.assertEqual([('install', 'lscpd', '.lscpd.previous'), ('install', 'lscpd.0.4.0', 'lscpd'),
                          ('restart', 'new binary'), ('ready', 'new binary')], self.events)
        self.assertEqual(['lscpd'], os.listdir(str(self.server.parent)))

    def test_a_panel_that_does_not_answer_gets_the_previous_binary_back(self):
        answers = iter([RuntimeError('no login page'), None])

        def ready():
            answer = next(answers)
            if answer:
                raise answer
        with self.assertRaisesRegex(RuntimeError, r'did not start on lscpd.0.4.0 \(no login page\); '
                                                  'the previous binary was put back'):
            self.switch(ready)
        self.assertEqual('old binary', self.server.read_text())
        self.assertEqual(['lscpd'], os.listdir(str(self.server.parent)))
        self.assertEqual(('restart', 'old binary'), self.events[-1])

    def test_a_panel_that_starts_on_neither_binary_is_reported(self):
        def ready():
            raise RuntimeError('down')
        with self.assertRaisesRegex(RuntimeError, 'nor on the previous binary'):
            self.switch(ready)
        self.assertEqual('old binary', self.server.read_text())


class WaitTests(unittest.TestCase):
    def test_the_panel_is_asked_until_it_answers_or_the_time_is_up(self):
        now = [0]
        answers = iter([OSError('refused'), OSError('refused'), {'http_status': 200}])

        def probe():
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer
        sleep = lambda seconds: now.__setitem__(0, now[0] + seconds)  # noqa: E731
        self.assertEqual({'http_status': 200}, panelRuntime.wait_for_panel(probe, 90, lambda: now[0], sleep))

        def down():
            raise OSError('refused')
        with self.assertRaisesRegex(RuntimeError, 'the panel did not answer: refused'):
            panelRuntime.wait_for_panel(down, 5, lambda: now[0], sleep)


if __name__ == '__main__':
    unittest.main()
