"""open_basedir protection is changed only for a website of this server and only to one of two words."""
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from plogical.test_php_restart_marker import load_methods
from websiteFunctions.test_stored_domain_name import NOT_A_DOMAIN, OLDER_NAMES, UNSAFE_STORED_NAME, prepared_manager

NOT_A_CHOICE = ('Enable --virtualHostName other.example', 'Enable;id', 'enable', 'Enabled', 'Enable ', '1', '',
                None, True, ['Enable'], {'Enable': 1})


class OpenBasedirRequestTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services, _, _ = prepared_manager()
        self.process = self.services['ProcessUtilities']

    def change(self, domain='owned.example', value='Enable'):
        self.process.reset_mock()
        return json.loads(self.manager().changeOpenBasedir(
            7, {'domainName': domain, 'openBasedirValue': value}).content)

    def commands(self):
        return [call[0][0] for call in self.process.popenExecutioner.call_args_list]

    def test_worker_gets_the_stored_name_and_the_chosen_word(self):
        for spelling, stored in (('owned.example', 'owned.example'), ('OWNED.EXAMPLE', 'owned.example'),
                                 ('shop.owned.example', 'shop.owned.example')):
            for value in ('Enable', 'Disable'):
                with self.subTest(spelling=spelling, value=value):
                    self.assertEqual(1, self.change(spelling, value)['status'])
                    self.assertEqual(
                        ['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/virtualHostUtilities.py',
                         'changeOpenBasedir', '--virtualHostName', stored, '--openBasedirValue', value],
                        shlex.split(self.commands()[0]))

    def test_another_value_starts_no_worker(self):
        for value in NOT_A_CHOICE:
            with self.subTest(value=value):
                self.assertEqual(0, self.change(value=value)['status'])
                self.assertEqual([], self.commands())

    def test_text_that_is_not_a_website_of_this_server_starts_no_worker(self):
        for domain in NOT_A_DOMAIN + ('other.example', "owned.example' --openBasedirValue 'Disable"):
            with self.subTest(domain=domain):
                self.assertEqual(0, self.change(domain=domain)['status'])
                self.assertEqual([], self.commands())

    def test_only_an_administrator_changes_it(self):
        self.services['ACLManager'].loadedACL.return_value = {'admin': 0}
        self.process.reset_mock()
        result = self.manager().changeOpenBasedir(7, {'domainName': 'owned.example', 'openBasedirValue': 'Enable'})
        self.assertIs(self.services['ACLManager'].loadErrorJson.return_value, result)
        self.assertEqual([], self.commands())


class OpenBasedirWorkerTests(unittest.TestCase):
    conf = 'docRoot $VH_ROOT/public_html\nphpIniOverride  {\nphp_admin_value open_basedir "/tmp:$VH_ROOT"\n}\n'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='open-basedir-test-')
        self.addCleanup(self.temp.cleanup)
        self.vhost = Path(self.temp.name) / 'conf' / 'vhosts' / 'example.test' / 'vhost.conf'
        self.vhost.parent.mkdir(parents=True)
        self.vhost.write_text(self.conf)
        self.process = mock.Mock(OLS='ols')
        self.process.decideServer.return_value = 'ols'
        self.install = mock.Mock()
        self.opened = []
        namespace = dict(ProcessUtilities=self.process, installUtilities=self.install, logging=mock.Mock(),
                         virtualHostUtilities=NS(Server_root=self.temp.name), ChildDomains=mock.Mock(),
                         open=self.open, print=print)
        self.worker, = load_methods('plogical/virtualHostUtilities.py', 'virtualHostUtilities',
                                    ['changeOpenBasedir'], namespace)

    def open(self, path, *args, **kwargs):
        self.opened.append(str(path))
        return open(path, *args, **kwargs)

    def run_worker(self, domain, value):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.worker(domain, value)
        return output.getvalue()

    def test_a_website_is_changed_as_before(self):
        self.assertEqual('1,None\n', self.run_worker('example.test', 'Disable'))
        self.assertEqual('docRoot $VH_ROOT/public_html\nphpIniOverride  {\n}\n', self.vhost.read_text())
        self.install.installUtilities.reStartLiteSpeed.assert_called_once_with()

    def test_a_website_named_by_an_earlier_release_is_changed(self):
        for name in OLDER_NAMES:
            with self.subTest(name=name):
                vhost = Path(self.temp.name) / 'conf' / 'vhosts' / name / 'vhost.conf'
                vhost.parent.mkdir(parents=True)
                vhost.write_text(self.conf)
                self.assertEqual('1,None\n', self.run_worker(name, 'Disable'))
                self.assertEqual('docRoot $VH_ROOT/public_html\nphpIniOverride  {\n}\n', vhost.read_text())

    def test_other_names_and_values_open_no_file_and_restart_nothing(self):
        os.mkdir(os.path.join(self.temp.name, 'conf', 'other'))
        for domain, value in [(domain, 'Disable') for domain in UNSAFE_STORED_NAME + ('../other', 'example.test/../../other')] + \
                [('example.test', value) for value in NOT_A_CHOICE]:
            with self.subTest(domain=domain, value=value):
                self.assertTrue(self.run_worker(domain, value).startswith('0,'))
        self.assertEqual([], self.opened)
        self.assertEqual(self.conf, self.vhost.read_text())
        self.install.installUtilities.reStartLiteSpeed.assert_not_called()


if __name__ == '__main__':
    unittest.main()
