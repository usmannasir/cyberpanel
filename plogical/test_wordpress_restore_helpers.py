"""The small decisions of a WordPress installation or restore, each on its own."""
import ast
import os
from pathlib import Path
import shlex
import sys
import types
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from plogical.websiteDeletion import REUSABLE, found_before_creation, kept_by_creation
from plogical.wordpressInstallerUtilities import (
    brief_output,
    build_directory_listing_command,
    build_entry_removal_command,
    current_wordpress_version,
    directory_entry_names,
    entries_added_since,
    out_of_quota,
    single_line_value,
    wordpress_cli_command,
    wordpress_table_prefix_command,
    worker_failure_reason,
)

ROOT = Path(__file__).resolve().parents[1]


class CurrentReleaseTests(unittest.TestCase):
    def fetch(self, payload):
        fetch = mock.Mock()
        fetch.return_value.json.return_value = payload
        return fetch

    def test_the_current_release_is_the_first_valid_one_wordpress_org_offers(self):
        fetch = self.fetch({'offers': [{'current': '7.1.5'}, {'current': '7.0.9'}]})
        self.assertEqual('7.1.5', current_wordpress_version(fetch))
        fetch.assert_called_once_with('https://api.wordpress.org/core/version-check/1.7/', timeout=15)
        fetch.return_value.raise_for_status.assert_called_once_with()

    def test_an_answer_without_a_release_is_an_error_and_never_a_default_version(self):
        for payload in ({'offers': []}, {'offers': [{'current': '6.0;id'}]}, {}, [], None, 'error'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    current_wordpress_version(self.fetch(payload))

    def test_a_failed_request_is_passed_on(self):
        fetch = self.fetch({'offers': [{'current': '7.1.5'}]})
        fetch.return_value.raise_for_status.side_effect = OSError('503')
        with self.assertRaises(OSError):
            current_wordpress_version(fetch)


class InstallDirectoryBookkeepingTests(unittest.TestCase):
    def test_the_listing_names_every_entry_of_the_directory_itself(self):
        command = build_directory_listing_command("/home/example site/public_html/it's-here")
        self.assertEqual(['find', "/home/example site/public_html/it's-here", '-mindepth', '1', '-maxdepth', '1',
                          '-printf', '%f\\n'], shlex.split(command))

    def test_a_listing_that_failed_is_no_reading(self):
        self.assertEqual({'a', '.b', 'c d'}, directory_entry_names(1, 'a\n.b\nc d\n'))
        self.assertEqual(set(), directory_entry_names(1, ''))
        self.assertIsNone(directory_entry_names(0, 'a\n'))
        self.assertIsNone(directory_entry_names(1, None))

    def test_only_what_was_not_there_before_counts_as_added(self):
        self.assertEqual(['index.php', 'wp-admin'], entries_added_since({'.well-known'}, {'.well-known', 'wp-admin',
                                                                                           'index.php'}))
        self.assertEqual([], entries_added_since({'a', 'b'}, {'a'}))

    def test_without_both_readings_nothing_counts_as_added(self):
        self.assertEqual([], entries_added_since(None, {'wp-admin'}))
        self.assertEqual([], entries_added_since({'a'}, None))

    def test_a_name_that_is_not_a_plain_entry_is_never_removed(self):
        self.assertEqual(['ok'], entries_added_since(set(), {'.', '..', "find: '/x/y': No such file", 'ok'}))
        for name in ('', '.', '..', 'a/b', '/etc', 'a\x00b', None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    build_entry_removal_command('/home/example.com/public_html', name)

    def test_a_removal_names_one_entry_inside_the_directory_and_no_option(self):
        for name in ('wp-admin', '-rf', "it's", 'a b', '$(id)', '*'):
            command = build_entry_removal_command('/home/example.com/public html/', name)
            self.assertEqual(['rm', '-rf', '--', '/home/example.com/public html/' + name], shlex.split(command))


class WordPressCliCommandTests(unittest.TestCase):
    PHP = '/usr/local/lsws/lsphp83/bin/php'

    def test_every_value_is_one_argument_and_no_plugin_or_theme_is_loaded(self):
        for value in ('source.example', 'a b', "it's", '$(id)', '`id`', 'x; rm -rf /', '"quoted"'):
            command = wordpress_cli_command(self.PHP, '/home/new.example/public_html/', 'search-replace', value,
                                            'new.example')
            self.assertEqual([self.PHP, '-d', 'error_reporting=0', '-d', 'memory_limit=350M', '-d',
                              'max_execution_time=400', '/usr/bin/wp', 'search-replace', value, 'new.example',
                              '--skip-plugins', '--skip-themes', '--path=/home/new.example/public_html/'],
                             shlex.split(command), repr(value))

    def test_the_table_prefix_is_a_plain_name(self):
        command = wordpress_table_prefix_command(self.PHP, '/home/x/public_html/', 'wp_7a_')
        self.assertIn(' config set table_prefix wp_7a_ --type=variable ', command)
        for prefix in ('', 'wp-', 'wp_; id', "wp_'", 'a' * 65, None, 7):
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    wordpress_table_prefix_command(self.PHP, '/home/x/public_html/', prefix)

    def test_a_value_is_exactly_one_line_of_output(self):
        self.assertEqual('newdb', single_line_value('newdb\n'))
        self.assertEqual(' p a$$ ', single_line_value(' p a$$ \n'))
        for output in ('', '\n', None, 'Warning: x\nnewdb\n', 'a\rb'):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    single_line_value(output)


class StatusTextTests(unittest.TestCase):
    def test_the_reason_of_a_failed_worker_is_one_line_without_its_end_marker(self):
        status = 'New SSL issuance failed. The existing self-signed certificate has been preserved. [404]\n'
        self.assertEqual('New SSL issuance failed. The existing self-signed certificate has been preserved',
                         worker_failure_reason(status))
        self.assertEqual('Directory is not empty', worker_failure_reason('Directory is not empty. [404]'))
        self.assertEqual('Warning: no fit. Error: No plugins installed',
                         worker_failure_reason('Warning: no fit.\nError: No plugins installed. [404]\n'))

    def test_a_worker_that_gave_no_reason_is_said_to_have_given_none(self):
        for status in ('', ' [404]\n', '. [404]', None):
            self.assertEqual('no reason was given', worker_failure_reason(status))

    def test_output_in_a_status_is_one_line_and_keeps_its_end_within_the_limit(self):
        self.assertEqual('a b c', brief_output('a\n b\t\tc\n'))
        self.assertEqual('', brief_output(None))
        long = '\n'.join('cp: cannot create regular file %d: Permission denied' % number for number in range(400))
        text = brief_output(long)
        self.assertEqual(304, len(text))
        self.assertTrue(text.startswith('... '))
        self.assertTrue(text.endswith('399: Permission denied'))
        self.assertNotIn('\n', text)
        self.assertEqual(24, len(brief_output('x' * 500, 20)))

    def test_a_used_up_quota_is_recognised_in_what_a_command_printed(self):
        self.assertTrue(out_of_quota("tar: wp-content/a.jpg: Cannot write: Disk quota exceeded\n"))
        self.assertFalse(out_of_quota('tar: Unexpected EOF in archive'))
        self.assertFalse(out_of_quota(None))


class ReusedByCreationTests(unittest.TestCase):
    def test_only_a_clear_no_makes_a_thing_the_creations_own(self):
        self.assertEqual((), found_before_creation(False, False, False))
        self.assertEqual(('dns',), found_before_creation(True, False, False))
        self.assertEqual(('dns', 'mail', 'ssl'), found_before_creation(True, True, True))
        self.assertEqual(('mail', 'ssl'), found_before_creation(False, None, mock.Mock()))
        self.assertEqual(REUSABLE, found_before_creation(None, None, None))

    def test_the_worker_takes_only_the_three_names(self):
        self.assertEqual(('dns', 'ssl'), kept_by_creation('ssl,dns'))
        self.assertEqual((), kept_by_creation(''))
        self.assertEqual((), kept_by_creation(None))
        self.assertEqual(('mail',), kept_by_creation('mail,website,../x, dns'))


class UndoneCreationTests(unittest.TestCase):
    """vhost.deleteVirtualHostConfigurations: what a creation only used is left when the creation is undone."""

    def setUp(self):
        self.events = []
        self.server = 'ols'
        self.site = NS(externalApp='fixtu1234', childdomains_set=NS(all=lambda: []),
                       delete=lambda: self.events.append('website-row'))
        process = NS(OLS='ols', centos='centos', cent8='cent8', decideServer=lambda: self.server,
                     decideDistro=lambda: 'ubuntu', normalExecutioner=lambda command: None)
        scope = {
            'ProcessUtilities': process,
            'Websites': NS(objects=NS(count=lambda: 1, get=lambda **kwargs: self.site)),
            'ChildDomains': NS(objects=NS(count=lambda: 0)),
            'Databases': NS(objects=NS(filter=lambda **kwargs: [NS(dbName='fixturedb', dbUser='fixturedb')])),
            'WPSites': NS(objects=NS(filter=lambda **kwargs: [])),
            'ACLManager': NS(FindIfChild=lambda: 0),
            'mysqlUtilities': NS(deleteDatabase=lambda *args: self.events.append('database') or 1),
            # The deletion also has the pattern forwarding map rebuilt; that is not what is looked at here.
            'patternForwardingMap': NS(rebuild_after_removal=lambda: None),
            'DNS': NS(deleteDNSZone=lambda domain: self.events.append('dns-zone:' + domain) or 1),
            'installUtilities': NS(installUtilities=NS(reStartLiteSpeed=lambda: None)),
            'os': NS(path=NS(exists=lambda path: path == '/root/.acme.sh/fixture.test')),
            'shutil': NS(rmtree=lambda path: self.events.append('removed:' + path)),
            'subprocess': NS(call=lambda argv: self.events.append(' '.join(argv)) or 0),
            'shlex': shlex,
            'logging': NS(CyberCPLogFileWriter=NS(writeToFile=lambda message: self.events.append('log:' + message))),
        }
        tree = ast.parse((ROOT / 'plogical/vhost.py').read_text())
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'vhost')
        method = next(node for node in owner.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'deleteVirtualHostConfigurations')
        method.decorator_list = []
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'vhost.py', 'exec'), scope)
        scope['vhost'] = NS(redisConf='/no/redis', deleteCoreConf=lambda domain, count: 1,
                            _delete_unix_account=lambda user, command: self.events.append('account:' + user))
        self.delete = scope['deleteVirtualHostConfigurations']
        limits = types.ModuleType('plogical.resourceLimits')
        limits.resource_manager = NS(remove_user_limits=lambda user: None)
        patcher = mock.patch.dict(sys.modules, {'plogical.resourceLimits': limits})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_deletion(self, *arguments):
        self.events = []
        self.assertEqual(1, self.delete('fixture.test', *arguments), self.events)
        return self.events

    def test_the_deletion_of_a_website_removes_its_zone_mail_and_certificate_folder(self):
        for server in ('ols', 'lsws'):
            self.server = server
            events = self.run_deletion()
            self.assertIn('dns-zone:fixture.test', events)
            self.assertIn('rm -rf /home/vmail/fixture.test', events)
            self.assertIn('website-row', events)
        self.server = 'ols'
        self.assertIn('removed:/root/.acme.sh/fixture.test', self.run_deletion())

    def test_a_zone_that_was_there_before_the_creation_outlives_its_undoing(self):
        for server in ('ols', 'lsws'):
            self.server = server
            events = self.run_deletion(('dns',))
            self.assertFalse([event for event in events if event.startswith('dns-zone')], events)
            self.assertIn('rm -rf /home/vmail/fixture.test', events)
            # Everything the creation did make still goes.
            self.assertIn('database', events)
            self.assertIn('website-row', events)
            self.assertIn('account:fixtu1234', events)

    def test_a_mail_folder_and_a_certificate_folder_that_were_there_stay_too(self):
        for server in ('ols', 'lsws'):
            self.server = server
            events = self.run_deletion(REUSABLE)
            self.assertEqual(['database', 'website-row', 'account:fixtu1234'], events)

    def test_the_worker_passes_on_what_the_job_asked_it_to_keep(self):
        source = (ROOT / 'plogical/virtualHostUtilities.py').read_text()
        self.assertIn("vhost.deleteVirtualHostConfigurations(\n            args.virtualHostName, "
                      "kept_by_creation(args.keep)) == 1", source)
        self.assertIn("parser.add_argument('--keep',", source)

    def test_a_creation_that_fails_leaves_what_it_found_and_everything_until_it_has_looked(self):
        source = (ROOT / 'plogical/virtualHostUtilities.py').read_text()
        start = source.index('    def createVirtualHost(')
        body = source[start:source.index('    def issueSSL(', start)]
        self.assertLess(body.index('keep = REUSABLE'), body.index("'Running some checks..,0'"))
        self.assertLess(body.index('keep = found_before_creation(DNS.zoneExists(virtualHostName),'),
                        body.index('DNS.dnsTemplate(virtualHostName, admin)'))
        self.assertIn('vhost.deleteVirtualHostConfigurations(virtualHostName, keep)', body)
        self.assertEqual(1, body.count('vhost.deleteVirtualHostConfigurations('))


if __name__ == '__main__':
    unittest.main()
