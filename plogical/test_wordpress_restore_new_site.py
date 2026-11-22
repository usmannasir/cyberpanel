"""A WordPress backup restored to a new site ends with a working copy or with no new website at all."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import types
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.phpConfig import stored_php_selection
from plogical import wordpressInstallerUtilities as utilities
from plogical.test_php_restart_marker import load_methods

SOURCE = (Path(__file__).resolve().parents[1] / 'plogical/applicationInstaller.py').read_text()
PHP = '/usr/local/lsws/lsphp83/bin/php'
METHODS = ['siteCommand', 'directoryEntries', 'removeAddedEntries', 'removeCreatedWebsite', 'wordpressInstallNew',
           'pathPresent', 'restoreStep', 'siteConfigValue', 'unpackBackupAs', 'restoreToNewSite',
           'fillNewSiteFromBackup']
CONFIG = {'WPtitle': 'Source', 'WebVHuser': 'sourceuser', 'WebadminEmail': 'owner@example.test',
          'WPAutoUpdates': 'Disabled', 'WPPluginUpdates': 'Disabled', 'WPThemeUpdates': 'Disabled',
          'WebphpSelection': 'PHP 8.3', 'DatabaseUser': 'sourcedb'}
REMOVED = 'The website new.example that was created for this job has been removed again.'


class Response:
    def __init__(self, payload):
        self.content = json.dumps(payload).encode()


class Harness(unittest.TestCase):
    """The worker's real methods, with the database, the helper and the web server replaced."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wp-restore-test-')
        self.addCleanup(self.temp.cleanup)
        self.status = os.path.join(self.temp.name, 'status')
        self.worker_status = os.path.join(self.temp.name, 'worker')
        self.commands = []
        self.replies = {}
        self.manager = mock.Mock()
        self.release = mock.Mock()
        self.release.return_value.json.return_value = {'offers': [{'current': '7.1.5'}]}
        website_module = types.ModuleType('websiteFunctions.website')
        website_module.WebsiteManager = lambda: self.manager
        php_module = types.ModuleType('plogical.phpUtilities')
        php_module.phpUtilities = NS(GetPHPVersionFromFile=lambda vhost, domain=None: PHP)
        requests_module = types.ModuleType('requests')
        requests_module.get = self.release
        patcher = mock.patch.dict(sys.modules, {
            'websiteFunctions.website': website_module, 'plogical.phpUtilities': php_module,
            'requests': requests_module})
        patcher.start()
        self.addCleanup(patcher.stop)

        self.websites = mock.Mock()
        self.websites.objects.filter.return_value.exists.return_value = False
        self.children = mock.Mock()
        self.children.objects.filter.return_value.exists.return_value = False
        self.wpsites = mock.Mock()
        self.wpsites.objects.get.return_value = NS(
            path='/home/new.example/public_html/', owner=NS(externalApp='newuser', domain='new.example'))
        self.process = mock.Mock(debugPath=os.path.join(self.temp.name, 'no-debug'))
        self.process.outputExecutioner.return_value = ''
        self.log = mock.Mock()
        self.log.statusWriter.side_effect = self.write_status
        self.web_server = mock.Mock()
        self.namespace = dict(
            Websites=self.websites, ChildDomains=self.children, WPSites=self.wpsites, Administrator=mock.Mock(),
            ACLManager=mock.Mock(), ProcessUtilities=self.process, logging=self.log, os=os, time=mock.Mock(),
            shlex=shlex, wpplugins=mock.Mock(), randomPassword=NS(generate_pass=lambda length=14: 'P' * length),
            installUtilities=self.web_server, run_as_site_user=self.run_as_site_user,
            stored_php_selection=stored_php_selection, randint=lambda low, high: low)
        for name in ('build_directory_listing_command', 'build_entry_removal_command', 'change_php_succeeded',
                     'current_wordpress_version', 'directory_entry_names', 'entries_added_since',
                     'php_binary_for_selection', 'single_line_value', 'wordpress_cli_command',
                     'wordpress_config_set_command', 'wordpress_table_prefix_command'):
            self.namespace[name] = getattr(utilities, name)
        loaded = dict(zip(METHODS, load_methods('plogical/applicationInstaller.py', 'ApplicationInstaller',
                                                METHODS, self.namespace)))
        loaded['siteCommand'] = staticmethod(loaded['siteCommand'])
        self.Installer = type('Installer', (), loaded)
        self.namespace['ApplicationInstaller'] = self.Installer
        self.installer = self.Installer()
        self.installer.tempStatusPath = self.status
        self.installer.tempPath = '/usr/local/CyberCP/tmp/' + 'a' * 32
        self.installer.extraArgs = {'path': '', 'home': '1'}
        self.installer.data = self.installer.extraArgs

    def write_status(self, path, message):
        with open(path, 'w') as handle:
            handle.write(message)

    def status_text(self):
        with open(self.status) as handle:
            return handle.read()

    def run_as_site_user(self, command, user):
        """Stands for the status-reporting runner: (it exited with 0, its output as bytes)."""
        self.commands.append((user, command))
        for fragment, reply in self.replies.items():
            if fragment in command:
                return reply
        return True, b'Success: done.\n'

    def site_commands(self):
        return [command for user, command in self.commands]

    def position(self, fragment):
        matches = [index for index, command in enumerate(self.site_commands()) if fragment in command]
        self.assertTrue(matches, '%s was not run: %s' % (fragment, self.site_commands()))
        return matches[0]

    def created(self, line='WordPress installed..,[200]'):
        with open(self.worker_status, 'w') as handle:
            handle.write(line)
        self.manager.submitWorpressCreation.return_value = Response(
            {'status': 1, 'installStatus': 1, 'error_message': 'None', 'tempStatusPath': self.worker_status})

    def restore(self, kind='both'):
        return self.installer.restoreToNewSite(
            dict(CONFIG), kind, 7, 'new.example', 'backup-source.example-11.20.2026_10-00-00', 'b' * 32,
            'sourcedb.sql', 'source.example', 'owner', 'Default')


class NewSiteCreationTests(Harness):
    def setUp(self):
        super().setUp()
        self.installer.fillNewSiteFromBackup = mock.Mock()
        self.installer.removeCreatedWebsite = mock.Mock(return_value=REMOVED)

    def test_the_new_site_is_created_with_the_current_wordpress_release_and_only_as_a_new_website(self):
        self.created()
        self.restore()
        request = self.manager.submitWorpressCreation.call_args[0][1]
        self.assertEqual('7.1.5', request['WPVersion'])
        self.assertEqual(1, request['newWebsiteOnly'])
        self.assertEqual('new.example', request['domain'])
        self.assertEqual('owner', request['websiteOwner'])
        self.installer.fillNewSiteFromBackup.assert_called_once()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_the_first_login_of_the_new_site_is_not_a_value_from_the_backup(self):
        self.created()
        for kind in ('both', 'files'):
            self.restore(kind)
            password = self.manager.submitWorpressCreation.call_args[0][1]['PasswordByPass']
            self.assertEqual('P' * 20, password)
            self.assertNotIn(password, CONFIG.values())

    def test_no_release_from_wordpress_org_means_no_website_is_created(self):
        for failure in (OSError('no route'), None):
            with self.subTest(failure=failure):
                self.release.side_effect = failure
                self.release.return_value.json.return_value = {'offers': [{'current': 'latest'}]}
                with self.assertRaisesRegex(BaseException, 'no website was created'):
                    self.restore()
        self.manager.submitWorpressCreation.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_domain_that_exists_as_website_or_child_domain_is_refused_and_left_alone(self):
        for model in (self.websites, self.children):
            model.objects.filter.return_value.exists.return_value = True
            with self.assertRaisesRegex(BaseException, 'new.example already exists'):
                self.restore()
            model.objects.filter.return_value.exists.return_value = False
        self.manager.submitWorpressCreation.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_refused_creation_is_reported_with_its_reason(self):
        self.manager.submitWorpressCreation.return_value = Response(
            {'status': 0, 'installStatus': 0, 'error_message': 'WordPress Manager is a paid feature.'})
        with self.assertRaisesRegex(BaseException, 'could not be created: WordPress Manager is a paid feature'):
            self.restore()
        self.installer.fillNewSiteFromBackup.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_failed_creation_stops_the_restore_and_leaves_the_removal_to_the_creating_worker(self):
        self.created('Failed to install WordPress: error: Your WordPress version is 6.0, however the uploaded '
                     'plugin requires 6.2. %s [404]' % REMOVED)
        with self.assertRaises(BaseException) as raised:
            self.restore()
        self.assertIn('requires 6.2', str(raised.exception))
        self.assertIn(REMOVED.rstrip('.'), str(raised.exception))
        self.assertNotIn('[404]', str(raised.exception))
        self.installer.fillNewSiteFromBackup.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_step_that_fails_after_the_creation_removes_the_website_this_job_created(self):
        self.created()
        self.installer.fillNewSiteFromBackup.side_effect = BaseException(
            'The database could not be imported: ERROR 1064 (42000) at line 12.')
        with self.assertRaises(BaseException) as raised:
            self.restore()
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example')
        self.assertEqual('The database could not be imported: ERROR 1064 (42000) at line 12. ' + REMOVED.rstrip('.'),
                         str(raised.exception))

    def test_the_site_is_looked_up_under_its_folder_when_the_restore_names_one(self):
        self.created()
        self.installer.extraArgs.update(path='blog', home='0')
        self.restore()
        self.assertEqual('new.example/blog', self.installer.fillNewSiteFromBackup.call_args[0][-1])
        request = self.manager.submitWorpressCreation.call_args[0][1]
        self.assertEqual(('blog', '0'), (request['path'], request['home']))


class NewSiteContentTests(Harness):
    def setUp(self):
        super().setUp()
        self.replies = {
            'config get DB_NAME': (True, b'newdb\n'), 'config get DB_USER': (True, b'newuser_db\n'),
            'config get DB_PASSWORD': (True, b"p a$$'w\n"), 'config get table_prefix': (True, b'wp_\n'),
            'option get siteurl': (True, b'http://new.example\n'),
        }

    def fill(self, kind='both', config=None):
        return self.installer.fillNewSiteFromBackup(
            dict(config or CONFIG), kind, 'new.example', 'backup-source.example-11.20.2026_10-00-00', 'b' * 32,
            'sourcedb.sql', 'source.example', 'new.example')

    def test_a_backup_with_files_and_database_becomes_a_copy_with_its_own_database(self):
        self.fill()
        files = self.installer.tempPath + '/ab/usr/local/CyberCP/tmp/' + 'b' * 32
        read, copied = self.position('config get DB_PASSWORD'), self.position('cp -Rf')
        written, imported = self.position('config set DB_NAME'), self.position('db import')
        rewritten, checked = self.position('search-replace'), self.position('core is-installed')
        self.assertTrue(read < copied < written < imported < rewritten < checked, self.site_commands())
        commands = self.site_commands()
        self.assertEqual('cp -Rf %s/public_html/. /home/new.example/public_html/ 2>&1' % files, commands[copied])
        self.assertIn(" config set DB_NAME newdb ", commands[written])
        self.assertIn(" config set DB_USER newuser_db ", commands[written + 1])
        self.assertIn(' config set DB_PASSWORD %s ' % shlex.quote("p a$$'w"), commands[written + 2])
        self.assertIn(' db import %s/sourcedb.sql ' % files, commands[imported])
        self.assertIn(' search-replace source.example new.example ', commands[rewritten])
        self.assertIn(' search-replace https://www.new.example http://new.example ', commands[rewritten + 1])
        self.assertEqual({'newuser'}, {user for user, command in self.commands})
        self.wpsites.objects.get.assert_called_once_with(owner__domain='new.example', FinalURL='new.example')
        self.web_server.reStartLiteSpeed.assert_called_once()

    def test_the_new_sites_account_unpacks_its_own_copy_of_the_archive(self):
        self.fill()
        archive = self.installer.tempPath + '/backup-source.example-11.20.2026_10-00-00.tar.gz'
        as_root = [call[0][0] for call in self.process.executioner.call_args_list]
        self.assertEqual('rm -rf %s/ab' % self.installer.tempPath, as_root[0])
        self.assertEqual('chown -h newuser:newuser %s %s' % (self.installer.tempPath, archive), as_root[1])
        unpacked = self.position('tar -xf')
        self.assertEqual('tar -xf %s -C %s/ab 2>&1' % (archive, self.installer.tempPath),
                         self.site_commands()[unpacked])
        self.assertLess(unpacked, self.position('cp -Rf'))
        self.assertEqual('rm -rf ' + self.installer.tempPath, as_root[-1])

    def test_an_archive_that_does_not_unpack_ends_the_restore_with_what_tar_said(self):
        self.replies['tar -xf'] = (False, b'tar: Unexpected EOF in archive\n')
        with self.assertRaisesRegex(BaseException, 'could not be unpacked: tar: Unexpected EOF in archive'):
            self.installer.unpackBackupAs('newuser', 'backup-source.example-11.20.2026_10-00-00')
        self.replies['tar -xf'] = (False, b'')
        with self.assertRaisesRegex(BaseException, 'could not be unpacked: the command failed'):
            self.installer.unpackBackupAs('newuser', 'backup-source.example-11.20.2026_10-00-00')

    def test_a_backup_of_files_alone_keeps_the_tables_of_the_new_installation(self):
        self.fill('files')
        commands = self.site_commands()
        self.assertFalse([command for command in commands if 'db import' in command or 'search-replace' in command])
        self.assertLess(self.position('cp -Rf'), self.position('config set DB_NAME'))
        self.assertIn(' config set table_prefix wp_ --type=variable ', commands[self.position('config set table_prefix')])
        self.assertLess(self.position('config set table_prefix'), self.position('core is-installed'))

    def test_every_failed_step_ends_the_restore_before_the_next_one(self):
        steps = ('config get DB_NAME', 'mkdir', 'tar -xf', 'cp -Rf', 'config set DB_USER', 'db import',
                 'search-replace', 'core is-installed', 'option get siteurl')
        for index, step in enumerate(steps):
            with self.subTest(step=step):
                self.commands = []
                self.web_server.reset_mock()
                self.replies[step] = (False, b'it failed\n')
                with self.assertRaises(BaseException) as raised:
                    self.fill()
                del self.replies[step]
                self.assertIn('it failed', str(raised.exception))
                self.assertIn(step, self.site_commands()[-1])
                for later in steps[index + 1:]:
                    self.assertFalse([command for command in self.site_commands() if later in command], later)
                self.web_server.reStartLiteSpeed.assert_not_called()
        self.replies['config get DB_NAME'] = (True, b'newdb\n')

    def test_a_reported_wordpress_error_ends_the_restore_even_when_the_command_exits_with_zero(self):
        self.replies['db import'] = (True, b'Error: Import file missing or not readable.\n')
        with self.assertRaisesRegex(BaseException, 'could not be imported: Error: Import file missing'):
            self.fill()
        self.assertFalse([command for command in self.site_commands() if 'search-replace' in command])

    def test_a_database_setting_that_is_not_one_clean_value_is_never_written_back(self):
        for reply in ((True, b''), (True, b'PHP Warning: something\nnewdb\n'), (False, b'newdb\n'),
                      (True, b'Error: wp-config.php not found.\n')):
            with self.subTest(reply=reply):
                self.commands = []
                self.replies['config get DB_NAME'] = reply
                with self.assertRaisesRegex(BaseException, 'DB_NAME could not be read'):
                    self.fill()
                self.assertFalse([command for command in self.site_commands() if 'cp -Rf' in command])

    def test_a_copy_that_still_answers_under_the_old_address_is_a_failed_restore(self):
        self.replies['option get siteurl'] = (True, b'https://source.example\n')
        with self.assertRaisesRegex(BaseException, 'still uses the address https://source.example'):
            self.fill()
        self.web_server.reStartLiteSpeed.assert_not_called()

    def test_the_php_version_of_the_backup_is_selected_when_this_server_has_it(self):
        config = dict(CONFIG, WebphpSelection='PHP 74')
        wanted = '/usr/local/lsws/lsphp74/bin/php'
        self.process.outputExecutioner.return_value = '1,None\n'
        with mock.patch('os.path.isfile', side_effect=lambda path: path == wanted):
            self.fill(config=config)
        change = self.process.outputExecutioner.call_args[0][0]
        self.assertTrue(change.endswith("changePHP --phpVersion 'PHP 7.4' --path "
                                        "/usr/local/lsws/conf/vhosts/new.example/vhost.conf"), change)

    def test_a_php_version_this_server_lacks_or_an_unreadable_one_leaves_the_site_as_created(self):
        for selection in ('PHP 7.4', 'PHP 8.3', 'whatever; id', None):
            with mock.patch('os.path.isfile', return_value=False):
                self.fill(config=dict(CONFIG, WebphpSelection=selection))
        self.process.outputExecutioner.assert_not_called()
        self.web_server.reStartLiteSpeed.assert_called()


class CreatedWebsiteRemovalTests(Harness):
    def remove(self, reply, still_there=False):
        self.process.outputExecutioner.side_effect = lambda command, retRequired=None: reply
        self.websites.objects.filter.return_value.exists.return_value = still_there
        return self.installer.removeCreatedWebsite("new.example")

    def test_the_website_is_removed_with_the_panels_own_deletion_and_only_reported_gone_when_it_is(self):
        done = (1, 'removing\nWEBSITE_DELETE_RESULT={"completed": true}')
        self.assertEqual(REMOVED, self.remove(done))
        command = self.process.outputExecutioner.call_args[0][0]
        self.assertTrue(command.endswith('virtualHostUtilities.py deleteVirtualHostConfigurations '
                                         '--virtualHostName new.example'), command)
        for reply, still_there in ((done, True), ((1, 'WEBSITE_DELETE_RESULT={"completed": false}'), False),
                                   ((1, 'no result line'), False), (None, False)):
            with self.subTest(reply=reply, still_there=still_there):
                self.assertIn('could not be removed; delete it under Websites', self.remove(reply, still_there))

    def test_the_domain_reaches_the_command_as_one_argument(self):
        self.process.outputExecutioner.side_effect = lambda command, retRequired=None: (1, '')
        self.installer.removeCreatedWebsite('new.example; touch /tmp/x')
        self.assertTrue(self.process.outputExecutioner.call_args[0][0].endswith(
            "--virtualHostName 'new.example; touch /tmp/x'"))


class StepOutcomeTests(Harness):
    def test_a_step_reports_its_real_exit_status_and_its_error_output(self):
        self.replies['false'] = (False, b'')
        self.assertEqual((1, 'Success: done.\n'), self.Installer.siteCommand('true', 'siteuser'))
        self.assertEqual((0, ''), self.Installer.siteCommand('false', 'siteuser'))
        self.assertEqual([('siteuser', 'true 2>&1'), ('siteuser', 'false 2>&1')], self.commands)
        self.Installer.siteCommand('find /x', 'siteuser', False)
        self.assertEqual(('siteuser', 'find /x'), self.commands[-1])

    def test_a_failed_step_names_what_failed(self):
        self.replies['cp '] = (False, b"cp: cannot open '/x/wp-config.php' for reading: Permission denied\n")
        with self.assertRaisesRegex(BaseException, "files could not be copied: cp: cannot open '/x/wp-config.php'"):
            self.installer.restoreStep('cp -Rf /x/. /y', 'siteuser', 'The website files could not be copied')
        self.replies['cp '] = (False, b'')
        with self.assertRaisesRegex(BaseException, 'files could not be copied: the command failed'):
            self.installer.restoreStep('cp -Rf /x/. /y', 'siteuser', 'The website files could not be copied')

    def test_presence_is_read_from_the_output_and_an_unclear_answer_is_not_a_yes_or_a_no(self):
        for output, answer in (('present', True), ('present\n', True), ('', False),
                               ("find: '/x': Permission denied", None), ('-1Connection failed', None), (None, None)):
            with self.subTest(output=output):
                self.process.outputExecutioner.return_value = output
                self.assertIs(answer, self.installer.pathPresent('/home/backup/a b.tar.gz', 'f'))
        self.assertEqual("sudo find '/home/backup/a b.tar.gz' -maxdepth 0 -type f -printf present 2>/dev/null",
                         self.process.outputExecutioner.call_args[0][0])


class InstallDirectoryCleanupTests(Harness):
    """The bookkeeping of a failed installation, with real commands in a temporary directory."""

    def setUp(self):
        super().setUp()
        self.site = os.path.join(self.temp.name, 'public html')
        os.mkdir(self.site)
        self.namespace['run_as_site_user'] = self.run_here
        self.process.executioner.side_effect = lambda command, user=None: self.run_here(command, user)[0]

    def run_here(self, command, user):
        self.assertTrue(self.site in command, command)
        done = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return done.returncode == 0, done.stdout

    def put(self, *names):
        for name in names:
            path = os.path.join(self.site, name)
            if name.endswith('/'):
                os.makedirs(os.path.join(path, 'inner'))
            else:
                Path(path).write_text('content of ' + name)

    def test_a_failed_installation_removes_what_it_unpacked_and_keeps_what_was_there(self):
        self.put('.well-known/', 'kept file.txt', '-rf')
        before = self.installer.directoryEntries(self.site, 'siteuser')
        self.assertEqual({'.well-known', 'kept file.txt', '-rf'}, before)
        self.put('wp-config.php', 'index.php', 'wp-admin/', 'wp-content/', '.htaccess', "it's new")
        self.installer.removeAddedEntries(self.site, 'siteuser', before)
        self.assertEqual(['-rf', '.well-known', 'kept file.txt'], sorted(os.listdir(self.site)))
        self.assertTrue(os.path.isdir(os.path.join(self.site, '.well-known', 'inner')))

    def test_nothing_is_removed_without_a_reading_from_before_the_installation(self):
        self.put('wp-config.php', 'wp-admin/')
        self.installer.removeAddedEntries(self.site, 'siteuser', None)
        self.assertEqual(['wp-admin', 'wp-config.php'], sorted(os.listdir(self.site)))
        self.process.executioner.assert_not_called()

    def test_a_directory_that_cannot_be_read_gives_no_reading_and_no_removal(self):
        missing = os.path.join(self.site, 'gone')
        self.assertIsNone(self.installer.directoryEntries(missing, 'siteuser'))
        self.namespace['run_as_site_user'] = mock.Mock(side_effect=OSError('no helper'))
        self.assertIsNone(self.installer.directoryEntries(self.site, 'siteuser'))
        self.put('kept.txt')
        self.namespace['run_as_site_user'] = lambda command, user: (False, b'kept.txt\nwp-config.php\n')
        self.installer.removeAddedEntries(self.site, 'siteuser', set())
        self.assertEqual(['kept.txt'], os.listdir(self.site))
        self.process.executioner.assert_not_called()


class FailedInstallationTests(Harness):
    """installWordPress: a failure deletes the database it made and the files that point at it."""

    def setUp(self):
        super().setUp()
        self.install_status = os.path.join(self.temp.name, 'install')
        self.failing = None
        self.ran = []
        plugin = os.path.join(self.temp.name, 'plugin.zip')
        missing = type('DoesNotExist', (Exception,), {})
        children = mock.Mock(DoesNotExist=missing)
        children.objects.get.side_effect = missing()
        site = NS(domain='site.example', externalApp='siteuser', phpSelection='PHP 8.3',
                  package=NS(dataBases=5), databases_set=NS(all=lambda: NS(count=lambda: 0)))
        self.websites.objects.get.return_value = site
        self.databases = mock.Mock()
        self.mysql = mock.Mock()
        self.process.outputExecutioner.side_effect = self.output
        self.namespace.update(
            ChildDomains=children, Databases=self.databases, mysqlUtilities=self.mysql, subprocess=subprocess,
            PHPManager=NS(getPHPString=lambda selection: '83'),
            os=NS(path=NS(isfile=lambda path: True, exists=lambda path: False), devnull=os.devnull,
                  unlink=lambda path: None),
            download_verified_plugin=lambda: plugin)
        for name in ('build_wordpress_core_install_command', 'wrap_wordpress_site_shell_script',
                     'build_wordpress_config_command', 'build_wordpress_config_password_command',
                     'build_wordpress_site_install_command'):
            self.namespace[name] = getattr(utilities, name)
        install = load_methods('plogical/applicationInstaller.py', 'ApplicationInstaller', ['installWordPress'],
                               self.namespace)[0]
        self.Installer.installWordPress = install
        self.Installer.LOCALHOST, self.Installer.PORT = 'localhost', '3306'
        self.installer.extraArgs = dict(
            domainName='site.example', home='1', tempStatusPath=self.install_status, blogTitle='Site',
            adminUser='admin', adminPassword='secret', adminEmail='owner@example.test', WPVersion='6.0')
        self.installer.dbCreation = mock.Mock(return_value=('wpdb', 'wpuser', 'wppass'))
        self.installer.dataLossCheck = mock.Mock(return_value=1)
        self.installer.directoryEntries = mock.Mock(return_value={'.well-known'})
        self.installer.removeAddedEntries = mock.Mock()
        self.installer.registerWordPressSite = mock.Mock()

    def output(self, command, user=None, shell=None, dir=None, retRequired=None):
        self.ran.append(command)
        if command == 'wp --info':
            return 'WP-CLI root dir: /root/.wp-cli'
        if self.failing is not None and self.failing in command:
            text = ('Warning: The package could not be installed. Your WordPress version is 6.0, however the '
                    'uploaded plugin requires 6.2.\nError: No plugins installed.')
            return (0, text) if retRequired else text
        return (1, 'Success: done.') if retRequired else 'Success: done.'

    def install(self):
        self.assertEqual(0, self.installer.installWordPress())
        with open(self.install_status) as handle:
            return handle.read()

    def test_a_plugin_that_the_installed_wordpress_is_too_old_for_fails_the_installation_cleanly(self):
        self.failing = 'plugin install'
        status = self.install()
        self.assertIn('the uploaded plugin requires 6.2', status)
        self.assertTrue(status.endswith('[404]'))
        self.mysql.deleteDatabase.assert_called_once_with('wpdb', 'wpuser')
        self.databases.objects.get.return_value.delete.assert_called_once_with()
        self.installer.removeAddedEntries.assert_called_once_with(
            '/home/site.example/public_html/', 'siteuser', {'.well-known'})
        self.installer.registerWordPressSite.assert_not_called()
        self.assertFalse([command for command in self.ran if 'plugin activate' in command])

    def test_the_directory_is_read_after_the_empty_check_and_before_anything_is_unpacked(self):
        calls = mock.Mock()
        calls.attach_mock(self.installer.dataLossCheck, 'check')
        calls.attach_mock(self.installer.directoryEntries, 'read')
        self.process.outputExecutioner.side_effect = lambda *a, **k: calls.run(a[0]) and self.output(*a, **k)
        self.install()
        names = [call[0] for call in calls.mock_calls]
        unpack = next(index for index, call in enumerate(calls.mock_calls)
                      if call[0] == 'run' and 'wordpress-6.0.tar.gz' in call[1][0])
        self.assertLess(names.index('check'), names.index('read'))
        self.assertLess(names.index('read'), unpack)

    def test_a_directory_that_was_not_empty_keeps_everything_in_it(self):
        self.installer.dataLossCheck.return_value = 0
        status = self.install()
        self.assertEqual('Directory is not empty. [404]', status)
        self.installer.directoryEntries.assert_not_called()
        self.installer.removeAddedEntries.assert_called_once_with('/home/site.example/public_html/', 'siteuser', None)
        self.mysql.deleteDatabase.assert_called_once_with('wpdb', 'wpuser')

    def test_a_complete_installation_removes_nothing(self):
        self.assertEqual('Successfully Installed. [200]', self.install())
        self.installer.removeAddedEntries.assert_not_called()
        self.mysql.deleteDatabase.assert_not_called()
        self.installer.registerWordPressSite.assert_called_once()

    def test_with_the_debug_marker_a_failed_installation_is_left_for_inspection_with_its_database(self):
        self.namespace['os'].path.exists = lambda path: path == self.process.debugPath
        self.failing = 'plugin install'
        self.assertIn('[404]', self.install())
        self.mysql.deleteDatabase.assert_not_called()
        self.installer.removeAddedEntries.assert_not_called()


class SiteAndWordPressTogetherTests(Harness):
    """wordpressInstallNew: a website it creates for a WordPress installation does not outlive a failed one."""

    def setUp(self):
        super().setUp()
        self.creation_status = os.path.join(self.temp.name, 'creation')
        self.install_status = os.path.join(self.temp.name, 'install')
        self.install_line = 'Successfully Installed. [200]'
        data = dict(tempStatusPath=self.status, domainName='new.example', adminEmail='owner@example.test',
                    websiteOwner='owner', package='Default', adminID=7, apacheBackend=0, currentACL={'admin': 1},
                    blogTitle='Source', home='1', updates='Disabled', Plugins='Disabled', Themes='Disabled')
        self.installer.extraArgs = data
        self.installer.data = data
        self.installer.installWordPress = self.install_wordpress
        self.installer.removeCreatedWebsite = mock.Mock(return_value=REMOVED)
        self.Installer.registerWordPressSite = staticmethod(mock.Mock())
        self.namespace['ACLManager'].checkOwnership.return_value = 1

    def install_wordpress(self):
        self.installer.extraArgs['tempStatusPath'] = self.install_status
        with open(self.install_status, 'w') as handle:
            handle.write(self.install_line)

    def website_is_new(self, line='Website successfully created. [200]'):
        with open(self.creation_status, 'w') as handle:
            handle.write(line)
        self.websites.objects.get.side_effect = [LookupError('no such website'), mock.Mock()]
        self.manager.submitWebsiteCreation.return_value = Response(
            {'status': 1, 'createWebSiteStatus': 1, 'error_message': 'None', 'tempStatusPath': self.creation_status})

    def create(self):
        return self.installer.wordpressInstallNew()

    def test_a_new_website_with_a_working_installation_is_kept(self):
        self.website_is_new()
        self.create()
        self.assertEqual('WordPress installed..,[200]', self.status_text())
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_failed_installation_takes_back_the_website_created_for_it(self):
        self.website_is_new()
        self.install_line = ('Warning: The package could not be installed. Your WordPress version is 6.0, however '
                             'the uploaded plugin requires 6.2. [404]')
        self.assertEqual(0, self.create())
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example')
        self.assertEqual('Failed to install WordPress: error: Warning: The package could not be installed. Your '
                         'WordPress version is 6.0, however the uploaded plugin requires 6.2. %s [404]' % REMOVED,
                         self.status_text())

    def test_a_failed_installation_into_a_website_that_was_already_there_leaves_that_website(self):
        self.install_line = 'Directory is not empty. [404]'
        self.assertEqual(0, self.create())
        self.installer.removeCreatedWebsite.assert_not_called()
        self.manager.submitWebsiteCreation.assert_not_called()
        self.assertEqual('Failed to install WordPress: error: Directory is not empty. [404]', self.status_text())

    def test_a_website_whose_creation_did_not_finish_cleanly_is_not_this_jobs_to_remove(self):
        self.website_is_new('Website was created, but its disk/inode quota could not be verified. [404]')
        self.assertEqual(0, self.create())
        self.installer.removeCreatedWebsite.assert_not_called()
        self.assertIn('[404]', self.status_text())

    def test_a_restore_is_never_given_a_website_that_already_exists(self):
        self.installer.extraArgs['newWebsiteOnly'] = 1
        self.assertEqual(0, self.create())
        self.assertEqual('This website already exists. [404]', self.status_text())
        self.manager.submitWebsiteCreation.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()
        self.assertFalse(os.path.exists(self.install_status))

    def test_an_unexpected_error_still_ends_the_job_in_its_status_file(self):
        self.website_is_new()
        self.Installer.registerWordPressSite = staticmethod(mock.Mock(side_effect=RuntimeError('row not saved')))
        self.assertEqual(0, self.create())
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example')
        self.assertEqual('Failed to install WordPress: error: row not saved. %s [404]' % REMOVED, self.status_text())


class RestoreSourceTests(unittest.TestCase):
    def restore_lines(self):
        start = SOURCE.index('    def RestoreWPbackupNow(self):')
        end = SOURCE.index('    def UpdateDownloadStatus(self, transferred, total):')
        return [line for line in SOURCE[start:end].splitlines() if not line.lstrip().startswith('#')]

    def test_no_restore_names_a_wordpress_or_php_version_of_its_own(self):
        live = '\n'.join(line for line in SOURCE.splitlines() if not line.lstrip().startswith('#'))
        self.assertNotIn('DataToPass[\'WPVersion\'] = "', live)
        self.assertNotIn('lsphp74', live)

    def test_the_steps_a_restore_depends_on_report_their_real_exit_status(self):
        for line in self.restore_lines():
            if 'sudo -u' in line:
                for step in ('cp -R', 'db import', 'search-replace', 'config get', 'config set', 'tar '):
                    self.assertNotIn(step, line)
        live = '\n'.join(self.restore_lines())
        self.assertEqual(2, live.count("self.restoreStep('cp -Rf %s %s'"))
        self.assertEqual(2, live.count("'db', 'import'"))
        self.assertEqual(2, live.count('self.restoreToNewSite('))

    def test_a_restore_into_an_existing_site_reads_the_archive_as_that_sites_account(self):
        live = '\n'.join(self.restore_lines())
        unpack = "self.unpackBackupAs(WPSites.objects.get(pk=DesSiteID).owner.externalApp, BackUpFileName)"
        self.assertEqual(1, live.count(unpack))
        self.assertLess(live.index("if restoreTarget == 'existing':"), live.index(unpack))
        self.assertLess(live.index(unpack), live.index("if BackupType == 'DataBase Backup':"))

    def test_a_request_the_backup_cannot_serve_ends_before_the_download_and_the_archive_is_checked_first(self):
        live = '\n'.join(self.restore_lines())
        self.assertLess(live.index('restore_plan(BackupType, DesSiteID, DomainName)'), live.index('paramiko'))
        self.assertLess(live.index("self.pathPresent(backupFiles, 'd') is not True"),
                        live.index("if BackupType == 'DataBase Backup':"))

    def test_only_an_archive_this_job_downloaded_is_removed_and_never_by_an_unset_name(self):
        live = '\n'.join(self.restore_lines())
        self.assertNotIn('rm -rf /home/backup/', live)
        self.assertEqual(2, live.count("'rm -f %s' % shlex.quote(downloadedArchive)"))
        self.assertEqual(2, live.count('if not archiveWasHere'))
        # An unclear answer about a file of that name counts as "it was here".
        self.assertIn('archiveWasHere = self.pathPresent(localArchive) is not False', live)
        self.assertLess(live.index('archiveWasHere = '), live.index('paramiko'))


if __name__ == '__main__':
    unittest.main()
