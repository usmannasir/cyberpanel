"""Every request that names a PHP version is refused unless it is exactly one of the panel's selections."""
import json
import shlex
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED
from websiteFunctions.test_apache_entitlements import child_data, website_data
from websiteFunctions.test_wordpress_entitlements import Response, load_wordpress_manager

# What a request body can carry; bytes cannot arrive in JSON.
REFUSED = tuple(value for value in NOT_A_SELECTION if not isinstance(value, bytes))


def site_changes(**changes):
    data = dict(domain='owned.example', packForWeb='Default', email='owner@example.test',
                phpVersion='PHP 8.3', admin='admin')
    data.update(changes)
    return data


class PHPSelectionEntryTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        acl = self.services['ACLManager']
        acl.CheckForPremFeature.return_value = 1
        acl.loadedACL.return_value = {'admin': 1}
        for check in ('checkOwnership', 'currentContextPermission', 'checkOwnerProtection', 'checkUserOwnerShip'):
            getattr(acl, check).return_value = 1
        acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(pk=7, userName='admin',
                                                                                 defaultSite=1)
        self.site = mock.Mock(domain='owned.example', phpSelection='PHP 7.4', externalApp='owned1234')
        self.site.childdomains_set.filter.return_value = []
        self.services['Websites'].objects.get.side_effect = LookupError('no such website')
        self.services['validators'].domain.return_value = True
        self.services['validators'].email.return_value = True
        self.services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        self.services['virtualHostUtilities'].Server_root = '/usr/local/lsws'
        self.services['ApacheVhost'].configBasePath = '/etc/apache2/sites-enabled/'
        self.services['os'].path.isfile.return_value = True
        self.services['os'].path.exists.return_value = False
        self.process = self.services['ProcessUtilities']
        self.process.outputExecutioner.return_value = 'owned.example\n1,None\n'
        self.ns['Package'] = mock.Mock()
        self.ns['ChildDomains'] = mock.Mock()
        self.ns['change_php_succeeded'] = lambda output: '1,None' in output
        quota = mock.Mock()
        quota.prepare_package_quota.return_value = None
        storage = mock.Mock()
        storage.prepare_policy.return_value = None
        # Website creation reserves a real status file; none is made here.
        for patcher in (
                mock.patch.dict(sys.modules, {'plogical.filesystemQuota': quota, 'plogical.storageQuota': storage}),
                mock.patch('plogical.statusUtilities.create_status_file', return_value='/home/cyberpanel/1000')):
            patcher.start()
            self.addCleanup(patcher.stop)

    def existing_site(self):
        self.services['Websites'].objects.get.side_effect = None
        self.services['Websites'].objects.get.return_value = self.site

    def entries(self):
        """(name, call with a PHP value, whether the website already exists)."""
        manager = self.manager
        return (
            ('submitWebsiteCreation', lambda php: manager().submitWebsiteCreation(7, dict(website_data(), phpSelection=php)),
             False),
            ('submitDomainCreation', lambda php: manager().submitDomainCreation(7, dict(child_data(), phpSelection=php)),
             False),
            ('saveWebsiteChanges', lambda php: manager().saveWebsiteChanges(7, site_changes(phpVersion=php)), True),
            ('switchServer', lambda php: manager().switchServer(
                7, {'domainName': 'owned.example', 'phpSelection': php, 'server': 1}), True),
            ('changePHP', lambda php: manager().changePHP(
                7, {'childDomain': 'owned.example', 'phpSelection': php}), True),
        )

    def worker_commands(self):
        calls = self.process.popenExecutioner.call_args_list + self.process.outputExecutioner.call_args_list + \
            self.process.executioner.call_args_list
        return [call[0][0] for call in calls if 'virtualHostUtilities.py' in str(call[0][0])]

    def test_other_text_is_refused_and_starts_no_worker(self):
        for name, call, exists in self.entries():
            for value in REFUSED:
                with self.subTest(entry=name, value=value):
                    self.process.reset_mock()
                    self.site.reset_mock()
                    if exists:
                        self.existing_site()
                    payload = json.loads(call(value).content)
                    self.assertEqual(0, payload['status'], payload)
                    self.assertIn('Invalid PHP version selected.', payload['error_message'])
                    self.assertEqual([], self.worker_commands())
                    # Nothing was stored with the website either.
                    self.site.save.assert_not_called()
                    self.assertEqual('PHP 7.4', self.site.phpSelection)

    def test_an_offered_version_reaches_the_worker_as_one_word(self):
        for name, call, exists in self.entries():
            for selection in OFFERED:
                with self.subTest(entry=name, selection=selection):
                    self.process.reset_mock()
                    if exists:
                        self.existing_site()
                    else:
                        self.services['Websites'].objects.get.side_effect = LookupError('no such website')
                    payload = json.loads(call(selection).content)
                    self.assertEqual(1, payload['status'], payload)
                    commands = self.worker_commands()
                    self.assertTrue(commands, name)
                    words = shlex.split(commands[0])
                    self.assertEqual(selection, words[words.index('--phpVersion') + 1])
                    self.assertEqual(1, words.count('--phpVersion'))

    def test_alias_of_a_website_with_an_unusable_stored_version_is_refused(self):
        self.services['Websites'].objects.get.side_effect = None
        self.services['Websites'].objects.get.return_value = SimpleNamespace(phpSelection='PHP 8.3 --apache 1')
        payload = json.loads(self.manager().submitDomainCreation(7, child_data(alias=1)).content)
        self.assertEqual(0, payload['createWebSiteStatus'])
        self.assertIn('Invalid PHP version selected.', payload['error_message'])
        self.assertEqual([], self.worker_commands())

    def test_refusal_follows_the_permission_checks_of_an_existing_website(self):
        # Someone who may not touch the website learns nothing about the value.
        self.existing_site()
        self.services['ACLManager'].checkOwnership.return_value = 0
        denied = self.services['ACLManager'].loadErrorJson.return_value
        for name, call, exists in self.entries():
            if exists:
                with self.subTest(entry=name):
                    self.assertIs(denied, call('PHP 8.3\tsshd'))
        self.assertEqual([], self.worker_commands())


if __name__ == '__main__':
    unittest.main()
