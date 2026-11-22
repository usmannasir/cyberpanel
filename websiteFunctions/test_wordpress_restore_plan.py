"""What a WordPress restore request asks for is decided before anything is downloaded or created."""
import json
import unittest

from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager
from websiteFunctions.wordpressRestore import backup_parts, restore_plan, restored_site_address

BOTH = 'Both Website and DataBase'


class RestorePlanTests(unittest.TestCase):
    def test_each_kind_of_backup_goes_into_an_existing_site(self):
        self.assertEqual(('both', 'existing'), restore_plan(BOTH, 34, ''))
        self.assertEqual(('files', 'existing'), restore_plan('Website Backup', '34', ''))
        self.assertEqual(('database', 'existing'), restore_plan('DataBase Backup', 34, ''))

    def test_a_backup_with_files_can_become_a_new_site(self):
        self.assertEqual(('both', 'new'), restore_plan(BOTH, -1, 'new.example'))
        self.assertEqual(('files', 'new'), restore_plan('Website Backup', '-1', 'new.example'))

    def test_a_database_alone_never_becomes_a_new_site(self):
        with self.assertRaisesRegex(ValueError, 'only be restored to an existing WordPress site'):
            restore_plan('DataBase Backup', -1, 'new.example')

    def test_a_request_names_exactly_one_destination(self):
        for site, domain in ((-1, ''), (34, 'new.example'), ('x', ''), (None, 'new.example'), (-1, None)):
            with self.subTest(site=site, domain=domain):
                with self.assertRaisesRegex(ValueError, 'exactly one restore destination'):
                    restore_plan(BOTH, site, domain)

    def test_a_description_without_a_known_kind_is_a_backup_of_files_and_database(self):
        for described in (None, '', 'Full', 'database backup'):
            self.assertEqual(('both', 'existing'), restore_plan(described, 34, ''))


class BackupPartsTests(unittest.TestCase):
    ROOT = '/usr/local/CyberCP/tmp/new/ab/usr/local/CyberCP/tmp/old'

    def parts(self, kind):
        return backup_parts(kind, '/usr/local/CyberCP/tmp/new', 'old', 'sourcedb.sql')

    def test_each_kind_holds_what_it_promises_and_nothing_else_is_expected(self):
        self.assertEqual((self.ROOT + '/public_html', self.ROOT + '/sourcedb.sql'), self.parts('both'))
        self.assertEqual((self.ROOT + '/public_html', None), self.parts('files'))
        self.assertEqual((None, self.ROOT + '/sourcedb.sql'), self.parts('database'))

    def test_the_recorded_address_of_a_site_is_its_domain_and_its_folder(self):
        self.assertEqual('new.example', restored_site_address('new.example', ''))
        self.assertEqual('new.example/blog/news', restored_site_address('new.example', 'blog/news'))


class NewWebsiteOnlyTests(unittest.TestCase):
    """The site a restore asks for is created for it; the request says so to the creating worker."""

    def create(self, **extra):
        manager, namespace, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 1
        services['Administrator'].objects.get.return_value.pk = 7
        data = {'domain': 'new.example', 'WPVersion': '7.1.5', 'title': 'Source', 'adminUser': 'admin',
                'PasswordByPass': 'inert', 'Email': 'owner@example.test', 'AutomaticUpdates': 'Disabled',
                'Plugins': 'Disabled', 'Themes': 'Disabled', 'websiteOwner': 'owner', 'package': 'Default',
                'home': '1', 'path': ''}
        data.update(extra)
        response = json.loads(manager().submitWorpressCreation(7, data).content)
        self.assertEqual(1, response['status'], response)
        self.assertEqual('wordpressInstallNew', services['ApplicationInstaller'].call_args.args[0])
        return services['ApplicationInstaller'].call_args.args[1]

    def test_a_restore_marks_its_site_as_one_that_must_not_exist_yet(self):
        self.assertEqual(1, self.create(newWebsiteOnly=1)['newWebsiteOnly'])

    def test_the_wordpress_deployment_page_may_still_install_into_a_website_the_user_owns(self):
        self.assertEqual(0, self.create()['newWebsiteOnly'])
        self.assertEqual(0, self.create(newWebsiteOnly=0)['newWebsiteOnly'])


if __name__ == '__main__':
    unittest.main()
