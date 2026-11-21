"""The privileged workers check a PHP selection themselves before they do anything with it."""
import os
import shlex
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.test_php_selection import NOT_A_SELECTION
from plogical.test_php_restart_marker import ENTERPRISE, OLS, PHPChange, load_methods

VHOST = '/usr/local/lsws/conf/vhosts/example.test/vhost.conf'
WORKER = 'plogical/virtualHostUtilities.py'


class PHPChangeWorkerTests(unittest.TestCase):
    def change(self, server, **options):
        change = PHPChange(server, **options)
        self.addCleanup(change.close)
        return change

    def test_anything_but_a_selection_is_refused_before_any_lookup_file_or_command(self):
        for server in (OLS, ENTERPRISE):
            change = self.change(server)
            change.namespace['Websites'] = change.namespace['ChildDomains'] = mock.Mock()
            for value in NOT_A_SELECTION:
                with self.subTest(server=server, value=value):
                    result, output = change.run(VHOST, value)
                    self.assertEqual(0, result[0])
                    self.assertIn('Invalid PHP version selected.', result[1])
                    self.assertNotIn('1,None', output)
            self.assertEqual([], change.events)
            self.assertEqual([], change.opened)
            self.assertEqual([], change.namespace['Websites'].mock_calls)
            self.assertEqual([], change.process.mock_calls)

    def test_enterprise_record_gets_the_version_number_built_from_the_digits(self):
        change = self.change(ENTERPRISE, redis=True)
        result, output = change.run(VHOST, 'PHP 8.3')
        self.assertEqual((1, 'None'), tuple(result), output)
        self.assertEqual(['redis-cli set vhost:example.test \'{"phpVersion": 8.3, "uid": 1001}\''], change.events)


class CreationWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='php-worker-test-')
        self.addCleanup(self.temp.cleanup)
        os.mkdir(os.path.join(self.temp.name, 'conf'))
        self.logging = mock.Mock()
        self.inner = NS(Server_root=self.temp.name, _createDomain=mock.Mock(return_value=(1, 'None')),
                        _switchServer=mock.Mock(return_value=None))
        self.namespace = dict(logging=self.logging, virtualHostUtilities=self.inner,
                              Administrator=mock.Mock(), vhost=mock.Mock(), ACLManager=mock.Mock())
        self.create_site, self.create_domain, self.switch = load_methods(
            WORKER, 'virtualHostUtilities', ['createVirtualHost', 'createDomain', 'switchServer'], self.namespace)

    def status(self):
        return self.logging.CyberCPLogFileWriter.statusWriter.call_args[0][1]

    def test_website_creation_is_refused_before_the_block_that_removes_a_configuration(self):
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                result = self.create_site('example.test', 'owner@example.test', value, 'siteuser', 1, 1, 0,
                                          'admin', 'Default', 0, '/home/cyberpanel/status')
                self.assertEqual((0, 'Invalid PHP version selected.'), result)
                self.assertEqual('Invalid PHP version selected. [404]', self.status())
        # The error handler of the creation itself deletes the named
        # website's configuration; a refused request must not reach it.
        self.assertEqual([], self.namespace['vhost'].mock_calls)
        self.assertEqual([], self.namespace['Administrator'].mock_calls)
        self.assertEqual([], self.namespace['ACLManager'].mock_calls)

    def test_child_domain_creation_is_refused_before_the_worker_body(self):
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                result = self.create_domain('example.test', 'shop.example.test', value, '/home/example.test/shop',
                                            1, 0, 0, 'admin', 0, '/home/cyberpanel/status')
                self.assertEqual((0, 'Invalid PHP version selected.'), result)
                self.assertIn('Invalid PHP version selected.', self.status())
        self.inner._createDomain.assert_not_called()

    def test_child_domain_creation_passes_a_selection_on_unchanged(self):
        result = self.create_domain('example.test', 'shop.example.test', 'PHP 8.10', '/home/example.test/shop',
                                    1, 0, 0, 'admin', 0, '/home/cyberpanel/status')
        self.assertEqual((1, 'None'), result)
        self.assertEqual('PHP 8.10', self.inner._createDomain.call_args[0][2])

    def test_server_switch_is_refused_before_the_worker_body(self):
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                self.switch('example.test', value, 1, '/home/cyberpanel/status')
                self.assertEqual('Invalid PHP version selected.[404]', self.status())
        self.inner._switchServer.assert_not_called()

    def test_server_switch_passes_a_selection_on_unchanged(self):
        self.switch('example.test', 'PHP 7.4', 1, '/home/cyberpanel/status')
        self.inner._switchServer.assert_called_once_with('example.test', 'PHP 7.4', 1, '/home/cyberpanel/status')


class WorkerCommandLineTests(unittest.TestCase):
    def test_no_worker_command_carries_a_hand_quoted_php_version(self):
        from plogical.test_php_restart_marker import ROOT
        import re
        accepted = re.compile(r"""--phpVersion (?:" \+ shlex\.quote\(|'PHP [0-9]\.[0-9]' )""")
        found = 0
        for source in sorted(ROOT.rglob('*.py')):
            relative = source.relative_to(ROOT).as_posix()
            if '/test_' in '/' + relative or relative.startswith(('cli/', 'static/', 'public/')):
                continue
            for number, line in enumerate(source.read_text(errors='replace').splitlines(), 1):
                if '--phpVersion' in line and 'add_argument' not in line:
                    found += 1
                    self.assertRegex(line, accepted, '%s:%s' % (relative, number))
        self.assertGreaterEqual(found, 9)

    def test_quoted_selection_is_one_word_of_the_worker_command(self):
        for value in ('PHP 8.3', "PHP 8.3' --apache '1", 'PHP 8.3 --apache 1', 'PHP 8.3; id', 'PHP $(id)'):
            words = shlex.split('worker changePHP --phpVersion ' + shlex.quote(value) + ' --path /x')
            self.assertEqual(['worker', 'changePHP', '--phpVersion', value, '--path', '/x'], words)


if __name__ == '__main__':
    unittest.main()
