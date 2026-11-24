"""The upgrader names the steps that did not complete, keeps phpMyAdmin through a GitHub outage,
and brings the panel's runtime up to the release in an upgrade started from the panel page."""
import ast
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'plogical' / 'upgrade.py').read_text()


def upgrader_class():
    return next(node for node in ast.parse(SOURCE).body
                if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')


def methods(*names):
    """The named methods of Upgrade as plain functions on a stand-in class."""
    found = [node for node in upgrader_class().body if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in found:
        node.decorator_list = [ast.Name(id='staticmethod', ctx=ast.Load())]
    stand_in = ast.ClassDef(name='Upgrade', bases=[], keywords=[], body=found, decorator_list=[])
    return ast.fix_missing_locations(ast.Module(body=[stand_in], type_ignores=[]))


def method_text(name):
    members = upgrader_class().body
    index = next(i for i, node in enumerate(members) if isinstance(node, ast.FunctionDef) and node.name == name)
    lines = SOURCE.splitlines()
    end = members[index + 1].lineno - 1 if index + 1 < len(members) else len(lines)
    return '\n'.join(lines[members[index].lineno - 1:end])


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.base))
        self.said = []
        namespace = {'os': os, 'json': json, 'shlex': shlex, 'shutil': shutil, 'tempfile': tempfile,
                     'subprocess': subprocess}
        exec(compile(methods('warn', 'reportIncomplete', 'unpackPhpMyAdmin', 'executioner_silent'),
                     'upgrade.py', 'exec'), namespace)
        self.Upgrade = namespace['Upgrade']
        self.Upgrade.Incomplete = []
        self.Upgrade.stdOut = staticmethod(lambda message, do_exit=0: self.said.append(message))


class CompletionReportTests(Fixture):
    def test_steps_that_did_not_complete_are_named_at_the_end_and_for_the_launcher(self):
        report = self.base / 'report.json'
        os.environ['CYBERPANEL_UPGRADE_REPORT'] = str(report)
        self.addCleanup(os.environ.pop, 'CYBERPANEL_UPGRADE_REPORT', None)
        self.Upgrade.warn('The panel web worker was not rebuilt; the installed one stays in use: no network')
        self.assertEqual('WARNING: The panel web worker was not rebuilt; the installed one stays in use: '
                         'no network', self.said[-1])
        self.Upgrade.reportIncomplete()
        self.assertEqual('The upgrade finished, but 1 step(s) did not complete:\n- The panel web worker was '
                         'not rebuilt; the installed one stays in use: no network', self.said[-1])
        self.assertEqual({'incomplete': ['The panel web worker was not rebuilt; the installed one stays in '
                                         'use: no network']}, json.loads(report.read_text()))
        self.assertEqual(0o600, report.stat().st_mode & 0o777)

    def test_a_clean_run_says_so_and_an_older_launcher_gets_no_file(self):
        os.environ.pop('CYBERPANEL_UPGRADE_REPORT', None)
        self.Upgrade.reportIncomplete()
        self.assertEqual('The upgrade finished and every step completed.', self.said[-1])
        self.assertEqual([], os.listdir(str(self.base)))

    def test_the_report_is_the_upgrades_last_step(self):
        body = method_text('upgrade')
        last = body.rindex('Upgrade.reportIncomplete()')
        self.assertLess(body.rindex('requireCSFMigration()'), last)
        # Only the next method's decorator follows.
        self.assertEqual(['Upgrade.reportIncomplete()', '@staticmethod'], body[last:].split())

    def test_failures_of_optional_steps_are_reported_not_only_logged(self):
        for step in ('The panel web worker was not rebuilt', 'The automatic update timer was not refreshed',
                     'OpenLiteSpeed package protection was not applied', 'The Dovecot MySQL driver check did not run',
                     'The phpMyAdmin setup did not complete', 'The panel server binary was not replaced'):
            with self.subTest(step):
                self.assertIn("Upgrade.warn('" + step, SOURCE)
        self.assertNotIn("Upgrade.stdOut('WARNING: The panel web worker", SOURCE)


class PhpMyAdminTests(Fixture):
    def setUp(self):
        super().setUp()
        self.public = self.base / 'public'
        (self.public / 'phpmyadmin').mkdir(parents=True)
        (self.public / 'phpmyadmin' / 'index.php').write_text('installed copy')
        self.archive = self.base / 'phpmyadmin.zip'

    def release_archive(self, name='phpMyAdmin-5.2.1-all-languages'):
        with zipfile.ZipFile(str(self.archive), 'w') as archive:
            archive.writestr(name + '/config.sample.inc.php', '<?php\n')
            archive.writestr(name + '/index.php', 'release copy')

    def unpack(self, url='http://127.0.0.1:9/unreachable.zip'):
        self.Upgrade.unpackPhpMyAdmin(str(self.public), archive=str(self.archive), url=url)

    def test_the_release_archive_replaces_the_installed_copy_without_a_download(self):
        if not shutil.which('unzip'):
            self.skipTest('unzip is not installed')
        self.release_archive()
        self.unpack(url='http://127.0.0.1:9/must-not-be-asked.zip')
        self.assertEqual('release copy', (self.public / 'phpmyadmin' / 'index.php').read_text())
        self.assertEqual(['phpmyadmin'], os.listdir(str(self.public)))

    def test_an_unusable_archive_and_an_unreachable_github_keep_the_installed_copy(self):
        self.archive.write_text('not a zip')
        with self.assertRaisesRegex(RuntimeError, 'could not be unpacked'):
            self.unpack()
        self.archive.unlink()
        with self.assertRaisesRegex(RuntimeError, 'could not be downloaded'):
            self.unpack()
        if shutil.which('unzip'):
            self.release_archive(name='something-else')
            with self.assertRaisesRegex(RuntimeError, 'does not hold one phpMyAdmin release'):
                self.unpack()
        self.assertEqual('installed copy', (self.public / 'phpmyadmin' / 'index.php').read_text())
        self.assertEqual(['phpmyadmin'], os.listdir(str(self.public)))

    def test_the_installed_copy_is_no_longer_deleted_before_the_new_one_exists(self):
        body = method_text('download_install_phpmyadmin')
        self.assertNotIn('shutil.rmtree("/usr/local/CyberCP/public/phpmyadmin")', body)
        self.assertNotIn('raw/stable/phpmyadmin.zip', body)
        self.assertIn("Upgrade.unpackPhpMyAdmin('/usr/local/CyberCP/public')", body)


class PanelRuntimeWiringTests(unittest.TestCase):
    def test_requirements_are_installed_after_the_new_source_and_before_the_migrations(self):
        body = method_text('upgrade')
        step = body.index('requirements = install_requirements(log=Upgrade.stdOut)')
        self.assertLess(body.index('Upgrade.downloadAndUpgrade('), step)
        self.assertLess(step, body.index('Upgrade.mailServerMigrations()'))
        self.assertIn('if Upgrade.SoftUpgrade:\n            from plogical.panelRuntime import install_requirements',
                      body)

    def test_the_panel_server_binary_is_installed_in_an_upgrade_from_the_panel(self):
        body = method_text('installLSCPD')
        soft = body.index('if Upgrade.SoftUpgrade:')
        self.assertLess(soft, body.index('if Upgrade.SoftUpgrade == 0:'))
        self.assertIn('install_panel_server(select_lscpd_binary(), install_binary_atomically)', body)

    def test_git_gives_up_on_a_stalled_github_transfer(self):
        body = method_text('upgrade')
        self.assertLess(body.index("os.environ.setdefault('GIT_HTTP_LOW_SPEED_TIME', '60')"),
                        body.index('Upgrade.downloadAndUpgrade('))


if __name__ == '__main__':
    unittest.main()
