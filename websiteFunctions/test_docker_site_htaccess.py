"""Deleting a Docker site takes the panel's own rules out of the website's .htaccess and leaves the rest."""
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import Docker_Sites

CUSTOMER = '''# kept by the customer
Options -Indexes
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule ^old/(.*)$ /new/$1 [R=301,L]
</IfModule>
'''


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='docker-site-htaccess-')
        self.addCleanup(shutil.rmtree, self.directory)
        self.path = os.path.join(self.directory, '.htaccess')

    def write(self, content):
        with open(self.path, 'w') as handle:
            handle.write(content)

    def read(self):
        with open(self.path) as handle:
            return handle.read()

    def setup_rules(self, port='11007', domain='shop.example'):
        with mock.patch('builtins.print'):
            Docker_Sites.SetupHTAccess(port, self.path, domain)

    def test_what_the_customer_wrote_survives_the_removal(self):
        for domain in ('shop.example', None):
            with self.subTest(domain=domain):
                self.write(CUSTOMER)
                self.setup_rules(domain=domain)
                self.assertIn('HTTP://docker11007/$1 [P]', self.read())
                self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
                self.assertEqual(CUSTOMER, self.read())

    def test_a_file_that_held_only_the_panels_rules_is_removed(self):
        for domain in ('shop.example', None):
            with self.subTest(domain=domain):
                self.setup_rules(domain=domain)
                self.assertTrue(os.path.exists(self.path))
                self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
                self.assertFalse(os.path.exists(self.path))

    def test_lines_added_after_the_panels_rules_survive_too(self):
        self.write(CUSTOMER)
        self.setup_rules()
        with open(self.path, 'a') as handle:
            handle.write('Header set X-Added-Later "1"\n')
        Docker_Sites.RemoveHTAccess(self.path, 'shop.example')
        self.assertEqual(CUSTOMER + 'Header set X-Added-Later "1"\n', self.read())

    def test_the_rule_is_removed_even_where_the_lines_around_it_were_changed(self):
        self.write(CUSTOMER + 'RewriteEngine on\n  REWRITERULE ^(.*)$ HTTP://docker11007/$1 [P]\nErrorDocument 404 /e.html\n')
        self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        self.assertEqual(CUSTOMER + 'RewriteEngine on\nErrorDocument 404 /e.html\n', self.read())

    def test_a_file_without_the_panels_rules_is_left_untouched(self):
        self.write(CUSTOMER + 'RewriteRule ^(.*)$ http://dockerhost.example/$1 [P]\n')
        before = os.stat(self.path).st_mtime_ns
        self.assertEqual(0, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        self.assertEqual(before, os.stat(self.path).st_mtime_ns)
        self.assertIn('dockerhost.example', self.read())

    def test_no_file_is_no_error(self):
        self.assertEqual(0, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        self.assertFalse(os.path.exists(self.path))

    def test_a_file_in_another_encoding_loses_the_panels_rules_and_nothing_else(self):
        # Latin-1 and Windows-1252 bytes that are not UTF-8, as an editor on the customer's computer saves them.
        customer = (b'# Weiterleitung f\xfcr die alte Adresse \x96 nicht l\xf6schen\n'
                    b'Options -Indexes\nErrorDocument 404 /nicht-gefunden.html\n')
        with self.assertRaises(UnicodeDecodeError):
            customer.decode('utf-8')
        for domain in ('shop.example', None):
            with self.subTest(domain=domain):
                with open(self.path, 'wb') as handle:
                    handle.write(customer)
                self.setup_rules(domain=domain)
                with open(self.path, 'rb') as handle:
                    self.assertIn(b'HTTP://docker11007/$1 [P]', handle.read())
                self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
                with open(self.path, 'rb') as handle:
                    self.assertEqual(customer, handle.read())

    def test_a_file_in_another_encoding_loses_the_rule_where_the_lines_around_it_were_changed(self):
        customer = b'# gepr\xfcft\nRewriteEngine on\n'
        with open(self.path, 'wb') as handle:
            handle.write(customer + b'  REWRITERULE ^(.*)$ HTTP://docker11007/$1 [P]\n# Ende \xa7\n')
        self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        with open(self.path, 'rb') as handle:
            self.assertEqual(customer + b'# Ende \xa7\n', handle.read())

    def test_the_line_ends_of_the_customers_file_are_kept(self):
        customer = b'# kept by the customer\r\nOptions -Indexes\r\nErrorDocument 404 /e.html\r\n'
        with open(self.path, 'wb') as handle:
            handle.write(customer)
        self.setup_rules()
        self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        with open(self.path, 'rb') as handle:
            self.assertEqual(customer, handle.read())
        # The whole file, the panel's rule included, saved with the other line ends afterwards.
        with open(self.path, 'wb') as handle:
            handle.write(customer + b'RewriteEngine On\r\nREWRITERULE ^(.*)$ HTTP://docker11007/$1 [P]\r\n'
                         + b'Header set X-Later "1"\r\n')
        self.assertEqual(1, Docker_Sites.RemoveHTAccess(self.path, 'shop.example'))
        with open(self.path, 'rb') as handle:
            self.assertEqual(customer + b'RewriteEngine On\r\nHeader set X-Later "1"\r\n', handle.read())

    def test_setup_still_writes_the_same_rules_once(self):
        self.setup_rules()
        self.setup_rules()
        self.assertEqual('RewriteEngine On\nRewriteCond %{HTTPS} !=on\n'
                         'RewriteRule ^ https://shop.example%{REQUEST_URI} [R=301,L]\n'
                         '\nRewriteEngine On\nREWRITERULE ^(.*)$ HTTP://docker11007/$1 [P]\n', self.read())


def delete(account='shop1234', lookup_fails=False):
    site = Docker_Sites.__new__(Docker_Sites)
    site.data = {'domain': 'shop.example', 'name': 'shop', 'JobID': None}
    site.DockerAppName = 'shop_shop'
    calls = []

    def execute(command, *more):
        calls.append((command,) + more)
        return 1

    models = SimpleNamespace(Websites=mock.Mock())
    if lookup_fails:
        models.Websites.objects.get.side_effect = RuntimeError('no such website')
    else:
        models.Websites.objects.get.return_value = SimpleNamespace(externalApp=account)
    client = mock.Mock()
    client.containers.list.return_value = []
    with mock.patch.object(docker_sites.docker, 'from_env', return_value=client), \
            mock.patch.object(docker_sites.ProcessUtilities, 'executioner', side_effect=execute), \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value='ubuntu'), \
            mock.patch.dict(sys.modules, {'plogical.installUtilities': SimpleNamespace(installUtilities=mock.Mock()),
                                          'websiteFunctions.models': models}), \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        site.DeleteDockerApp()
    return calls, models


class DeleteTests(unittest.TestCase):
    def test_root_never_removes_the_websites_htaccess(self):
        for kwargs in ({}, {'lookup_fails': True}, {'account': None}, {'account': 'a b'}, {'account': 'x;id'}):
            with self.subTest(**kwargs):
                calls, models = delete(**kwargs)
                for call in calls:
                    if '.htaccess' in call[0]:
                        self.assertNotIn('rm ', call[0])
                        self.assertEqual(2, len(call), call)

    def test_the_websites_own_account_takes_the_rules_out(self):
        calls, models = delete()
        models.Websites.objects.get.assert_called_once_with(domain='shop.example')
        touching = [call for call in calls if '.htaccess' in call[0]]
        self.assertEqual([('/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py RemoveHTAccess '
                           '--htaccess /home/shop.example/public_html/.htaccess --domain shop.example',
                           'shop1234')], touching)

    def test_without_a_usable_account_the_file_is_left_alone(self):
        for kwargs in ({'lookup_fails': True}, {'account': None}, {'account': ''}, {'account': 'a b'},
                       {'account': 'x;id'}, {'account': '-u'}, {'account': 7}):
            with self.subTest(**kwargs):
                calls, models = delete(**kwargs)
                self.assertEqual([], [call for call in calls if '.htaccess' in call[0]])
                self.assertTrue([call for call in calls if call[0] == 'rm -rf /home/docker/shop.example'])


class CommandLineTests(unittest.TestCase):
    def test_the_helper_is_reachable_from_the_command_line(self):
        with mock.patch.object(sys, 'argv', ['DockerSites.py', 'RemoveHTAccess', '--htaccess', '/tmp/x/.htaccess',
                                             '--domain', 'shop.example']), \
                mock.patch.object(Docker_Sites, 'RemoveHTAccess') as remove:
            docker_sites.Main()
        remove.assert_called_once_with('/tmp/x/.htaccess', 'shop.example')


if __name__ == '__main__':
    unittest.main(verbosity=2)
