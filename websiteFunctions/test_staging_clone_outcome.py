"""The website Clone/Staging job ends with a true status: success for a working copy, a reason otherwise.

Commands are answered by fakes; nothing here runs WP-CLI, touches a
database or writes outside a temporary folder.
"""
import ast
import json
import os
import re
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import tempfile
import threading
import types
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from websiteFunctions.stagingClone import CloneFailed, StagingCopy, import_failure, step_failure


ROOT = Path(__file__).resolve().parents[1]
PROCESS_NOTE = ("mysqldump: Error: 'Access denied; you need (at least one of) the PROCESS privilege(s) "
                "for this operation' when trying to dump tablespaces")


def answer(command):
    """What a healthy site and a healthy server print for each command of a clone."""
    if ' core version ' in command:
        return 1, '6.8.3\n'
    if 'config get table_prefix' in command:
        return 1, 'wpq_\n'
    if ' theme path ' in command:
        # A cache drop-in of the site prints a line of its own first.
        return 1, 'CyberEdge cache: page cache needs WordPress 6.2 or later\n/home/live.example/public_html/wp-content/themes\n'
    if ' core download ' in command:
        return 1, 'Downloading WordPress 6.8.3 (en_US)...\nSuccess: WordPress downloaded.\n'
    if ' core config ' in command:
        return 1, "Success: Generated 'wp-config.php' file.\n"
    if ' config set ' in command:
        return 1, "Success: Updated the constant in the 'wp-config.php' file.\n"
    if ' db export ' in command:
        return 1, PROCESS_NOTE + "\nSuccess: Exported to '/home/live.example/.staging.sql'.\n"
    if ' db import ' in command:
        return 1, "Success: Imported from '/home/live.example/.staging.sql'.\n"
    if ' search-replace ' in command:
        return 1, 'Warning: unserialize() error in a row.\nSuccess: Made 4 replacements.\n'
    if ' core is-installed ' in command:
        return 1, ''
    if ' option get siteurl ' in command:
        return 1, 'http://stage.live.example\n'
    return 1, ''


def unquoted(command):
    try:
        return ' %s ' % ' '.join(shlex.split(command))
    except ValueError:
        return command


class FakeSite(object):
    def __init__(self, **overrides):
        self.calls = []
        self.overrides = overrides

    def __call__(self, command, user='liveuser', withErrors=True):
        self.calls.append((command, user))
        plain = unquoted(command)
        for marker, result in self.overrides.items():
            if marker in plain:
                return result
        return answer(plain)

    def ran(self, marker):
        return [command for command, _ in self.calls if marker in unquoted(command)]


def as_site_user(site):
    """The runner StagingSetup hands to StagingCopy: commands of the website's own user."""
    return lambda command, withErrors=True: site(command, 'liveuser', withErrors)


class StepRuleTests(unittest.TestCase):
    def test_remarks_beside_a_successful_result_are_no_failure(self):
        for output in (PROCESS_NOTE + "\nSuccess: Exported to 'x.sql'.",
                       'Warning: Some code is trying to do a URL redirect.\nSuccess: Made 0 replacements.',
                       'PHP Deprecated:  Creation of dynamic property is deprecated\nSuccess: done.', ''):
            self.assertIsNone(step_failure(1, output), output)

    def test_an_exit_status_or_an_error_of_wp_cli_is_a_failure_with_its_reason(self):
        self.assertEqual("Error: Error establishing a database connection.",
                         step_failure(0, "Error: Error establishing a database connection.\n"))
        self.assertEqual('Error: This does not seem to be a WordPress installation.',
                         step_failure(1, 'Error: This does not seem to be a WordPress installation.'))
        self.assertEqual('the command failed', step_failure(0, ''))
        self.assertEqual('the disk quota of this website is used up',
                         step_failure(0, "cp: error writing 'x': Disk quota exceeded"))

    def test_an_import_that_the_database_refused_is_a_failure_although_it_says_success(self):
        output = "ERROR 1064 (42000) at line 9 in file: 'x.sql': You have an error\nSuccess: Imported from 'x.sql'."
        self.assertIn('ERROR 1064', import_failure(1, output))
        self.assertIsNone(import_failure(1, "Success: Imported from 'x.sql'."))


class StagingCopyTests(unittest.TestCase):
    def setUp(self):
        self.statuses = []
        self.database = ('stagedb', 'stagedb', "p'w", 'localhost:3306')

    def copy(self, site):
        copy = StagingCopy(as_site_user(site), self.statuses.append)
        facts = copy.read_source('/usr/local/lsws/lsphp82/bin/php', '/home/live.example/public_html')
        copy.run('/usr/local/lsws/lsphp82/bin/php', '/home/live.example/public_html', facts,
                 '/home/live.example/stage.live.example', self.database, '/home/live.example/.staging-1.sql',
                 'live.example', 'stage.live.example')
        return facts

    def test_a_healthy_clone_succeeds_as_the_site_user_with_the_source_version_and_prefix(self):
        site = FakeSite()
        facts = self.copy(site)
        self.assertEqual({'version': '6.8.3', 'prefix': 'wpq_', 'content': '/home/live.example/public_html/wp-content'},
                         facts)
        self.assertEqual({'liveuser'}, set(user for _, user in site.calls))
        self.assertTrue(site.ran(' core download --version=6.8.3 --skip-content '))
        self.assertTrue(site.ran(' config set table_prefix wpq_ --type=variable '))
        self.assertTrue(site.ran(' db export /home/live.example/.staging-1.sql --single-transaction '
                                 '--skip-plugins --skip-themes --path=/home/live.example/public_html '))
        self.assertTrue(site.ran(' cp -R -- /home/live.example/public_html/wp-content/. '
                                 '/home/live.example/stage.live.example/wp-content/ '))
        self.assertEqual(3, len(site.ran(' search-replace ')))
        self.assertFalse([command for command, _ in site.calls if '--allow-root' in command])

    def test_a_failed_step_that_the_copy_needs_stops_it_with_the_step_and_its_reason(self):
        cases = (
            ({' db import ': (1, "ERROR 1146 (42S02) at line 3: Table 'x' doesn't exist\nSuccess: Imported.")},
             'The database could not be imported: ERROR 1146'),
            ({' db export ': (0, 'mysqldump: Got error: 1045: Access denied for user')},
             'The database of the site could not be exported: mysqldump: Got error: 1045'),
            ({' cp -R ': (0, "cp: cannot open 'wp-content/uploads/a.jpg' for reading: Permission denied")},
             'The themes, plugins and uploads of the site could not be copied: cp: cannot open'),
            ({' core download ': (1, 'Error: Release not found.')}, 'WordPress could not be downloaded: Error'),
            ({' option get siteurl ': (1, 'https://live.example\n')},
             'The copy answers under the address "https://live.example" instead of under stage.live.example'),
            ({' core is-installed ': (0, '')}, 'The copy does not start with its database'),
        )
        for overrides, message in cases:
            with self.assertRaises(CloneFailed) as raised:
                self.copy(FakeSite(**overrides))
            self.assertTrue(str(raised.exception).startswith(message), str(raised.exception))

    def test_the_source_is_read_before_anything_is_created_and_must_make_sense(self):
        for overrides, message in (
                ({' core version ': (1, 'PHP Warning: x\n6.8.3\n')}, 'The WordPress version of the site could not'),
                ({' theme path ': (1, 'Fatal error in a drop-in\n')}, 'The content folder of the site could not'),
                ({'config get table_prefix': (0, '')}, 'The table prefix of the site could not')):
            site = FakeSite(**overrides)
            with self.assertRaises(CloneFailed) as raised:
                StagingCopy(as_site_user(site), self.statuses.append).read_source('/php', '/home/live.example/public_html')
            self.assertTrue(str(raised.exception).startswith(message), str(raised.exception))

    def test_a_version_that_cannot_be_downloaded_falls_back_to_the_latest_release_with_a_note(self):
        for version, failure in (('6.9-alpha-60123-src', {' core download --version=': (1, 'Error: Release not found.')}),
                                 ("6.8'; rm -rf /", {})):
            site = FakeSite(**dict(failure, **{' core version ': (1, version + '\n')}))
            copy = StagingCopy(as_site_user(site), self.statuses.append)
            facts = copy.read_source('/php', '/home/live.example/public_html')
            notes = copy.run('/php', '/home/live.example/public_html', facts, '/home/live.example/stage.live.example',
                             self.database, '/home/live.example/.staging-1.sql', 'live.example', 'stage.live.example')
            self.assertEqual(1, len(notes))
            self.assertTrue(notes[0].startswith('WordPress %s of the site could not be downloaded (' % version), notes)
            self.assertTrue(notes[0].endswith('the copy runs the latest release'), notes)
            self.assertTrue(site.ran(' core download --skip-content --force '))
            self.assertEqual(bool(failure), bool(site.ran(' core download --version=')))

    def test_a_release_the_site_runs_is_downloaded_without_a_note(self):
        for version in ('6.8.3', '6.9-RC1', '6.9-beta2'):
            site = FakeSite(**{' core version ': (1, version + '\n')})
            copy = StagingCopy(as_site_user(site), self.statuses.append)
            facts = copy.read_source('/php', '/home/live.example/public_html')
            self.assertEqual([], copy.run('/php', '/home/live.example/public_html', facts,
                                          '/home/live.example/stage.live.example', self.database,
                                          '/home/live.example/.staging-1.sql', 'live.example', 'stage.live.example'))
            self.assertTrue(site.ran(' core download --version=%s --skip-content ' % version))
            self.assertFalse(site.ran(' --force '))

    def test_the_dump_is_written_for_the_site_user_alone(self):
        site = FakeSite()
        self.copy(site)
        self.assertTrue(site.ran(' db export ')[0].startswith('umask 077 && '))

    def test_an_htaccess_that_the_site_does_not_have_is_skipped_by_the_shell_not_failed(self):
        site = FakeSite()
        self.copy(site)
        command = site.ran('.htaccess')[0]
        self.assertTrue(command.startswith('if [ -e /home/live.example/public_html/.htaccess ]; then cp -f -- '))


def staging_class(namespace):
    tree = ast.parse((ROOT / 'websiteFunctions/StagingSetup.py').read_text())
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'StagingSetup')
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'StagingSetup.py', 'exec'), namespace)
    return namespace['StagingSetup']


class StagingJobTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.status = os.path.join(scratch.name, '42')
        self.site = FakeSite()
        self.website = NS(domain='live.example', externalApp='liveuser', phpSelection='PHP 8.2')
        self.domains = []
        self.createResult = 'Domain successfully created. [200]\n'
        self.present = False
        self.dropped = mock.Mock(return_value=1)
        self.registry = mock.Mock()
        self.events = []
        self.permissions = mock.Mock(side_effect=lambda domain: self.events.append('repair %s' % domain))
        self.deployment = None
        self.childRemoval = mock.Mock(return_value='The domain stage.live.example that was created for this job '
                                                   'has been removed again.')

        test = self

        class Installer(object):
            LOCALHOST = 'localhost'
            PORT = '3306'
            @staticmethod
            def siteCommand(command, user, withErrors=True):
                test.events.append(command)
                return test.site(command, user, withErrors)

            def __init__(self, *args):
                pass

            def installWPCLI(self):
                pass

            def pathPresent(self, path, kind=None):
                return test.present

            def foundBeforeCreation(self, domain):
                return ('ssl',)

            def dbCreation(self, statusPath, website):
                return ('stagedb', 'stagedb', 'secret')

            def removeCreatedChildDomain(self, domain, keep):
                return test.childRemoval(domain, keep)

        def executioner(command, user=None):
            self.domains.append(command)
            with open(self.status + '1', 'w') as status:
                status.write(self.createResult)
            return 1

        def outputExecutioner(command, user=None):
            self.rootCommands.append(command)
            return 'WP-CLI root dir: phar://wp-cli.phar'

        self.rootCommands = []

        def deployment(owner):
            if self.deployment is None:
                raise LookupError('no WordPress Manager record')
            return NS(config=json.dumps(self.deployment))
        models = types.ModuleType('cloudAPI.models')
        models.WPDeployments = NS(objects=NS(get=deployment))

        def statusWriter(path, message, append=None):
            with open(path, 'w') as status:
                status.write(message + '\n')

        empty = NS(exists=lambda: False)
        stubs = {'managePHP.phpManager': NS(PHPManager=NS(getPHPString=lambda selection: '82')),
                 'cloudAPI.models': models,
                 'filemanager.filemanager': NS(FileManager=lambda *args: NS(fixPermissions=self.permissions)),
                 'plogical.installUtilities': NS(installUtilities=NS(reStartLiteSpeed=mock.Mock())),
                 'databases.models': NS(Databases=NS(objects=NS(filter=self.registry)))}
        patcher = mock.patch.dict(sys.modules, stubs)
        patcher.start()
        self.addCleanup(patcher.stop)
        from plogical.wordpressInstallerUtilities import brief_output, worker_failure_reason
        from websiteFunctions.wordpressRestore import validate_restore_path
        namespace = {
            'multi': threading, 'shlex': shlex, 'subprocess': subprocess, 'os': os, 'secrets': secrets,
            'logging': NS(statusWriter=statusWriter, writeToFile=mock.Mock()),
            'virtualHostUtilities': NS(cyberPanel='/usr/local/CyberCP'),
            'ProcessUtilities': NS(executioner=executioner, outputExecutioner=outputExecutioner),
            'Websites': NS(objects=NS(get=lambda domain: self.website, filter=lambda domain: empty)),
            'ChildDomains': NS(objects=NS(filter=lambda domain: empty)),
            'ApplicationInstaller': Installer, 'mysqlUtilities': NS(deleteDatabase=self.dropped),
            'stored_php_selection': lambda value: value, 'StagingCopy': StagingCopy,
            'worker_failure_reason': worker_failure_reason, 'brief_output': brief_output,
            'validate_restore_path': validate_restore_path}
        self.job = staging_class(namespace)('startCloning', {
            'tempStatusPath': self.status, 'masterDomain': 'live.example', 'domain': 'stage.live.example',
            'admin': NS(userName='admin')})

    def finalStatus(self):
        self.job.startCloning()
        with open(self.status) as status:
            return status.read().splitlines()[-1]

    def test_a_working_clone_ends_with_success(self):
        self.assertEqual('Completed,[200]', self.finalStatus())
        self.dropped.assert_not_called()
        self.childRemoval.assert_not_called()
        # The database passed through a file outside every document root, removed afterwards.
        removal = [command for command, _ in self.site.calls if command.startswith('rm -f -- /home/live.example/.staging-')]
        self.assertEqual(1, len(removal))
        # Nothing of the site is read or run as root apart from the WP-CLI check.
        self.assertEqual(['wp --info'], self.rootCommands)

    def test_the_site_is_repaired_before_its_files_are_copied(self):
        self.assertEqual('Completed,[200]', self.finalStatus())
        repair = self.events.index('repair live.example')
        copy = next(i for i, event in enumerate(self.events) if ' cp -R ' in unquoted(event))
        self.assertLess(repair, copy)

    def test_a_permission_repair_that_fails_is_no_failure_and_the_copy_names_what_it_could_not_read(self):
        self.permissions.side_effect = RuntimeError('Permission repair failed. Check the panel log before retrying.')
        self.assertEqual('Completed,[200]', self.finalStatus())
        self.childRemoval.assert_not_called()
        self.permissions.side_effect = RuntimeError('Permission repair failed.')
        self.site = FakeSite(**{' cp -R ': (0, "cp: cannot open '/home/live.example/public_html/wp-content/"
                                                "uploads/old.sql' for reading: Permission denied")})
        final = self.finalStatus()
        self.assertIn("could not be copied: cp: cannot open '/home/live.example/public_html/wp-content/uploads/"
                      "old.sql' for reading: Permission denied.", final)

    def test_a_stale_dump_of_a_stopped_clone_is_removed_by_the_next_one(self):
        self.finalStatus()
        sweep = [event for event in self.events if event.startswith('find ')]
        self.assertEqual(["find /home/live.example -maxdepth 1 -regextype posix-extended -type f -regex "
                          "'/home/live\\.example/\\.staging-[0-9a-f]{32}\\.sql' -mmin +1440 -delete"], sweep)
        pattern = re.compile(shlex.split(sweep[0])[9].replace('\\.', '[.]'))
        self.assertTrue(pattern.fullmatch('/home/live.example/.staging-%s.sql' % ('ab12' * 8)))
        for other in ('/home/live.example/.staging-ab12.sql', '/home/live.example/staging-%s.sql' % ('ab12' * 8),
                      '/home/live.example/.staging-%s.sql.bak' % ('ab12' * 8), '/home/live.example/db.sql'):
            self.assertIsNone(pattern.fullmatch(other), other)

    def test_a_version_that_cannot_be_downloaded_is_named_in_the_final_status(self):
        self.site = FakeSite(**{' core version ': (1, '6.9-alpha-60123-src\n'),
                                ' core download --version=': (1, 'Error: Release not found.')})
        final = self.finalStatus()
        self.assertTrue(final.startswith('Completed. Note: WordPress 6.9-alpha-60123-src of the site could not '
                                         'be downloaded ('), final)
        self.assertTrue(final.endswith('the copy runs the latest release.,[200]'), final)

    def test_a_wordpress_folder_recorded_for_the_site_is_used_when_it_is_plain(self):
        self.deployment = {'path': 'blog'}
        self.assertEqual('Completed,[200]', self.finalStatus())
        self.assertTrue(self.site.ran(' test -f /home/live.example/public_html/blog/wp-config.php '))
        self.assertTrue(self.site.ran(' search-replace live.example/blog stage.live.example '))

    def test_a_recorded_folder_that_leaves_the_document_root_or_carries_shell_text_is_refused(self):
        for recorded in ('../../etc', '/etc', 'blog;id', 'blog$(id)', 'a b', 'blog/../..', 'x\n'):
            self.deployment = {'path': recorded}
            self.site = FakeSite()
            self.events[:] = []
            final = self.finalStatus()
            self.assertTrue(final.startswith('The WordPress folder recorded for live.example is not a folder '
                                             'inside its document root'), (recorded, final))
            self.assertEqual([], self.site.calls)
            self.assertEqual([], self.domains)

    def test_a_failure_after_creation_removes_this_jobs_domain_and_database_and_says_so(self):
        self.site = FakeSite(**{' db import ': (1, "ERROR 1064 (42000) at line 1: syntax\nSuccess: Imported.")})
        final = self.finalStatus()
        self.assertTrue(final.startswith('The database could not be imported: ERROR 1064 (42000) at line 1: syntax.'), final)
        self.assertTrue(final.endswith('The domain stage.live.example that was created for this job has been '
                                       'removed again. [404]'), final)
        self.dropped.assert_called_once_with('stagedb', 'stagedb')
        self.registry.assert_called_once_with(dbName='stagedb')
        self.childRemoval.assert_called_once_with('stage.live.example', ('ssl',))
        self.assertTrue([command for command, _ in self.site.calls if command.startswith('rm -f -- /home/live.example/.staging-')])

    def test_a_database_that_cannot_be_removed_is_named_in_the_status(self):
        self.site = FakeSite(**{' search-replace ': (0, 'Error: Database connection lost.')})
        self.dropped.return_value = 'could not connect'
        final = self.finalStatus()
        self.assertIn('The database stagedb that was created for this job could not be removed; '
                      'delete it under Databases.', final)
        self.registry.assert_not_called()
        self.assertTrue(final.endswith('[404]'))

    def test_a_site_that_cannot_be_read_creates_nothing(self):
        self.site = FakeSite(**{' theme path ': (0, '')})
        final = self.finalStatus()
        self.assertTrue(final.startswith('The content folder of the site could not be found'), final)
        self.assertEqual([], self.domains)
        self.childRemoval.assert_not_called()
        self.dropped.assert_not_called()

    def test_a_folder_that_is_already_there_is_refused_and_left_alone(self):
        self.present = True
        final = self.finalStatus()
        self.assertEqual('The folder /home/live.example/stage.live.example already exists; choose another name '
                         'for the staging site. [404]', final)
        self.assertEqual([], self.domains)
        self.assertFalse(self.site.ran('rmdir'))

    def test_a_refused_domain_creation_passes_its_reason_on_and_removes_only_an_empty_folder(self):
        self.createResult = 'Exceeded maximum number of domains for this package. [404]\n'
        final = self.finalStatus()
        self.assertEqual('Failed to create child-domain for staging environment: Exceeded maximum number of '
                         'domains for this package. [404]', final)
        self.assertEqual(['rmdir -- /home/live.example/stage.live.example'],
                         [command for command, _ in self.site.calls if command.startswith('rmdir')])
        self.childRemoval.assert_not_called()

    def test_a_site_without_wordpress_is_still_refused_as_before(self):
        self.site = FakeSite(**{' test -f ': (0, '')})
        self.assertEqual('WordPress is not detected. [404]', self.finalStatus())
        self.assertEqual([], self.domains)
        self.assertEqual(["test -f /home/live.example/public_html/wp-config.php"],
                         [command for command, _ in self.site.calls])


def method(path, cls, name):
    tree = ast.parse(path.read_text())
    holder = next(item for item in ast.walk(tree) if isinstance(item, ast.ClassDef) and item.name == cls)
    return next(item for item in holder.body if isinstance(item, ast.FunctionDef) and item.name == name)


class ChildDomainRemovalTests(unittest.TestCase):
    def setUp(self):
        self.execute = mock.Mock(return_value=(1, 'restarting\n1,None\n'))
        self.left = mock.Mock(return_value=False)
        node = method(ROOT / 'plogical/applicationInstaller.py', 'ApplicationInstaller', 'removeCreatedChildDomain')
        namespace = {'shlex': shlex, 'ProcessUtilities': NS(outputExecutioner=self.execute),
                     'ChildDomains': NS(objects=NS(filter=lambda domain: NS(exists=self.left))),
                     'logging': NS(writeToFile=mock.Mock())}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'applicationInstaller.py', 'exec'), namespace)
        self.remove = namespace['removeCreatedChildDomain']

    def test_removes_the_domain_with_its_folder_and_keeps_what_was_found(self):
        sentence = self.remove(None, 'stage.live.example', ('ssl',))
        command = self.execute.call_args[0][0]
        self.assertIn(' deleteDomain --virtualHostName stage.live.example --DeleteDocRoot 1 --keep ssl', command)
        self.assertEqual('The domain stage.live.example that was created for this job has been removed again.',
                         sentence)

    def test_a_removal_that_is_not_confirmed_says_so(self):
        for result, left in (((1, '0,Could not remove the child domain configuration.'), False),
                             ((0, ''), False), ((1, '1,None'), True)):
            self.execute.return_value = result
            self.left.return_value = left
            self.assertIn('could not be removed; delete it under Sub/Addon Domains',
                          self.remove(None, 'stage.live.example', ()))


class DeleteDomainKeepTests(unittest.TestCase):
    def run_deletion(self, keep):
        node = method(ROOT / 'plogical/virtualHostUtilities.py', 'virtualHostUtilities', 'deleteDomain')
        node.decorator_list = []
        ssl = mock.Mock()
        child = NS(path='/home/live.example/stage.live.example', delete=mock.Mock())
        namespace = {'Websites': NS(objects=NS(count=lambda: 1)), 'ChildDomains': NS(objects=NS(count=lambda: 1,
                                                                                            get=lambda domain: child)),
                     'vhost': NS(deleteCoreConf=lambda name, count: 1), 'shlex': shlex,
                     'ProcessUtilities': NS(outputExecutioner=mock.Mock(return_value=(1, ''))),
                     'patternForwardingMap': NS(rebuild_after_removal=mock.Mock()),
                     'installUtilities': NS(installUtilities=NS(reStartLiteSpeed=mock.Mock())),
                     'sslUtilities': NS(removeSSLForDomain=ssl), 'logging': NS(CyberCPLogFileWriter=mock.Mock()),
                     'print': lambda *args: None}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'virtualHostUtilities.py', 'exec'), namespace)
        arguments = ('stage.live.example', 1) if keep is None else ('stage.live.example', 1, keep)
        self.assertEqual((1, 'None'), namespace['deleteDomain'](*arguments))
        return ssl

    def test_a_certificate_folder_found_before_the_creation_stays(self):
        self.run_deletion(('ssl',)).assert_not_called()

    def test_an_ordinary_deletion_still_removes_the_certificate(self):
        self.run_deletion(None).assert_called_once_with('stage.live.example')
        self.run_deletion(('dns', 'mail')).assert_called_once_with('stage.live.example')


if __name__ == '__main__':
    unittest.main()
