"""After the ownership check, paths and commands use the stored name of a website, not the request's spelling."""
import json
import shlex
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from websiteFunctions.test_wordpress_entitlements import Response, load_wordpress_manager

# Spellings the database's default comparison treats as the stored 'owned.example'.
SAME_ROW = ('owned.example', 'OWNED.EXAMPLE', 'Owned.Example')
# Text that finds no website: not text at all, or a spelling the database does not match with a stored name.
NOT_A_DOMAIN = (' owned.example', 'owned.example\t', 'owned.example/..', '../owned.example',
                'owned.example;id', 'owned example', 'owned..example', '-owned.example', '', None, 7,
                ['owned.example'])
# Names from earlier releases that today's rule for a new name refuses.
OLDER_NAMES = ('my_shop.example.com', 'm\u00fcnchen.de')
# A stored name that cannot be one component of a path.
UNSAFE_STORED_NAME = ('', '.', '..', '-owned.example', 'owned.example/..', '../owned.example', '/owned.example',
                      'owned example', 'owned.example ', ' owned.example', 'owned.example\t', 'owned.example\n',
                      'owned\x00.example', 'owned.example\x7f', 'owned\u2028.example', None, 7, ['owned.example'])


class Rows:
    """A table that finds a name the way the database's default comparison does.

    Letter case and trailing spaces do not matter to it, so a lookup with
    another spelling returns the row with the stored name.
    """

    def __init__(self, *rows):
        self.rows = list(rows)
        self.lookups = []

    def matching(self, domain):
        self.lookups.append(domain)
        return [row for row in self.rows if row.domain.lower() == str(domain).rstrip(' ').lower()]

    def get(self, domain=None):
        found = self.matching(domain)
        if not found:
            raise LookupError(domain)
        return found[0]

    def filter(self, domain=None):
        found = self.matching(domain)
        return NS(first=lambda: found[0] if found else None)


def prepared_manager(admin=1):
    """The real WebsiteManager with an owned website, a child domain and inert services."""
    manager, namespace, services = load_wordpress_manager()
    site = mock.Mock(domain='owned.example', phpSelection='PHP 7.4', externalApp='owned1234')
    site.childdomains_set.filter.return_value = []
    child = mock.Mock(domain='shop.owned.example', phpSelection='PHP 7.4', master=site)
    namespace['Websites'] = NS(objects=Rows(site))
    namespace['ChildDomains'] = NS(objects=Rows(child))
    acl = services['ACLManager']
    acl.CheckForPremFeature.return_value = 1
    acl.loadedACL.return_value = {'admin': admin}
    for check in ('checkOwnership', 'currentContextPermission', 'checkOwnerProtection', 'checkUserOwnerShip'):
        getattr(acl, check).return_value = 1
    acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
    services['Administrator'].objects.get.return_value = NS(pk=7, userName='admin', defaultSite=1)
    services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
    services['virtualHostUtilities'].Server_root = '/usr/local/lsws'
    services['ApacheVhost'].configBasePath = '/etc/apache2/sites-enabled/'
    services['os'].path.isfile.return_value = True
    services['os'].path.exists.return_value = False
    services['ProcessUtilities'].outputExecutioner.return_value = 'owned.example\n1,None\n'
    namespace['change_php_succeeded'] = lambda output: '1,None' in output
    return manager, namespace, services, site, child


class StoredDomainNameTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services, self.site, self.child = prepared_manager()
        self.process = self.services['ProcessUtilities']

    def worker_words(self):
        calls = self.process.popenExecutioner.call_args_list + self.process.outputExecutioner.call_args_list
        commands = [call[0][0] for call in calls if 'virtualHostUtilities.py' in str(call[0][0])]
        self.assertTrue(commands)
        return shlex.split(commands[0])

    def test_every_spelling_the_database_matches_gives_the_stored_name(self):
        for spelling in SAME_ROW:
            self.assertEqual('owned.example', self.manager.storedDomainName(spelling))
        self.assertEqual('shop.owned.example', self.manager.storedDomainName('SHOP.owned.example'))

    def test_text_that_finds_no_website_is_refused(self):
        for value in NOT_A_DOMAIN:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid domain name'):
                    self.manager.storedDomainName(value)

    def test_only_text_is_looked_up(self):
        for value in (None, 7, ['owned.example'], {'domain': 'owned.example'}, b'owned.example'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid domain name'):
                    self.manager.storedDomainName(value)
        self.assertEqual([], self.ns['Websites'].objects.lookups)
        self.assertEqual([], self.ns['ChildDomains'].objects.lookups)

    def test_a_trailing_space_the_database_ignores_gives_the_stored_name(self):
        self.assertEqual('owned.example', self.manager.storedDomainName('owned.example '))

    def add_website(self, name, child=False):
        row = mock.Mock(domain=name, phpSelection='PHP 7.4', externalApp='older1234', master=self.site)
        row.childdomains_set.filter.return_value = []
        self.ns['ChildDomains' if child else 'Websites'].objects.rows.append(row)
        return row

    def test_a_website_named_by_an_earlier_release_is_found_under_its_stored_name(self):
        for name in OLDER_NAMES:
            self.add_website(name)
            self.add_website('shop.' + name, child=True)
        for name in OLDER_NAMES:
            with self.subTest(name=name):
                self.assertEqual(name, self.manager.storedDomainName(name))
                self.assertEqual(name, self.manager.storedDomainName(name.upper()))
                self.assertEqual('shop.' + name, self.manager.storedDomainName('Shop.' + name))

    def test_a_stored_name_that_cannot_name_a_directory_is_refused(self):
        for name in UNSAFE_STORED_NAME:
            if not isinstance(name, str) or not name:
                continue
            with self.subTest(name=name):
                row = mock.Mock(domain=name)
                self.ns['ChildDomains'] = NS(objects=NS(filter=lambda domain=None: NS(first=lambda: None)))
                self.ns['Websites'] = NS(objects=NS(filter=lambda domain=None: NS(first=lambda: row)))
                with self.assertRaisesRegex(ValueError, 'Invalid domain name'):
                    self.manager.storedDomainName(name)

    def test_the_stored_name_rule(self):
        from plogical.websiteSuspension import validate_stored_domain
        for name in OLDER_NAMES + ('owned.example', 'OWNED.example', 'xn--mnchen-3ya.de', 'a', 'owned.example-'):
            self.assertEqual(name, validate_stored_domain(name))
        for name in UNSAFE_STORED_NAME:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'Invalid domain name'):
                    validate_stored_domain(name)

    def test_php_change_works_for_a_website_named_by_an_earlier_release(self):
        for name in OLDER_NAMES:
            self.add_website(name)
            with self.subTest(name=name):
                self.process.reset_mock()
                payload = json.loads(self.manager().changePHP(
                    7, {'childDomain': name.upper(), 'phpSelection': 'PHP 8.3'}).content)
                self.assertEqual(1, payload['status'], payload)
                words = self.worker_words()
                self.assertEqual('/usr/local/lsws/conf/vhosts/%s/vhost.conf' % name,
                                 words[words.index('--path') + 1])

    def test_server_switch_and_open_basedir_work_for_a_website_named_by_an_earlier_release(self):
        for name in OLDER_NAMES:
            self.add_website(name)
            with self.subTest(name=name):
                self.process.reset_mock()
                payload = json.loads(self.manager().switchServer(
                    7, {'domainName': name, 'phpSelection': 'PHP 8.3', 'server': 1}).content)
                self.assertEqual(1, payload['status'], payload)
                words = self.worker_words()
                self.assertEqual(name, words[words.index('--virtualHostName') + 1])
                self.process.reset_mock()
                payload = json.loads(self.manager().changeOpenBasedir(
                    7, {'domainName': name, 'openBasedirValue': 'Enable'}).content)
                self.assertEqual(1, payload['status'], payload)
                words = self.worker_words()
                self.assertEqual(name, words[words.index('--virtualHostName') + 1])

    def test_a_domain_this_server_does_not_have_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Invalid domain name'):
            self.manager.storedDomainName('other.example')

    def test_php_change_names_the_stored_configuration_file(self):
        for spelling in SAME_ROW:
            with self.subTest(spelling=spelling):
                self.process.reset_mock()
                payload = json.loads(self.manager().changePHP(
                    7, {'childDomain': spelling, 'phpSelection': 'PHP 8.3'}).content)
                self.assertEqual(1, payload['status'], payload)
                words = self.worker_words()
                self.assertEqual('/usr/local/lsws/conf/vhosts/owned.example/vhost.conf',
                                 words[words.index('--path') + 1])

    def test_php_change_is_refused_for_text_that_is_not_a_domain(self):
        payload = json.loads(self.manager().changePHP(
            7, {'childDomain': 'owned.example /etc', 'phpSelection': 'PHP 8.3'}).content)
        self.assertEqual(0, payload['status'])
        self.assertIn('Invalid domain name', payload['error_message'])
        self.process.outputExecutioner.assert_not_called()

    def test_website_changes_name_the_stored_configuration_file(self):
        self.ns['Package'] = mock.Mock()
        quota, storage = mock.Mock(), mock.Mock()
        quota.prepare_package_quota.return_value = None
        storage.prepare_policy.return_value = None
        import sys
        with mock.patch.dict(sys.modules, {'plogical.filesystemQuota': quota, 'plogical.storageQuota': storage}):
            payload = json.loads(self.manager().saveWebsiteChanges(7, dict(
                domain='OWNED.EXAMPLE', packForWeb='Default', email='owner@example.test', phpVersion='PHP 8.3',
                admin='admin')).content)
        self.assertEqual(1, payload['status'], payload)
        words = self.worker_words()
        self.assertEqual('/usr/local/lsws/conf/vhosts/owned.example/vhost.conf', words[words.index('--path') + 1])

    def test_server_switch_names_the_stored_website(self):
        for spelling in SAME_ROW:
            with self.subTest(spelling=spelling):
                self.process.reset_mock()
                payload = json.loads(self.manager().switchServer(
                    7, {'domainName': spelling, 'phpSelection': 'PHP 8.3', 'server': 1}).content)
                self.assertEqual(1, payload['status'], payload)
                words = self.worker_words()
                self.assertEqual('owned.example', words[words.index('--virtualHostName') + 1])

    def test_server_switch_is_refused_for_text_that_is_not_a_domain(self):
        payload = json.loads(self.manager().switchServer(
            7, {'domainName': 'owned.example --server 2', 'phpSelection': 'PHP 8.3', 'server': 1}).content)
        self.assertEqual(0, payload['status'])
        self.process.popenExecutioner.assert_not_called()

    def test_switch_status_reads_the_stored_configuration_file(self):
        self.process.decideServer.return_value = self.process.OLS
        self.services['os'].path.exists.return_value = True
        self.services['ApacheVhost'].whichPHPExists.side_effect = \
            lambda domain: '/etc/php/8.1/fpm/pool.d/%s.conf' % domain
        self.process.outputExecutioner.return_value = '\n'.join(['x = y z'] * 12)
        payload = json.loads(self.manager().getSwitchStatus(7, {'domainName': 'OWNED.EXAMPLE'}).content)
        self.assertEqual(1, payload['status'], payload)
        self.assertEqual('/etc/php/8.1/fpm/pool.d/owned.example.conf', payload['phpPath'])
        self.assertEqual(['sudo cat /etc/php/8.1/fpm/pool.d/owned.example.conf',
                          'cat /etc/apache2/sites-enabled/owned.example.conf'],
                         [call[0][0] for call in self.process.outputExecutioner.call_args_list])


if __name__ == '__main__':
    unittest.main()
