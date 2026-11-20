"""Options of website and child-domain creation reach the worker's command line only as 0 or 1."""
import json
import shlex
from types import SimpleNamespace
import unittest

from websiteFunctions.test_apache_entitlements import child_data, website_data
from websiteFunctions.test_wordpress_entitlements import Response, load_wordpress_manager

# Values a request can carry that are not a plain 0 or 1.
OTHER_VALUES = ({'a': '$(id)'}, ['1', '--path', '/etc'], '1 --websiteOwner admin', '0; id', 2, -1, 1.5,
                None, 'true', '', [1], {'1': 1})


class CreationOptionTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        acl = self.services['ACLManager']
        acl.CheckForPremFeature.return_value = 0
        acl.loadedACL.return_value = {'admin': 1}
        acl.checkOwnership.return_value = 1
        acl.currentContextPermission.return_value = 1
        acl.checkOwnerProtection.return_value = 1
        acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(pk=7, userName='admin',
                                                                                 defaultSite=1)
        self.services['Websites'].objects.get.side_effect = LookupError('No username collision')
        self.services['validators'].domain.return_value = True
        self.services['validators'].email.return_value = True
        self.services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        self.services['ApacheVhost'].configBasePath = '/etc/apache2/sites-enabled/'

    def command(self, method, data):
        self.services['ProcessUtilities'].reset_mock()
        result = getattr(self.manager(), method)(7, data)
        self.assertEqual(1, json.loads(result.content)['createWebSiteStatus'], result.content)
        return shlex.split(self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])

    def option(self, words, name):
        self.assertEqual(1, words.count(name), words)
        return words[words.index(name) + 1]

    def test_plain_choices_are_passed_on_unchanged(self):
        for value, expected in ((1, '1'), ('1', '1'), (True, '1'), (0, '0'), ('0', '0'), (False, '0')):
            words = self.command('submitWebsiteCreation', dict(website_data(), openBasedir=value, mailDomain=value))
            self.assertEqual((expected, expected),
                             (self.option(words, '--openBasedir'), self.option(words, '--mailDomain')), value)
            words = self.command('submitDomainCreation', dict(child_data(), openBasedir=value))
            self.assertEqual(expected, self.option(words, '--openBasedir'), value)
            self.assertEqual('0', self.option(words, '--aliasDomain'))

    def test_any_other_value_becomes_zero_and_adds_nothing_to_the_command(self):
        plain_site = self.command('submitWebsiteCreation', dict(website_data(), openBasedir=0, mailDomain=0))
        plain_child = self.command('submitDomainCreation', dict(child_data(), openBasedir=0))
        for value in OTHER_VALUES:
            words = self.command('submitWebsiteCreation', dict(website_data(), openBasedir=value, mailDomain=value))
            self.assertEqual(len(plain_site), len(words), repr(value))
            self.assertEqual(('0', '0'), (self.option(words, '--openBasedir'), self.option(words, '--mailDomain')),
                             repr(value))
            words = self.command('submitDomainCreation', dict(child_data(), openBasedir=value, alias=value))
            self.assertEqual(len(plain_child), len(words), repr(value))
            self.assertEqual(('0', '0'), (self.option(words, '--openBasedir'), self.option(words, '--aliasDomain')),
                             repr(value))

    def test_missing_mail_domain_keeps_its_default(self):
        words = self.command('submitWebsiteCreation', website_data())
        self.assertEqual('1', self.option(words, '--mailDomain'))


if __name__ == '__main__':
    unittest.main()
