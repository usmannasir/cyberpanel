"""Only an administrator can start the server-wide installation of Apache and PHP-FPM."""
import json
import unittest
from unittest import mock

from websiteFunctions.test_apache_entitlements import child_data, website_data
from websiteFunctions.test_stored_domain_name import prepared_manager


class FirstSetupRuleTests(unittest.TestCase):
    def test_refused_only_for_another_user_while_apache_is_not_installed(self):
        apache_first_setup_error = prepared_manager()[1]['apache_first_setup_error']
        self.assertIsNone(apache_first_setup_error({'admin': 1}, 0))
        self.assertIsNone(apache_first_setup_error({'admin': 1}, 1))
        self.assertIsNone(apache_first_setup_error({'admin': 0}, 1))
        for acl in ({'admin': 0}, {'admin': '1'}, {'admin': 2}, {}, None):
            with self.subTest(acl=acl):
                payload = json.loads(apache_first_setup_error(acl, 0).content)
                self.assertEqual(0, payload['status'])
                self.assertEqual(0, payload['createWebSiteStatus'])
                self.assertIn('administrator', payload['error_message'])


class FirstApacheWebsiteTests(unittest.TestCase):
    def prepare(self, admin, installed):
        self.manager, self.ns, self.services, _, _ = prepared_manager(admin=admin)
        self.services['ApacheController'].checkIfApacheInstalled.return_value = installed
        self.services['validators'].domain.return_value = True
        self.services['validators'].email.return_value = True
        self.process = self.services['ProcessUtilities']
        # Website creation reserves a real status file; none is made here.
        patcher = mock.patch('plogical.statusUtilities.create_status_file', return_value='/home/cyberpanel/1000')
        patcher.start()
        self.addCleanup(patcher.stop)

    def requests(self):
        manager = self.manager
        return (
            ('switchServer', lambda: manager().switchServer(
                7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 1})),
            ('submitWebsiteCreation', lambda: manager().submitWebsiteCreation(
                7, dict(website_data(), apacheBackend=1))),
            ('submitDomainCreation', lambda: manager().submitDomainCreation(
                7, dict(child_data(), apacheBackend=1))),
        )

    def started(self):
        return [call[0][0] for call in self.process.popenExecutioner.call_args_list]

    def test_another_user_cannot_start_the_first_installation(self):
        self.prepare(admin=0, installed=0)
        for name, request in self.requests():
            with self.subTest(request=name):
                payload = json.loads(request().content)
                self.assertEqual(0, payload['status'], payload)
                self.assertIn('administrator', payload['error_message'])
                self.assertEqual([], self.started())

    def test_an_administrator_starts_it(self):
        self.prepare(admin=1, installed=0)
        for name, request in self.requests():
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))

    def test_every_user_may_use_apache_once_it_is_installed(self):
        self.prepare(admin=0, installed=1)
        for name, request in self.requests():
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))

    def test_requests_that_install_nothing_are_not_held_back(self):
        self.prepare(admin=0, installed=0)
        manager = self.manager
        for name, request in (
                ('switch back to OpenLiteSpeed', lambda: manager().switchServer(
                    7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 2})),
                ('website without Apache', lambda: manager().submitWebsiteCreation(
                    7, website_data())),
                ('child domain without Apache', lambda: manager().submitDomainCreation(
                    7, child_data()))):
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))
        self.services['ApacheController'].checkIfApacheInstalled.assert_not_called()

    def test_a_server_that_is_not_a_number_starts_nothing(self):
        self.prepare(admin=1, installed=1)
        for server in ('1 --tempStatusPath /etc/x', 'apache', None, [1]):
            with self.subTest(server=server):
                payload = json.loads(self.manager().switchServer(
                    7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': server}).content)
                self.assertEqual(0, payload['status'])
        self.assertEqual([], self.started())


if __name__ == '__main__':
    unittest.main()
