"""The folder a WordPress backup works in is the job's alone and does not outlive the job."""
import ast
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import sys
import tempfile
import time
import types
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from plogical import backupStaging
from plogical.backupStaging import (
    folder_size,
    is_job_folder,
    looks_like_backup_staging,
    remove_stale_staging,
    stale_staging_folders,
)
from plogical.test_php_restart_marker import load_methods

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'plogical/applicationInstaller.py').read_text()
DAY = 24 * 60 * 60


class JobFolderTests(unittest.TestCase):
    def test_a_jobs_folder_is_a_32_hex_name_directly_under_the_work_directory(self):
        self.assertTrue(is_job_folder('/usr/local/CyberCP/tmp/' + 'a1' * 16))
        self.assertTrue(is_job_folder('/usr/local/CyberCP/tmp/' + secrets.token_hex(16)))
        self.assertTrue(is_job_folder('/work/' + '0' * 32, '/work/'))

    def test_nothing_else_is_ever_handed_to_the_removal(self):
        name = 'a1' * 16
        for path in (None, '', '/', '/usr/local/CyberCP/tmp', '/usr/local/CyberCP/tmp/', '/usr/local/CyberCP',
                     '/usr/local/CyberCP/tmp/' + name + '/', '/usr/local/CyberCP/tmp/' + name + '/site',
                     '/usr/local/CyberCP/tmp/' + name[:31], '/usr/local/CyberCP/tmp/' + name + 'a',
                     '/usr/local/CyberCP/tmp/' + name.upper(), '/usr/local/CyberCP/tmp/1234',
                     '/usr/local/CyberCP/tmp/../tmp/' + name, '/usr/local/CyberCP/tmp//' + name,
                     '/home/example.com/' + name, 'usr/local/CyberCP/tmp/' + name, name,
                     '/usr/local/CyberCP/tmp/' + name + ' /home', '/usr/local/CyberCP/tmp/' + name + '\n',
                     '/usr/local/CyberCP/tmp/*', 7, ['/usr/local/CyberCP/tmp/' + name]):
            self.assertFalse(is_job_folder(path), repr(path))
        self.assertFalse(is_job_folder('/work/' + name, 'work'))
        self.assertFalse(is_job_folder('/work/' + name, None))


class StaleStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wp-staging-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = os.path.join(self.temp.name, 'tmp')
        os.mkdir(self.root)
        self.now = time.time()
        self.log = []

    def folder(self, name, files=('public_html/index.php',), age=2 * DAY):
        path = os.path.join(self.root, name)
        os.mkdir(path)
        for relative in files:
            target = os.path.join(path, relative)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w') as handle:
                handle.write('x' * 1000)
        os.utime(path, (self.now - age, self.now - age))
        return path

    def test_what_an_earlier_releases_backup_left_is_found(self):
        both = self.folder('a' * 32, ('public_html/wp-config.php', 'public_html/wp-admin/index.php', 'wpdb.sql', '3609'))
        files = self.folder('b' * 32, ('public_html/index.php', '1234'))
        dump = self.folder('c' * 32, ('wpdb.sql', '1234'))
        self.assertEqual([both, files, dump], stale_staging_folders(self.root, self.now))

    def test_a_folder_that_may_belong_to_a_running_job_is_left(self):
        self.folder('a' * 32, age=DAY - 60)
        self.folder('b' * 32, age=0)
        self.assertEqual([], stale_staging_folders(self.root, self.now))
        self.assertEqual([os.path.join(self.root, 'a' * 32)], stale_staging_folders(self.root, self.now + 120))

    def test_only_a_jobs_folder_that_holds_a_backups_content_qualifies(self):
        self.folder('uploads')
        self.folder('A' * 32)
        self.folder('a' * 31)
        self.folder('a' * 33)
        self.folder('1234', ('wpdb.sql',))
        self.folder('d' * 32, ('upload.zip',))
        self.folder('e' * 32, ())
        self.folder('f' * 32, ('site/public_html/index.php', 'site/wpdb.sql'))
        self.folder('0' * 32, ('public_html',))
        self.folder('1' * 32, ('dump.sql/inside',))
        with open(os.path.join(self.root, '2' * 32), 'w') as handle:
            handle.write('a file, not a folder')
        self.assertEqual([], stale_staging_folders(self.root, self.now))

    def test_a_link_is_never_followed_or_taken_for_a_folder(self):
        outside = os.path.join(self.temp.name, 'outside')
        os.makedirs(os.path.join(outside, 'public_html'))
        os.utime(outside, (self.now - 3 * DAY, self.now - 3 * DAY))
        os.symlink(outside, os.path.join(self.root, 'a' * 32))
        linked = self.folder('b' * 32, ())
        os.symlink(os.path.join(outside, 'public_html'), os.path.join(linked, 'public_html'))
        os.symlink('/etc/hostname', os.path.join(linked, 'wpdb.sql'))
        os.utime(linked, (self.now - 2 * DAY, self.now - 2 * DAY))
        self.assertEqual([], stale_staging_folders(self.root, self.now))
        self.assertEqual((0, 0), remove_stale_staging(self.root, self.log.append, self.now))
        self.assertTrue(os.path.isdir(os.path.join(outside, 'public_html')))

    def test_the_stale_folders_are_removed_and_counted_and_everything_else_stays(self):
        self.folder('a' * 32, ('public_html/wp-config.php', 'public_html/wp-content/uploads/pic.jpg', 'wpdb.sql'))
        self.folder('b' * 32, ('wpdb.sql',))
        young = self.folder('c' * 32, age=60)
        other = self.folder('uploads', ('file.txt',))
        self.assertEqual((2, 4000), remove_stale_staging(self.root, self.log.append, self.now))
        self.assertEqual(['c' * 32, 'uploads'], sorted(os.listdir(self.root)))
        self.assertTrue(os.path.isdir(young) and os.path.isdir(other))
        self.assertEqual(['Backup work folders left by earlier releases: 2 removed, 0.0 MB freed.'], self.log)
        # A second run finds nothing more to do.
        self.assertEqual((0, 0), remove_stale_staging(self.root, self.log.append, self.now))

    def test_a_folder_that_cannot_be_removed_is_named_and_does_not_stop_the_rest(self):
        first = self.folder('a' * 32)
        self.folder('b' * 32)

        def remove(path):
            if path == first:
                raise OSError('Device or resource busy')
            backupStaging.shutil.rmtree(path)

        self.assertEqual((1, 1000), remove_stale_staging(self.root, self.log.append, self.now, remove))
        self.assertEqual(['a' * 32], os.listdir(self.root))
        self.assertEqual('WARNING: The backup work folder %s was not removed: Device or resource busy' % first,
                         self.log[0])
        self.assertIn('1 removed', self.log[1])

    def test_a_missing_work_directory_is_nothing_to_do(self):
        self.assertEqual((0, 0), remove_stale_staging(os.path.join(self.root, 'absent'), self.log.append, self.now))
        self.assertEqual(['Backup work folders left by earlier releases: 0 removed, 0.0 MB freed.'], self.log)

    def test_size_counts_files_and_does_not_follow_links(self):
        path = self.folder('a' * 32, ('public_html/a', 'public_html/deep/b', 'wpdb.sql'))
        os.symlink('/etc', os.path.join(path, 'public_html', 'link'))
        self.assertEqual(3000, folder_size(path))
        self.assertTrue(looks_like_backup_staging(path))
        self.assertFalse(looks_like_backup_staging(os.path.join(self.root, 'absent')))


class UpgradeCallTests(unittest.TestCase):
    def test_the_upgrade_removes_them_and_can_not_fail_on_it(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        start = upgrader.index('    def removeStaleBackupStaging():')
        method = upgrader[start:upgrader.index('    @staticmethod', start)]
        self.assertIn('from plogical.backupStaging import remove_stale_staging', method)
        self.assertIn('remove_stale_staging(log=lambda message: Upgrade.stdOut(message, 0))', method)
        self.assertLess(method.index('        try:'), method.index('from plogical.backupStaging'))
        self.assertIn("except Exception as error:\n            Upgrade.stdOut('WARNING: Backup work folders of earlier "
                      "releases were not looked for: ' + str(error), 0)", method)
        self.assertEqual(1, upgrader.count('Upgrade.removeStaleBackupStaging()'))
        self.assertIn('\n        Upgrade.relocateScannerBackups()\n        Upgrade.removeStaleBackupStaging()\n', upgrader)
        # The upgrade script still reads as a program after the step was added.
        ast.parse(upgrader)

    def test_an_upgrade_started_from_the_cloud_platform_runs_it_too(self):
        cloud = (ROOT / 'plogical' / 'CyberPanelUpgrade.py').read_text()
        self.assertEqual(1, cloud.count('Upgrade.removeStaleBackupStaging()'))
        self.assertIn('\n        Upgrade.relocateScannerBackups()\n        Upgrade.removeStaleBackupStaging()\n', cloud)

    def test_the_helper_needs_nothing_of_the_panel(self):
        source = (ROOT / 'plogical' / 'backupStaging.py').read_text()
        self.assertEqual(['import os', 'import re', 'import shutil', 'import time'],
                         [line for line in source.splitlines() if line.startswith(('import ', 'from '))])


class BackupJobTests(unittest.TestCase):
    """WPCreateBackup with the database, the helper and the site replaced: what happens to its work folder."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wp-backup-job-test-')
        self.addCleanup(self.temp.cleanup)
        self.status = os.path.join(self.temp.name, 'status')
        self.commands = []
        self.failing = None
        php_module = types.ModuleType('plogical.phpUtilities')
        php_module.phpUtilities = NS(WrapGetPHPVersionFromFileToGetVersionWithPHP=lambda vhost: 'PHP 8.3')
        manager_module = types.ModuleType('managePHP.phpManager')
        manager_module.PHPManager = NS(getPHPString=lambda version: '83')
        patcher = mock.patch.dict(sys.modules, {'plogical.phpUtilities': php_module,
                                                'managePHP.phpManager': manager_module})
        patcher.start()
        self.addCleanup(patcher.stop)
        site = NS(id=5, title='Source', AutoUpdates='Disabled', FinalURL='source.example', PluginUpdates='Disabled',
                  ThemeUpdates='Disabled', owner_id=3, path='/home/source.example/public_html/',
                  owner=NS(id=3, domain='source.example', externalApp='sourc1234', adminEmail='owner@example.test',
                           phpSelection='PHP 8.3', ssl=1, state=1, package_id=1, admin_id=1))
        self.backups = mock.Mock()
        process = NS(debugPath=os.path.join(self.temp.name, 'no-debug'), executioner=self.executioner,
                     outputExecutioner=self.output)
        log = NS(statusWriter=self.write_status, writeToFile=lambda message: None)
        self.namespace = dict(
            WPSites=NS(objects=NS(get=lambda pk: site)), Administrator=NS(objects=NS(get=lambda pk: NS(pk=1))),
            WPSitesBackup=self.backups,
            ACLManager=NS(CreateSecureDir=lambda: None), ProcessUtilities=process, logging=log, secrets=secrets,
            shlex=shlex, time=time, json=json, randint=lambda low, high: low, is_job_folder=is_job_folder,
            os=NS(path=os.path, chmod=lambda path, mode: None), open=self.open_description, print=lambda *a: None)
        create, remove = load_methods('plogical/applicationInstaller.py', 'ApplicationInstaller',
                                      ['WPCreateBackup', 'removeJobFolder'], self.namespace)
        self.Installer = type('Installer', (), {'WPCreateBackup': create, 'removeJobFolder': remove})

    def open_description(self, path, mode='r'):
        # The backup's description is written to the panel's own folder first; here it stays in the test's.
        self.assertTrue(path.startswith('/home/cyberpanel/'), path)
        return open(os.path.join(self.temp.name, 'description'), mode)

    def write_status(self, path, message):
        with open(path, 'w') as handle:
            handle.write(message)

    def executioner(self, command, user=None):
        self.commands.append(command)
        return 1

    def output(self, command, user=None, shell=None, dir=None, retRequired=None):
        self.commands.append(command)
        if self.failing is not None and self.failing in command:
            return 0, 'it failed'
        return 1, 'wpdb'

    def backup(self, kind):
        installer = self.Installer()
        installer.extraArgs = {'tempStatusPath': self.status, 'WPid': 5, 'adminID': 1, 'Backuptype': kind}
        self.commands = []
        result = installer.WPCreateBackup()
        with open(self.status) as handle:
            return installer, result, handle.read()

    def folder(self, installer):
        self.assertTrue(is_job_folder(installer.tempPath), installer.tempPath)
        return installer.tempPath

    def position(self, fragment):
        matches = [index for index, command in enumerate(self.commands) if fragment in command]
        self.assertTrue(matches, '%s was not run: %s' % (fragment, self.commands))
        return matches[0]

    def test_every_kind_of_backup_closes_its_folder_first_and_removes_it_before_it_reports_success(self):
        for kind in ('1', '2', '3'):
            with self.subTest(kind=kind):
                installer, result, status = self.backup(kind)
                folder = self.folder(installer)
                self.assertEqual('Completed.[200]', status)
                self.assertEqual(1, result[0])
                made, closed = self.position('mkdir -p ' + folder), self.position('chmod 700 ' + folder)
                given, packed = self.position('chown -R sourc1234:sourc1234 ' + folder), self.position('tar -czvf')
                removed = self.position('rm -rf ' + folder)
                self.assertTrue(made < closed < given < packed < removed, self.commands)
                # Nothing is put into the folder before it is closed, and it is the last thing touched.
                self.assertEqual(closed, min(index for index, command in enumerate(self.commands)
                                             if folder in command and index != made))
                self.assertEqual([command for command in self.commands if command.startswith('rm -rf ')],
                                 ['rm -rf ' + folder])
                self.assertFalse([command for command in self.commands[removed + 1:] if folder in command])

    def test_the_archive_is_roots_alone_before_anything_is_written_to_it(self):
        for kind in ('1', '2', '3'):
            with self.subTest(kind=kind):
                installer, result, status = self.backup(kind)
                made = self.position('install -m 600 /dev/null ' + result[1])
                self.assertEqual(made + 1, self.position('tar -czvf ' + result[1]))

    def test_the_archive_is_made_of_the_same_folder_under_the_same_names(self):
        installer, result, status = self.backup('1')
        folder = self.folder(installer)
        packed = self.commands[self.position('tar -czvf')]
        self.assertTrue(re.fullmatch(r'tar -czvf /home/backup/backup-source\.example-[0-9._-]+\.tar\.gz -P ' + folder,
                                     packed), packed)
        self.assertEqual(result[1], packed.split()[2])
        description = json.loads(self.backups.call_args[1]['config'])
        self.assertEqual(os.path.basename(folder), description['RandomPath'])

    def test_a_backup_that_fails_at_any_step_leaves_no_copy_of_the_site_either(self):
        for kind, step in (('1', 'cp -R /home/source.example/public_html/*'), ('1', 'db export'), ('1', 'tar -czvf'),
                           ('2', 'tar -czvf'), ('3', 'db export'), ('3', 'tar -czvf')):
            with self.subTest(kind=kind, step=step):
                self.failing = step
                installer, result, status = self.backup(kind)
                folder = self.folder(installer)
                self.assertEqual('it failed. [404]', status)
                self.assertEqual(0, result[0])
                self.assertEqual('rm -rf ' + folder, self.commands[-1])
                self.assertLess(self.position(step), len(self.commands) - 1)

    def test_a_backup_that_fails_before_it_has_a_folder_removes_nothing(self):
        self.failing = 'config get DB_NAME'
        self.namespace['ProcessUtilities'].outputExecutioner = lambda *a, **k: (1, 'Error: wp-config.php not found')
        installer, result, status = self.backup('1')
        self.assertIn('[404]', status)
        self.assertFalse(hasattr(installer, 'tempPath'))
        self.assertFalse([command for command in self.commands if command.startswith('rm ')])

    def test_the_removal_takes_only_the_jobs_own_folder(self):
        installer = self.Installer()
        for path in (None, '', '/', '/usr/local/CyberCP/tmp', '/usr/local/CyberCP/tmp/', '/home/source.example',
                     '/usr/local/CyberCP/tmp/' + 'a' * 32 + '/..', '/usr/local/CyberCP/tmp/1234'):
            installer.tempPath = path
            self.assertEqual(0, installer.removeJobFolder(), path)
        self.assertEqual([], self.commands)
        self.assertEqual(0, self.Installer().removeJobFolder())
        installer.tempPath = '/usr/local/CyberCP/tmp/' + 'a' * 32
        self.assertEqual(1, installer.removeJobFolder())
        self.assertEqual(['rm -rf /usr/local/CyberCP/tmp/' + 'a' * 32], self.commands)

    def test_the_page_reads_the_jobs_status_from_outside_that_folder(self):
        manager = (ROOT / 'websiteFunctions/website.py').read_text()
        start = manager.index('    def WPCreateBackup(self, userID=None, data=None):')
        method = manager[start:manager.index('    def RestoreWPbackupNow(self, userID=None, data=None):', start)]
        self.assertIn("extraArgs['tempStatusPath'] = \"/home/cyberpanel/\" + str(randint(1000, 9999))", method)
        # The numbered file inside the folder is the backup's description, copied in for the archive.
        self.assertEqual(3, SOURCE.count('command = f"cp -R {configPath} {self.tempPath}"'))


class SourceTests(unittest.TestCase):
    def live(self, start, end):
        body = SOURCE[SOURCE.index(start):SOURCE.index(end)]
        return '\n'.join(line for line in body.splitlines() if not line.lstrip().startswith('#'))

    def test_no_backup_or_restore_removes_a_folder_by_a_path_it_has_not_checked(self):
        for start, end in (('    def WPCreateBackup(self):', '    def removeJobFolder(self):'),
                           ('    def RestoreWPbackupNow(self):', '    def UpdateDownloadStatus(self'),
                           ('    def placeBackup(self', '    def RestoreWPbackupNow(self):')):
            live = self.live(start, end)
            self.assertNotIn('rm -rf {self.tempPath}', live, start)
            self.assertNotIn("'rm -rf %s' % shlex.quote(self.tempPath)", live, start)
        self.assertEqual(4, self.live('    def WPCreateBackup(self):', '    def removeJobFolder(self):').count(
            'self.removeJobFolder()'))
        self.assertEqual(4, self.live('    def RestoreWPbackupNow(self):', '    def UpdateDownloadStatus(self').count(
            'self.removeJobFolder()'))


if __name__ == '__main__':
    unittest.main()
