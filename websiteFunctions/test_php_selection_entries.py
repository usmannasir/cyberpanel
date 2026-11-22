"""Every request that names a PHP version is refused unless it is exactly one of the panel's selections."""
import json
import shlex
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED, OLDER_SPELLINGS
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
        self.ns['ChildDomains'].objects.filter.return_value.first.return_value = None
        self.services['Websites'].objects.filter.return_value.first.return_value = None
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
        self.services['Websites'].objects.filter.return_value.first.return_value = self.site

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

    def php_word(self):
        commands = self.worker_commands()
        self.assertTrue(commands)
        words = shlex.split(commands[0])
        self.assertEqual(1, words.count('--phpVersion'))
        return words[words.index('--phpVersion') + 1]

    def test_a_page_request_for_a_new_website_keeps_the_strict_check(self):
        for spelling in OLDER_SPELLINGS:
            with self.subTest(spelling=spelling):
                self.process.reset_mock()
                payload = json.loads(self.manager().submitWebsiteCreation(
                    7, dict(website_data(), phpSelection=spelling)).content)
                self.assertEqual(0, payload['status'], payload)
                # Nor does a field of the request switch the check off.
                payload = json.loads(self.manager().submitWebsiteCreation(
                    7, dict(website_data(), phpSelection=spelling, controller='submitWebsiteCreation')).content)
                self.assertEqual(0, payload['status'], payload)
                self.assertEqual([], self.worker_commands())

    def api_request(self, **changes):
        self.ns['hashPassword'] = mock.Mock()
        self.ns['hashPassword'].check_password.return_value = True
        self.ns['ACL'] = mock.Mock()
        self.ns['generate_api_token'] = lambda: 'token'
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(
            pk=7, userName='admin', defaultSite=1, password='stored-hash')
        self.services['Administrator'].objects.filter.return_value.exists.return_value = True
        self.services['ACLManager'].websitesLimitCheck.return_value = 1
        data = dict(adminUser='admin', adminPass='inert-password', ownerEmail='owner@example.test',
                    websiteOwner='admin', ownerPassword='inert-password', packageName='Default',
                    domainName='owned.example')
        data.update(changes)
        return json.loads(self.manager().createWebsiteAPI(data).content)

    def test_api_website_creation_takes_an_older_spelling(self):
        for spelling, selection in OLDER_SPELLINGS.items():
            with self.subTest(spelling=spelling):
                self.process.reset_mock()
                payload = self.api_request(phpSelection=spelling)
                self.assertEqual(1, payload['createWebSiteStatus'], payload)
                self.assertEqual(selection, self.php_word())

    def test_api_website_creation_keeps_its_default_version(self):
        payload = self.api_request()
        self.assertEqual(1, payload['createWebSiteStatus'], payload)
        self.assertEqual('PHP 7.4', self.php_word())

    def test_api_website_creation_refuses_text_that_is_no_version(self):
        for value in ('PHP 7', 'latest', 'PHP 7.4 --apache 1', '', None, 74):
            with self.subTest(value=value):
                self.process.reset_mock()
                payload = self.api_request(phpSelection=value)
                self.assertEqual(0, payload['createWebSiteStatus'], payload)
                self.assertIn('Invalid PHP version selected.', payload['error_message'])
                self.assertEqual([], self.worker_commands())

    def test_an_alias_is_created_with_the_masters_stored_version_in_the_panels_form(self):
        for stored, selection in (('PHP 74', 'PHP 7.4'), ('php 8.1', 'PHP 8.1'), ('PHP 8.3', 'PHP 8.3')):
            with self.subTest(stored=stored):
                self.process.reset_mock()
                self.existing_site()
                self.site.phpSelection = stored
                payload = json.loads(self.manager().submitDomainCreation(
                    7, dict(child_data(), domainName='alias.example', alias=1)).content)
                self.assertEqual(1, payload['status'], payload)
                self.assertEqual(selection, self.php_word())

    def test_an_alias_is_refused_when_the_masters_stored_version_is_no_version(self):
        self.existing_site()
        self.site.phpSelection = 'PHP seven'
        payload = json.loads(self.manager().submitDomainCreation(
            7, dict(child_data(), domainName='alias.example', alias=1)).content)
        self.assertEqual(0, payload['status'], payload)
        self.assertIn('Invalid PHP version selected.', payload['error_message'])
        self.assertEqual([], self.worker_commands())

    def test_website_changes_refuse_a_version_that_is_not_installed(self):
        self.existing_site()
        self.services['os'].path.isfile.return_value = False
        payload = json.loads(self.manager().saveWebsiteChanges(7, site_changes(phpVersion='PHP 8.4')).content)
        self.assertEqual(0, payload['status'], payload)
        self.assertIn('PHP 8.4 is not installed on this server.', payload['error_message'])
        self.services['os'].path.isfile.assert_called_once_with('/usr/local/lsws/lsphp84/bin/php')
        self.assertEqual([], self.worker_commands())
        self.site.save.assert_not_called()
        self.assertEqual('PHP 7.4', self.site.phpSelection)

    def test_website_changes_keep_working_for_the_version_the_website_already_has(self):
        # Its PHP may have been removed from the server since; the owner,
        # the package and the e-mail address can still be changed.
        self.existing_site()
        self.services['os'].path.isfile.return_value = False
        payload = json.loads(self.manager().saveWebsiteChanges(7, site_changes(phpVersion='PHP 7.4')).content)
        self.assertEqual(1, payload['status'], payload)
        self.site.save.assert_called_once_with()

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
