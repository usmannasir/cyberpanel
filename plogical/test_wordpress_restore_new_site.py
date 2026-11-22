"""A WordPress backup restored to a new site ends with a working copy or with no new website at all.

A restore into an existing site keeps that site's own database settings in
place at every moment, and no restore unpacks a backup with root's rights.
"""
import json
import os
from pathlib import Path
import pwd
import shlex
import shutil
import stat
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
from websiteFunctions.wordpressRestore import backup_layout

SOURCE = (Path(__file__).resolve().parents[1] / 'plogical/applicationInstaller.py').read_text()
PHP = '/usr/local/lsws/lsphp83/bin/php'
METHODS = ['siteCommand', 'directoryEntries', 'removeAddedEntries', 'removeCreatedWebsite', 'wordpressInstallNew',
           'pathPresent', 'restoreStep', 'siteConfigValue', 'siteDatabaseSettings', 'foundBeforeCreation',
           'backupLayout', 'otherDomainRefusal', 'placeBackup', 'restoreToNewSite', 'fillNewSiteFromBackup']
CONFIG = {'WPtitle': 'Source', 'WebVHuser': 'sourceuser', 'WebadminEmail': 'owner@example.test',
          'WPAutoUpdates': 'Disabled', 'WPPluginUpdates': 'Disabled', 'WPThemeUpdates': 'Disabled',
          'WebphpSelection': 'PHP 8.3', 'DatabaseUser': 'sourcedb'}
REMOVED = 'The website new.example that was created for this job has been removed again.'
NAME = 'backup-source.example-11.20.2026_10-00-00'
FOLDER = 'b' * 32
STORED = '/usr/local/CyberCP/tmp/' + FOLDER
LISTING = '\n'.join([STORED + '/public_html/wp-includes/version.php', STORED + '/public_html/wp-config.php',
                     STORED + '/sourcedb.sql'])
SITE = '/home/new.example/public_html/'


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
        self.zone = mock.Mock(return_value=False)
        dns_module = types.ModuleType('plogical.dnsUtilities')
        dns_module.DNS = NS(zoneExists=self.zone)
        accounts = types.ModuleType('pwd')
        accounts.getpwnam = lambda user: pwd.getpwnam(user) if user == 'nobody' else NS(pw_gid=1234)
        patcher = mock.patch.dict(sys.modules, {
            'websiteFunctions.website': website_module, 'plogical.phpUtilities': php_module,
            'requests': requests_module, 'plogical.dnsUtilities': dns_module, 'pwd': accounts})
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
                     'wordpress_config_set_command', 'wordpress_table_prefix_command', 'brief_output',
                     'out_of_quota', 'worker_failure_reason'):
            self.namespace[name] = getattr(utilities, name)
        loaded = dict(zip(METHODS, load_methods('plogical/applicationInstaller.py', 'ApplicationInstaller',
                                                METHODS, self.namespace)))
        loaded['siteCommand'] = staticmethod(loaded['siteCommand'])
        self.Installer = type('Installer', (), loaded)
        self.namespace['ApplicationInstaller'] = self.Installer
        self.installer = self.Installer()
        self.installer.tempStatusPath = self.status
        self.installer.tempPath = '/usr/local/CyberCP/tmp/' + 'a' * 32
        self.archive = '%s/%s.tar.gz' % (self.installer.tempPath, NAME)
        self.work = self.installer.tempPath + '/site'
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

    def layout(self, kind='both', listing=LISTING):
        return backup_layout(kind, listing, FOLDER, 'sourcedb.sql')

    def restore(self, kind='both'):
        return self.installer.restoreToNewSite(
            dict(CONFIG), kind, 7, 'new.example', self.archive, self.layout(kind), 'source.example', 'owner',
            'Default')


class NewSiteCreationTests(Harness):
    def setUp(self):
        super().setUp()
        self.installer.fillNewSiteFromBackup = mock.Mock()
        self.installer.removeCreatedWebsite = mock.Mock(return_value=REMOVED)
        self.installer.otherDomainRefusal = mock.Mock(return_value=None)
        self.installer.foundBeforeCreation = mock.Mock(return_value=('dns',))

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

    def test_a_backup_tied_to_its_old_domain_is_refused_with_the_reason_before_anything_is_created(self):
        self.installer.otherDomainRefusal.return_value = 'The wp-config.php in this backup fixes the address'
        with self.assertRaisesRegex(BaseException, 'fixes the address'):
            self.restore()
        self.installer.otherDomainRefusal.assert_called_once_with(self.archive, self.layout())
        self.release.assert_not_called()
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
                     'plugin requires 6.2. %s [404]\n' % REMOVED)
        with self.assertRaises(BaseException) as raised:
            self.restore()
        self.assertIn('requires 6.2', str(raised.exception))
        self.assertIn(REMOVED.rstrip('.'), str(raised.exception))
        self.assertNotIn('[404]', str(raised.exception))
        self.assertNotIn('\n', str(raised.exception))
        self.installer.fillNewSiteFromBackup.assert_not_called()
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_step_that_fails_after_the_creation_removes_the_website_but_not_what_was_there_before_it(self):
        self.created()
        self.installer.fillNewSiteFromBackup.side_effect = BaseException(
            'The database could not be imported: ERROR 1064 (42000) at line 12.')
        calls = mock.Mock()
        calls.attach_mock(self.installer.foundBeforeCreation, 'look')
        calls.attach_mock(self.manager.submitWorpressCreation, 'create')
        with self.assertRaises(BaseException) as raised:
            self.restore()
        # The zone was there before the creation: asked before, and kept.
        self.assertEqual(['look', 'create'], [call[0] for call in calls.mock_calls])
        self.installer.foundBeforeCreation.assert_called_once_with('new.example')
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example', ('dns',))
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

    def fill(self, kind='both', config=None, listing=LISTING):
        return self.installer.fillNewSiteFromBackup(
            dict(config or CONFIG), kind, 'new.example', self.archive, self.layout(kind, listing),
            'source.example', 'new.example')

    def test_a_backup_with_files_and_database_becomes_a_copy_with_its_own_database(self):
        self.fill()
        commands = self.site_commands()
        read, small = self.position('config get DB_PASSWORD'), self.position('--strip-components=5')
        written, files = self.position('config set DB_NAME'), self.position('--strip-components=6')
        placed, imported = self.position('cp -f'), self.position('db import')
        rewritten, checked = self.position('search-replace'), self.position('core is-installed')
        self.assertTrue(read < small < written < files < placed < imported < rewritten < checked, commands)
        unpack = 'tar -xzf %s --no-same-owner --no-same-permissions -C ' % self.archive
        self.assertEqual('%s%s --strip-components=5 %s/public_html/wp-config.php %s/sourcedb.sql 2>&1' % (
            unpack, self.work, STORED, STORED), commands[small])
        self.assertEqual('%s%s --strip-components=6 --anchored --exclude=%s/public_html/wp-config.php '
                         '%s/public_html 2>&1' % (unpack, SITE, STORED, STORED), commands[files])
        self.assertEqual('cp -f %s/public_html/wp-config.php %swp-config.php 2>&1' % (self.work, SITE),
                         commands[placed])
        self.assertIn(' db import %s/sourcedb.sql ' % self.work, commands[imported])
        self.assertIn(' search-replace source.example new.example ', commands[rewritten])
        self.assertIn(' search-replace https://www.new.example http://new.example ', commands[rewritten + 1])
        self.assertEqual({'newuser'}, {user for user, command in self.commands})
        self.wpsites.objects.get.assert_called_once_with(owner__domain='new.example', FinalURL='new.example')
        self.web_server.reStartLiteSpeed.assert_called_once()

    def test_the_backups_configuration_gets_the_new_sites_database_before_it_is_ever_in_the_site(self):
        self.fill()
        commands = self.site_commands()
        written = self.position('config set DB_NAME')
        scratch = '--path=%s/public_html' % self.work
        self.assertIn(' config set DB_NAME newdb ', commands[written])
        self.assertIn(' config set DB_USER newuser_db ', commands[written + 1])
        self.assertIn(' config set DB_PASSWORD %s ' % shlex.quote("p a$$'w"), commands[written + 2])
        for command in commands:
            if ' config set ' in command:
                self.assertTrue(command.endswith(scratch + ' 2>&1'), command)
        self.assertFalse([command for command in commands if 'table_prefix' in command])

    def test_the_archive_is_opened_to_the_sites_group_and_stays_roots_file(self):
        self.fill()
        as_root = [call[0][0] for call in self.process.executioner.call_args_list]
        self.assertEqual(['chown -h root:1234 ' + self.archive, 'chmod 640 ' + self.archive, 'mkdir ' + self.work,
                          'chown -h newuser ' + self.work, 'rm -rf ' + self.installer.tempPath], as_root)
        # Nothing is unpacked by root, and no command of the site's account is a root command.
        for call in self.process.method_calls:
            self.assertNotIn('tar ', str(call))

    def test_a_backup_of_files_alone_keeps_the_tables_of_the_new_installation(self):
        self.fill('files')
        commands = self.site_commands()
        self.assertFalse([command for command in commands if 'db import' in command or 'search-replace' in command])
        self.assertIn(' config set table_prefix wp_ --type=variable ',
                      commands[self.position('config set table_prefix')])
        self.assertLess(self.position('config set table_prefix'), self.position('--strip-components=6'))
        self.assertLess(self.position('cp -f'), self.position('core is-installed'))
        self.assertEqual('%s --strip-components=5 %s/public_html/wp-config.php 2>&1' % (
            'tar -xzf %s --no-same-owner --no-same-permissions -C %s' % (self.archive, self.work), STORED),
            commands[self.position('--strip-components=5')])

    def test_a_backup_of_a_staging_site_is_copied_from_the_folder_its_files_are_in(self):
        nested = '\n'.join(['usr/local/CyberCP/tmp/%s/public_html/public_html/wp-config.php' % FOLDER,
                            'usr/local/CyberCP/tmp/%s/public_html/public_html/wp-includes/version.php' % FOLDER,
                            'usr/local/CyberCP/tmp/%s/sourcedb.sql' % FOLDER])
        self.fill(listing=nested)
        commands = self.site_commands()
        stored = STORED.lstrip('/')
        self.assertTrue(commands[self.position('--strip-components=7')].endswith(
            '-C %s --strip-components=7 --anchored --exclude=%s/public_html/public_html/wp-config.php '
            '%s/public_html/public_html 2>&1' % (SITE, stored, stored)))
        self.assertEqual('cp -f %s/public_html/public_html/wp-config.php %swp-config.php 2>&1' % (self.work, SITE),
                         commands[self.position('cp -f')])

    def test_every_failed_step_ends_the_restore_before_the_next_one(self):
        steps = ('config get DB_NAME', '--strip-components=5', 'config set DB_USER', '--strip-components=6', 'cp -f',
                 'db import', 'search-replace', 'core is-installed', 'option get siteurl')
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
                self.assertFalse([command for command in self.site_commands() if 'tar ' in command])

    def test_the_copy_must_answer_under_exactly_the_new_domain(self):
        for address in (b'https://source.example\n', b'http://anew.example\n', b'http://new.example.evil.test\n',
                        b'http://old.test/new.example\n', b''):
            with self.subTest(address=address):
                self.replies['option get siteurl'] = (True, address)
                with self.assertRaisesRegex(BaseException, 'instead of under new.example'):
                    self.fill()
        self.web_server.reStartLiteSpeed.assert_not_called()
        for address in (b'http://new.example\n', b'https://www.new.example/blog\n', b'HTTPS://New.Example\n'):
            self.replies['option get siteurl'] = (True, address)
            self.fill()

    def test_a_used_up_quota_is_named_as_the_reason(self):
        self.replies['--strip-components=6'] = (
            False, b'tar: wp-content/uploads/a.jpg: Cannot write: Disk quota exceeded\n' * 50)
        with self.assertRaises(BaseException) as raised:
            self.fill()
        self.assertIn('The website files could not be copied: the disk quota of this website is used up',
                      str(raised.exception))
        self.assertNotIn('a.jpg', str(raised.exception))

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


class ExistingSiteContentTests(Harness):
    """placeBackup as the restores into an existing site use it."""

    SETTINGS = [('DB_NAME', 'owndb'), ('DB_USER', 'ownuser'), ('DB_PASSWORD', 'ownpass')]

    def place(self, kind='both', settings=SETTINGS):
        return self.installer.placeBackup(self.layout(kind), self.archive, 'siteuser', PHP,
                                          '/home/site.example/public_html', settings)

    def test_a_restore_that_stops_while_copying_leaves_the_sites_own_configuration_in_place(self):
        self.replies['--strip-components=6'] = (
            False, b"tar: wp-content/cache: Cannot open: Permission denied\ntar: Exiting with failure status\n")
        with self.assertRaisesRegex(BaseException, 'The website files could not be copied: tar: wp-content/cache'):
            self.place()
        commands = self.site_commands()
        # Nothing has written a wp-config.php into the site: the copy leaves
        # that one file out, and the prepared one is not put in place.
        self.assertIn('--anchored --exclude=%s/public_html/wp-config.php ' % STORED, commands[-1])
        self.assertFalse([command for command in commands if 'cp -f' in command])
        for command in commands:
            if ' config set ' in command:
                self.assertIn('--path=%s/public_html ' % self.work, command)
            self.assertNotIn('/home/site.example/public_html/wp-config.php', command)

    def test_the_configuration_put_in_place_carries_the_sites_own_database_settings(self):
        self.assertEqual(self.work + '/sourcedb.sql', self.place())
        commands = self.site_commands()
        written = self.position('config set DB_NAME')
        self.assertEqual(['owndb', 'ownuser', 'ownpass'],
                         [shlex.split(command)[11] for command in commands[written:written + 3]])
        self.assertLess(written + 2, self.position('--strip-components=6'))
        self.assertEqual('cp -f %s/public_html/wp-config.php /home/site.example/public_html/wp-config.php 2>&1'
                         % self.work, commands[-1])

    def test_a_failed_setting_stops_before_any_file_of_the_site_is_touched(self):
        self.replies['config set DB_USER'] = (False, b'Error: Could not process the wp-config.php transformation.\n')
        with self.assertRaisesRegex(BaseException, 'database settings could not be written'):
            self.place()
        self.assertFalse([command for command in self.site_commands() if '/home/site.example' in command])

    def test_a_database_backup_only_brings_its_dump(self):
        self.assertEqual(self.work + '/sourcedb.sql', self.place('database', None))
        self.assertEqual(['tar -xzf %s --no-same-owner --no-same-permissions -C %s --strip-components=5 '
                          '%s/sourcedb.sql 2>&1' % (self.archive, self.work, STORED)], self.site_commands())

    def test_a_backup_without_a_configuration_file_leaves_the_sites_own_one(self):
        listing = STORED + '/public_html/wp-includes/version.php'
        self.installer.placeBackup(backup_layout('files', listing, FOLDER, 'x.sql'), self.archive, 'siteuser', PHP,
                                   '/home/site.example/public_html', self.SETTINGS)
        self.assertEqual(['tar -xzf %s --no-same-owner --no-same-permissions -C /home/site.example/public_html '
                          '--strip-components=6 %s/public_html 2>&1' % (self.archive, STORED)],
                         self.site_commands())

    def test_a_site_without_readable_settings_takes_its_own_backups_configuration_unchanged(self):
        self.place('files', None)
        self.assertFalse([command for command in self.site_commands() if ' config set ' in command])
        self.assertIn('cp -f ', self.site_commands()[-1])

    def test_the_sites_settings_are_read_in_the_order_they_are_written(self):
        self.replies = {'config get DB_NAME': (True, b'a\n'), 'config get DB_USER': (True, b'b\n'),
                        'config get DB_PASSWORD': (True, b'c\n'), 'config get table_prefix': (True, b'wp_\n')}
        self.assertEqual([('DB_NAME', 'a'), ('DB_USER', 'b'), ('DB_PASSWORD', 'c')],
                         self.installer.siteDatabaseSettings(PHP, '/home/site.example/public_html', 'siteuser',
                                                             False))
        self.assertEqual(('table_prefix', 'wp_'), self.installer.siteDatabaseSettings(
            PHP, '/home/site.example/public_html', 'siteuser', True)[-1])


class ArchiveReadingTests(Harness):
    def test_the_layout_is_read_from_the_names_in_the_archive_by_an_account_without_rights(self):
        self.process.outputExecutioner.return_value = LISTING + '\n'
        self.assertEqual(self.layout(), self.installer.backupLayout(self.archive, 'both', FOLDER, 'sourcedb.sql'))
        self.assertEqual(
            ("sudo cat %s | sudo -u nobody tar -tzf - 2>/dev/null | grep -E '^/?usr/local/CyberCP/tmp/%s/"
             "(public_html/(public_html/)?(wp-config\\.php|wp-includes/version\\.php)|[^/]+\\.sql)$'"
             % (self.archive, FOLDER), None, True), self.process.outputExecutioner.call_args[0])

    def test_an_archive_without_what_its_kind_promises_ends_the_restore_with_the_reason(self):
        for kind, listing, reason in (('both', '', 'holds no WordPress files'), ('files', None, 'no WordPress files'),
                                      ('both', STORED + '/public_html/wp-config.php', 'holds no database dump'),
                                      ('database', STORED + '/other.sql', 'holds no database dump')):
            self.process.outputExecutioner.return_value = listing
            with self.assertRaisesRegex(BaseException, reason):
                self.installer.backupLayout(self.archive, kind, FOLDER, 'sourcedb.sql')
        with self.assertRaisesRegex(BaseException, 'work folder that no backup of this panel has'):
            self.installer.backupLayout(self.archive, 'both', '../../etc', 'sourcedb.sql')

    def test_the_backups_configuration_is_only_printed_and_only_its_address_lines_are_kept(self):
        self.process.outputExecutioner.return_value = "define( 'WP_SITEURL', 'https://source.example' );\n"
        self.assertIn('fixes the address', self.installer.otherDomainRefusal(self.archive, self.layout()))
        self.assertEqual(
            ("sudo cat %s | sudo -u nobody tar -xzOf - %s/public_html/wp-config.php 2>/dev/null | grep -E "
             "'WP_HOME|WP_SITEURL|MULTISITE|SUBDOMAIN_INSTALL|DOMAIN_CURRENT_SITE'" % (self.archive, STORED),
             None, True), self.process.outputExecutioner.call_args[0])
        self.process.outputExecutioner.return_value = "define('MULTISITE', true);\n"
        self.assertIn('WordPress network', self.installer.otherDomainRefusal(self.archive, self.layout()))
        for harmless in ('', None, "// define('WP_HOME', 'x');\n# define('MULTISITE', true);\n",
                         "define('MULTISITE', false);\ndefine( 'WP_ALLOW_MULTISITE', true );\n"):
            self.process.outputExecutioner.return_value = harmless
            self.assertIsNone(self.installer.otherDomainRefusal(self.archive, self.layout()))

    def test_a_backup_without_a_configuration_file_has_nothing_that_ties_it_to_a_domain(self):
        layout = backup_layout('files', STORED + '/public_html/wp-includes/version.php', FOLDER, 'x.sql')
        self.assertIsNone(self.installer.otherDomainRefusal(self.archive, layout))
        self.process.outputExecutioner.assert_not_called()

    def test_what_a_creation_would_reuse_is_asked_and_an_unclear_answer_counts_as_there(self):
        self.zone.return_value = True
        self.process.outputExecutioner.side_effect = lambda command: '' if 'vmail' in command else 'find: no'
        self.assertEqual(('dns', 'ssl'), self.installer.foundBeforeCreation('new.example'))
        self.zone.assert_called_once_with('new.example')
        asked = [call[0][0] for call in self.process.outputExecutioner.call_args_list]
        self.assertEqual(['sudo find /home/vmail/new.example -maxdepth 0 -printf present 2>/dev/null',
                          'sudo find /root/.acme.sh/new.example -maxdepth 0 -printf present 2>/dev/null'], asked)
        self.zone.return_value = False
        self.process.outputExecutioner.side_effect = lambda command: ''
        self.assertEqual((), self.installer.foundBeforeCreation('new.example'))
        self.zone.side_effect = RuntimeError('no database')
        self.assertEqual(('dns', 'mail', 'ssl'), self.installer.foundBeforeCreation('new.example'))


@unittest.skipUnless(os.geteuid() == 0 and shutil.which('sudo') and shutil.which('tar'),
                     'needs root, sudo and tar: the archive is unpacked as the account "nobody"')
class RealArchiveTests(Harness):
    """placeBackup with real archives and a real unprivileged account, inside a temporary directory."""

    def setUp(self):
        super().setUp()
        os.chmod(self.temp.name, 0o755)
        self.nobody = pwd.getpwnam('nobody')
        self.site = os.path.join(self.temp.name, 'site')
        os.mkdir(self.site)
        self.write(self.site, 'wp-config.php', 'own configuration\n')
        self.write(self.site, 'kept.txt', 'kept\n')
        self.own(self.site)
        self.installer.tempPath = os.path.join(self.temp.name, 'work')
        os.mkdir(self.installer.tempPath)
        self.archive = os.path.join(self.installer.tempPath, NAME + '.tar.gz')
        self.process.executioner.side_effect = self.as_root
        self.process.outputExecutioner.side_effect = self.read_as_root
        self.namespace['run_as_site_user'] = self.as_nobody

    def write(self, folder, name, content, mode=0o644):
        path = os.path.join(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as handle:
            handle.write(content)
        os.chmod(path, mode)
        return path

    def own(self, path):
        subprocess.check_call(['chown', '-R', 'nobody', path])

    def pack(self, folder='public_html', leading_slash=True, config='backup configuration\n', core=True):
        source = os.path.join(self.temp.name, 'source')
        shutil.rmtree(source, ignore_errors=True)
        root = os.path.join(source, 'usr/local/CyberCP/tmp', FOLDER)
        files = os.path.join(root, folder)
        if config is not None:
            self.write(files, 'wp-config.php', config, 0o600)
        if core:
            self.write(files, 'wp-includes/version.php', "<?php $wp_version = '6.8';\n", 0o4755)
        self.write(files, 'index.php', 'index of the backup\n')
        self.write(files, '.htaccess', 'rules\n')
        self.write(files, 'wp-content/uploads/pic.jpg', 'picture\n')
        self.write(files, 'blog/wp-config.php', 'configuration of a second site in a folder\n')
        self.write(root, 'sourcedb.sql', 'CREATE TABLE wp_posts (id int);\n')
        self.write(root, '1234', '{}\n')
        command = ['tar', '-czf', self.archive, '-C', source]
        if leading_slash:
            command += ['-P', '--transform', 's,^usr,/usr,']
        subprocess.check_call(command + ['usr'])
        os.chmod(self.archive, 0o600)

    def inside(self, command):
        self.assertIn(self.temp.name, command, command)

    def as_root(self, command, user=None):
        self.inside(command)
        return 1 if subprocess.call(command, shell=True) == 0 else 0

    def read_as_root(self, command, user=None, shell=None):
        self.inside(command)
        return subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True).stdout

    def as_nobody(self, command, user):
        self.assertEqual('nobody', user)
        self.inside(command)
        words = shlex.split(command)
        if '/usr/bin/wp' in words:
            # Stands for `wp config set`: the setting is added to the file it was pointed at.
            at = words.index('set')
            folder = [word for word in words if word.startswith('--path=')][0][len('--path='):]
            with open(os.path.join(folder, 'wp-config.php'), 'a') as handle:
                handle.write('%s=%s\n' % (words[at + 1], words[at + 2]))
            return True, b'Success: Updated.\n'
        done = subprocess.run(['sudo', '-u', 'nobody', '--', 'sh', '-c', command], cwd='/', stdout=subprocess.PIPE)
        return done.returncode == 0, done.stdout

    def read(self, *names):
        with open(os.path.join(self.site, *names)) as handle:
            return handle.read()

    def place(self, kind='both', settings=(('DB_NAME', 'owndb'), ('DB_USER', 'ownuser'))):
        layout = self.installer.backupLayout(self.archive, kind, FOLDER, 'sourcedb.sql')
        return layout, self.installer.placeBackup(layout, self.archive, 'nobody', PHP, self.site + '/', settings)

    def test_the_files_land_in_the_site_and_the_configuration_arrives_with_the_sites_own_database(self):
        for leading_slash in (True, False):
            with self.subTest(leading_slash=leading_slash):
                shutil.rmtree(os.path.join(self.installer.tempPath, 'site'), ignore_errors=True)
                self.pack(leading_slash=leading_slash)
                layout, dump = self.place()
                self.assertEqual(6, layout['strip'])
                self.assertEqual('backup configuration\nDB_NAME=owndb\nDB_USER=ownuser\n', self.read('wp-config.php'))
                self.assertEqual('index of the backup\n', self.read('index.php'))
                self.assertEqual('rules\n', self.read('.htaccess'))
                self.assertEqual('picture\n', self.read('wp-content', 'uploads', 'pic.jpg'))
                # Only the site's own wp-config.php is held back, not one further down.
                self.assertEqual('configuration of a second site in a folder\n', self.read('blog', 'wp-config.php'))
                self.assertEqual('kept\n', self.read('kept.txt'))
                with open(dump) as handle:
                    self.assertEqual('CREATE TABLE wp_posts (id int);\n', handle.read())
                self.assertFalse(os.path.exists(os.path.join(self.site, 'public_html')))
                self.assertFalse(os.path.exists(os.path.join(self.site, 'sourcedb.sql')))

    def test_nothing_from_the_archive_is_roots_or_setuid_and_the_archive_is_not_the_accounts_file(self):
        self.pack()
        self.place()
        for top in (self.site, os.path.join(self.installer.tempPath, 'site')):
            for folder, folders, files in os.walk(top):
                for name in folders + files:
                    status = os.lstat(os.path.join(folder, name))
                    self.assertEqual(self.nobody.pw_uid, status.st_uid, name)
                    self.assertFalse(status.st_mode & (stat.S_ISUID | stat.S_ISGID), name)
        archive = os.stat(self.archive)
        self.assertEqual((0, self.nobody.pw_gid, 0o640), (archive.st_uid, archive.st_gid, stat.S_IMODE(archive.st_mode)))
        self.assertEqual([NAME + '.tar.gz', 'site'], sorted(os.listdir(self.installer.tempPath)))

    def test_a_staging_sites_backup_is_copied_from_the_folder_one_level_down(self):
        self.pack(folder='public_html/public_html', leading_slash=False)
        layout, dump = self.place()
        self.assertEqual(7, layout['strip'])
        self.assertEqual('index of the backup\n', self.read('index.php'))
        self.assertEqual('backup configuration\nDB_NAME=owndb\nDB_USER=ownuser\n', self.read('wp-config.php'))
        self.assertFalse(os.path.exists(os.path.join(self.site, 'public_html')))

    def test_a_folder_the_account_cannot_write_stops_the_restore_with_the_sites_own_configuration(self):
        self.pack()
        os.mkdir(os.path.join(self.site, 'wp-content'))
        with self.assertRaisesRegex(BaseException, 'The website files could not be copied: .*Permission denied'):
            self.place()
        self.assertEqual('own configuration\n', self.read('wp-config.php'))
        # The copy went on past the folder it could not write, as far as it could.
        self.assertEqual('index of the backup\n', self.read('index.php'))
        self.assertFalse(os.path.exists(os.path.join(self.site, 'wp-content', 'uploads')))

    def test_a_folder_of_the_site_that_was_a_link_holds_the_backups_files_afterwards(self):
        # The backup holds a real folder there. It takes the link's place;
        # what the link pointed at is left as it was.
        self.pack()
        elsewhere = os.path.join(self.temp.name, 'elsewhere')
        self.write(elsewhere, 'theirs.txt', 'not the site\'s\n')
        os.symlink(elsewhere, os.path.join(self.site, 'wp-content'))
        self.own(elsewhere)
        subprocess.check_call(['chown', '-h', 'nobody', os.path.join(self.site, 'wp-content')])
        self.place()
        self.assertEqual('picture\n', self.read('wp-content', 'uploads', 'pic.jpg'))
        self.assertEqual(['theirs.txt'], os.listdir(elsewhere))

    def test_a_folder_of_other_files_is_not_taken_for_a_wordpress_site(self):
        self.pack(config=None, core=False)
        with self.assertRaisesRegex(BaseException, 'holds no WordPress files'):
            self.place('files')
        self.assertEqual(['kept.txt', 'wp-config.php'], sorted(os.listdir(self.site)))

    def test_a_truncated_archive_ends_the_restore_before_the_site_is_touched(self):
        self.pack()
        layout = self.installer.backupLayout(self.archive, 'both', FOLDER, 'sourcedb.sql')
        with open(self.archive, 'r+b') as handle:
            handle.truncate(os.path.getsize(self.archive) // 2)
        with self.assertRaisesRegex(BaseException, 'The backup file could not be unpacked'):
            self.installer.placeBackup(layout, self.archive, 'nobody', PHP, self.site + '/', ())
        self.assertEqual(['kept.txt', 'wp-config.php'], sorted(os.listdir(self.site)))

    def test_the_address_lines_are_found_in_the_packed_configuration(self):
        self.pack(config="<?php\ndefine( 'DB_NAME', 'x' );\ndefine('WP_HOME', 'https://source.example');\n")
        layout = self.installer.backupLayout(self.archive, 'both', FOLDER, 'sourcedb.sql')
        self.assertIn('fixes the address', self.installer.otherDomainRefusal(self.archive, layout))
        self.pack(config="<?php\ndefine( 'DB_NAME', 'x' );\n// define('WP_HOME', 'https://source.example');\n")
        self.assertIsNone(self.installer.otherDomainRefusal(self.archive, layout))


class CreatedWebsiteRemovalTests(Harness):
    def remove(self, reply, still_there=False, keep=()):
        self.process.outputExecutioner.side_effect = lambda command, retRequired=None: reply
        self.websites.objects.filter.return_value.exists.return_value = still_there
        return self.installer.removeCreatedWebsite("new.example", keep)

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

    def test_what_was_there_before_the_creation_is_named_to_the_deletion_as_kept(self):
        done = (1, 'WEBSITE_DELETE_RESULT={"completed": true}')
        self.assertEqual(REMOVED, self.remove(done, keep=('dns', 'ssl')))
        self.assertTrue(self.process.outputExecutioner.call_args[0][0].endswith(
            '--virtualHostName new.example --keep dns,ssl'))

    def test_the_domain_reaches_the_command_as_one_argument(self):
        self.process.outputExecutioner.side_effect = lambda command, retRequired=None: (1, '')
        self.installer.removeCreatedWebsite('new.example; touch /tmp/x', ())
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

    def test_what_a_failed_step_printed_reaches_the_status_as_one_short_line(self):
        self.replies['tar '] = (False, b''.join(b'tar: file%d: Cannot open: Permission denied\n' % number
                                                for number in range(5000)))
        with self.assertRaises(BaseException) as raised:
            self.installer.restoreStep('tar -xzf a', 'siteuser', 'The website files could not be copied')
        message = str(raised.exception)
        self.assertLess(len(message), 360)
        self.assertNotIn('\n', message)
        self.assertTrue(message.endswith('tar: file4999: Cannot open: Permission denied'), message)

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
        self.installer.foundBeforeCreation = mock.Mock(return_value=('dns', 'mail'))
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
        # The zone and the mail folder of that name were there before the
        # website: they are named to the removal as not this job's.
        self.installer.foundBeforeCreation.assert_called_once_with('new.example')
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example', ('dns', 'mail'))
        self.assertEqual('Failed to install WordPress: error: Warning: The package could not be installed. Your '
                         'WordPress version is 6.0, however the uploaded plugin requires 6.2. %s [404]' % REMOVED,
                         self.status_text())

    def test_what_a_creation_would_reuse_is_looked_for_before_the_website_is_created(self):
        self.website_is_new()
        calls = mock.Mock()
        calls.attach_mock(self.installer.foundBeforeCreation, 'look')
        calls.attach_mock(self.manager.submitWebsiteCreation, 'create')
        self.create()
        self.assertEqual(['look', 'create'], [call[0] for call in calls.mock_calls])

    def test_the_reason_a_website_could_not_be_created_reaches_the_last_line_of_the_status(self):
        # As the creating worker writes it: the reason, its marker, a line break.
        self.website_is_new('New SSL issuance failed. The existing self-signed certificate has been preserved. '
                            '[404]\n')
        self.assertEqual(0, self.create())
        self.assertEqual('Failed to Create Website: error: New SSL issuance failed. The existing self-signed '
                         'certificate has been preserved. [404]', self.status_text())
        self.installer.removeCreatedWebsite.assert_not_called()

    def test_a_multi_line_reason_of_the_installation_stays_on_the_one_line_that_is_shown(self):
        self.website_is_new()
        self.install_line = 'Warning: The package could not be installed.\nError: No plugins installed. [404]\n'
        self.assertEqual(0, self.create())
        self.assertEqual(1, len(self.status_text().splitlines()))
        self.assertTrue(self.status_text().startswith('Failed to install WordPress: error: Warning: The package '
                                                      'could not be installed. Error: No plugins installed. '))
        self.assertTrue(self.status_text().endswith('[404]'))

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
        self.installer.removeCreatedWebsite.assert_called_once_with('new.example', ('dns', 'mail'))
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
        self.assertEqual(2, live.count("'db', 'import'"))
        self.assertEqual(2, live.count('self.restoreToNewSite('))

    def test_no_restore_unpacks_an_archive_with_roots_rights(self):
        live = [line for line in SOURCE.splitlines() if not line.lstrip().startswith('#')]
        start = next(index for index, line in enumerate(live) if 'def backupLayout(self' in line)
        end = next(index for index, line in enumerate(live) if 'def UpdateDownloadStatus(self' in line)
        unpacking = [line for line in live[start:end] if 'tar -x' in line or 'tar -zx' in line]
        # One place unpacks, as the destination's account; one prints a
        # single file as the account without rights. Neither is root's.
        self.assertEqual(2, len(unpacking), unpacking)
        self.assertIn("unpack = 'tar -xzf %s --no-same-owner --no-same-permissions' % shlex.quote(archive)",
                      unpacking[1])
        self.assertIn('sudo -u nobody tar -xzOf - ', unpacking[0])
        body = '\n'.join(live[start:end])
        self.assertNotIn('sudo tar', body)
        self.assertEqual(2, body.count('ProcessUtilities.outputExecutioner(command, None, True)'))

    def test_every_restore_into_an_existing_site_keeps_that_sites_own_settings_through_the_copy(self):
        live = '\n'.join(self.restore_lines())
        self.assertEqual(3, live.count('self.placeBackup(layout, archive, VHuser, FinalPHPPath, '))
        self.assertEqual(1, live.count('ownSettings = self.siteDatabaseSettings(FinalPHPPath, newWPpath, VHuser, False)'))
        self.assertEqual(1, live.count('ownSettings = self.siteDatabaseSettings(FinalPHPPath, WPpath, VHuser, True)'))
        self.assertEqual(2, live.count(', ownSettings)'))
        self.assertFalse('cp -Rf' in live)

    def test_a_request_the_backup_cannot_serve_ends_before_the_download_and_the_archive_is_checked_first(self):
        live = '\n'.join(self.restore_lines())
        self.assertLess(live.index('restore_plan(BackupType, DesSiteID, DomainName)'), live.index('paramiko'))
        self.assertLess(live.index('layout = self.backupLayout(archive, backupKind, oldtemppath, DumpFileName)'),
                        live.index("if BackupType == 'DataBase Backup':"))

    def test_a_failed_download_falls_back_to_the_copy_kept_on_the_server(self):
        live = '\n'.join(self.restore_lines())
        failed = live.index('downloaded = False')
        self.assertLess(failed, live.index('if self.pathPresent(localArchive) is not True:', failed))
        self.assertLess(live.index('if self.pathPresent(localArchive) is not True:', failed),
                        live.index("raise BaseException('The backup could not be downloaded from the storage", failed))
        self.assertIn('if downloaded:\n                    command = "mv %s /home/backup/" % shlex.quote(FinalZipPath)',
                      live)

    def test_the_final_reason_is_written_as_one_line(self):
        live = '\n'.join(self.restore_lines())
        self.assertIn("logging.statusWriter(self.tempStatusPath, '%s. [404]' % ' '.join(str(msg).split()).rstrip('. '))",
                      live)

    def test_only_an_archive_this_job_downloaded_is_removed_and_never_by_an_unset_name(self):
        live = '\n'.join(self.restore_lines())
        self.assertNotIn('rm -rf /home/backup/', live)
        self.assertEqual(2, live.count("'rm -f %s' % shlex.quote(downloadedArchive)"))
        self.assertEqual(1, live.count('if not archiveWasHere:'))
        self.assertEqual(1, live.count('if not archiveWasHere and uploadfilename == BackUpFileName:'))
        # An unclear answer about a file of that name counts as "it was here".
        self.assertIn('archiveWasHere = self.pathPresent(localArchive) is not False', live)
        self.assertLess(live.index('archiveWasHere = '), live.index('paramiko'))


if __name__ == '__main__':
    unittest.main()
