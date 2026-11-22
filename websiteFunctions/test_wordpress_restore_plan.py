"""What a WordPress restore request asks for is decided before anything is downloaded or created."""
import json
import os
import subprocess
import tempfile
import unittest

from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager
from websiteFunctions.wordpressRestore import (
    address_is_on,
    backup_layout,
    backup_listing_filter,
    database_not_replaced,
    dump_site_address_command,
    dump_site_addresses,
    other_domain_refusal,
    restore_plan,
    restored_site_address,
)

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


class BackupLayoutTests(unittest.TestCase):
    ROOT = 'usr/local/CyberCP/tmp/ab12'

    def listing(self, *names, **options):
        return '\n'.join(options.get('slash', '/') + self.ROOT + '/' + name for name in names)

    def test_a_backup_made_of_a_site_holds_its_files_one_folder_down(self):
        listing = "tar: Removing leading `/' from member names\n" + self.listing(
            'public_html/wp-includes/version.php', 'public_html/wp-config.php', 'sourcedb.sql')
        self.assertEqual({'files': '/' + self.ROOT + '/public_html', 'config': '/' + self.ROOT + '/public_html/wp-config.php',
                          'strip': 6, 'dump': '/' + self.ROOT + '/sourcedb.sql', 'root': 5},
                         backup_layout('both', listing, 'ab12', 'sourcedb.sql'))

    def test_a_backup_of_a_staging_site_holds_them_two_folders_down(self):
        listing = self.listing('public_html/public_html/wp-config.php',
                               'public_html/public_html/wp-includes/version.php', 'sourcedb.sql')
        layout = backup_layout('both', listing, 'ab12', 'sourcedb.sql')
        self.assertEqual(('/' + self.ROOT + '/public_html/public_html', 7), (layout['files'], layout['strip']))
        self.assertEqual('/' + self.ROOT + '/public_html/public_html/wp-config.php', layout['config'])

    def test_names_are_given_back_as_the_archive_stores_them(self):
        listing = self.listing('public_html/wp-config.php', 'sourcedb.sql', slash='')
        layout = backup_layout('both', listing, 'ab12', 'sourcedb.sql')
        self.assertEqual((self.ROOT + '/public_html', self.ROOT + '/sourcedb.sql'), (layout['files'], layout['dump']))

    def test_a_site_folder_is_one_that_holds_wordpress(self):
        self.assertIsNone(backup_layout('files', self.listing('public_html/wp-includes/version.php'), 'ab12',
                                        'x.sql')['config'])
        for listing in ('', None, self.listing('public_html/readme.txt', 'public_html/blog/wp-config.php'),
                        self.listing('public_html/wp-config.php').replace('ab12', 'zz99')):
            with self.subTest(listing=listing):
                with self.assertRaisesRegex(ValueError, 'holds no WordPress files'):
                    backup_layout('files', listing, 'ab12', 'x.sql')

    def test_each_kind_must_hold_what_it_promises_and_nothing_more_is_asked_of_it(self):
        files = self.listing('public_html/wp-config.php')
        self.assertEqual((None, 5), (backup_layout('files', files, 'ab12', 'sourcedb.sql')['dump'], 5))
        with self.assertRaisesRegex(ValueError, 'holds no database dump'):
            backup_layout('both', files, 'ab12', 'sourcedb.sql')
        with self.assertRaisesRegex(ValueError, 'holds no database dump'):
            backup_layout('database', self.listing('other.sql'), 'ab12', 'sourcedb.sql')
        layout = backup_layout('database', self.listing('sourcedb.sql'), 'ab12', 'sourcedb.sql')
        self.assertEqual((None, None, '/' + self.ROOT + '/sourcedb.sql'),
                         (layout['files'], layout['config'], layout['dump']))

    def test_the_work_folder_named_by_a_backup_is_a_plain_name(self):
        for name in ('../../etc', 'a/b', 'a b', '', '.*', None, 'x' * 65):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    backup_listing_filter(name)
                with self.assertRaises(ValueError):
                    backup_layout('files', '', name, 'x.sql')
        self.assertEqual(r'^/?usr/local/CyberCP/tmp/1234/(public_html/(public_html/)?'
                         r'(wp-config\.php|wp-includes/version\.php)|[^/]+\.sql)$', backup_listing_filter('1234'))

    def test_the_recorded_address_of_a_site_is_its_domain_and_its_folder(self):
        self.assertEqual('new.example', restored_site_address('new.example', ''))
        self.assertEqual('new.example/blog/news', restored_site_address('new.example', 'blog/news'))


class OtherDomainTests(unittest.TestCase):
    def test_a_configuration_that_fixes_the_address_cannot_move_to_another_domain(self):
        for line in ("define('WP_HOME', 'https://source.example');", '  define( "WP_SITEURL", $address );',
                     "define('WP_HOME','x'); define('WP_SITEURL','x');"):
            self.assertIn('fixes the address of the site', other_domain_refusal(line), line)

    def test_a_network_of_sites_is_tied_to_its_domain(self):
        for lines in ("define('MULTISITE', true);", "define( 'MULTISITE', TRUE );", "define('MULTISITE', 1);",
                      "define('DOMAIN_CURRENT_SITE', 'source.example');", "define('SUBDOMAIN_INSTALL', false);"):
            self.assertIn('WordPress network', other_domain_refusal(lines), lines)

    def test_lines_that_are_commented_out_or_switch_nothing_on_do_not_count(self):
        for lines in ('', None, "// define('WP_HOME', 'x');", "# define('WP_SITEURL', 'x');",
                      " * define('MULTISITE', true);", "define('MULTISITE', false);",
                      "define('WP_ALLOW_MULTISITE', true);", "$note = 'WP_HOME is not set here';"):
            self.assertIsNone(other_domain_refusal(lines), lines)

    def test_a_site_address_is_on_a_domain_only_when_its_host_is_that_domain(self):
        for address in ('http://example.com', 'https://www.example.com/blog', 'HTTPS://Example.com:8443/',
                        'example.com/blog', ' http://example.com\n'):
            self.assertTrue(address_is_on(address, 'example.com'), address)
        for address in ('http://ample.com', 'http://myexample.com', 'http://example.com.evil.test',
                        'http://evil.test/example.com', 'http://sub.example.com', '', None, 'http://'):
            self.assertFalse(address_is_on(address, 'example.com'), address)
        self.assertFalse(address_is_on('http://example.com', ''))


# Dumps as `wp db export` writes them. mariadb-dump puts every row on a line
# of its own (taken from a real dump of MariaDB 10.11: "(2,'siteurl','https://…','on'),");
# mysqldump puts all rows of a table on one line. In both, wp_comments comes
# before wp_options, and here a visitor has left a comment under the name "siteurl".
MARIADB_DUMP = """-- MariaDB dump 10.19  Distrib 10.11.15-MariaDB, for debian-linux-gnu (x86_64)
LOCK TABLES `wp_comments` WRITE;
INSERT INTO `wp_comments` VALUES
(3,5271,'siteurl','spam@example.test','https://spam.example/','198.51.100.7','2026-01-25 08:11:10','2026-01-25 08:11:10','(1,\\'siteurl\\',\\'https://quoted.example\\',\\'yes\\')',0,'0','agent','comment',0,0);
UNLOCK TABLES;
LOCK TABLES `wp_options` WRITE;
INSERT INTO `wp_options` VALUES
(1,'cron','a:1:{i:1770064397;a:0:{}}','on'),
(2,'siteurl','https://source.example','on'),
(3,'home','https://source.example','on');
UNLOCK TABLES;
"""
MYSQL_DUMP = ("-- MySQL dump 10.13  Distrib 8.0.36\n"
              "INSERT INTO `wp_comments` VALUES (3,5271,'siteurl','spam@example.test','https://spam.example/',"
              "'198.51.100.7','2026-01-25 08:11:10','2026-01-25 08:11:10','text',0,'0','agent','comment',0,0);\n"
              "INSERT INTO `wp_options` VALUES (1,'siteurl','http://source.example/','yes'),"
              "(2,'home','http://source.example/','yes'),(3,'blogname','Source','yes');\n")


class ReplacedDatabaseTests(unittest.TestCase):
    def found_in(self, dump):
        with tempfile.TemporaryDirectory(prefix='wp-dump-test-') as folder:
            path = os.path.join(folder, "source db's.sql")
            with open(path, 'w') as handle:
                handle.write(dump)
            return subprocess.run(['sh', '-c', dump_site_address_command(path)], stdout=subprocess.PIPE,
                                  universal_newlines=True).stdout

    def test_the_command_finds_the_options_row_in_both_forms_of_dump_and_not_a_visitors_comment(self):
        self.assertEqual("(2,'siteurl','https://source.example','on')\n", self.found_in(MARIADB_DUMP))
        self.assertEqual(['https://source.example'], dump_site_addresses(self.found_in(MARIADB_DUMP)))
        self.assertEqual(['http://source.example/'], dump_site_addresses(self.found_in(MYSQL_DUMP)))
        self.assertEqual([], dump_site_addresses(self.found_in('NOT SQL;\n')))

    def test_what_the_command_prints_is_bounded_whatever_the_dump_holds(self):
        row = "(%d,'siteurl','https://flood.example/" + 'x' * 500 + "','on'),\n"
        found = self.found_in(''.join(row % number for number in range(5000)))
        self.assertLessEqual(len(found), 8192)
        self.assertLessEqual(len(dump_site_addresses(found)), 20)
        self.assertIn(" -m 20 -E ", dump_site_address_command('/x'))
        self.assertTrue(dump_site_address_command('/x').endswith(' /x | head -c 8192'))

    def test_only_a_row_of_the_options_shape_carries_an_address(self):
        self.assertEqual(['https://a.example', 'http://b.example'], dump_site_addresses(
            "(1,'siteurl','https://a.example','yes')\n(22,'siteurl','http://b.example','auto-on')\n"))
        for found in ('', None, "'siteurl','spam@example.test'", "(3,5271,'siteurl','spam@example.test','x')",
                      "(1,'siteurl','','yes')", "(1,\\'siteurl\\',\\'https://quoted.example\\',\\'yes\\')",
                      "(1,'home','https://a.example','yes')", "('siteurl','https://a.example','yes')"):
            self.assertEqual([], dump_site_addresses(found), found)

    def test_after_the_import_the_database_says_what_the_dump_says(self):
        self.assertIsNone(database_not_replaced(['https://source.example'], 'https://source.example\n',
                                                'new.example'))
        # A dump of a site that already was on the new domain's name is still recognised by its own address.
        self.assertIsNone(database_not_replaced(['https://new.example'], 'https://new.example', 'new.example'))
        # WordPress prints the stored address without its last slash.
        self.assertIsNone(database_not_replaced(['https://source.example/'], 'https://source.example',
                                                'new.example'))
        self.assertIsNotNone(database_not_replaced(['https://source.example/a'], 'https://source.example',
                                                   'new.example'))

    def test_any_of_the_dumps_rows_may_be_the_one_the_database_holds(self):
        rows = ['spam@example.test', 'https://source.example', 'https://other.example']
        self.assertIsNone(database_not_replaced(rows, 'https://source.example', 'new.example'))
        self.assertIsNotNone(database_not_replaced(rows, 'http://new.example', 'new.example'))

    def test_a_database_that_still_is_the_plain_installations_is_named(self):
        self.assertEqual('after the import the database gives "http://new.example" as the site address, the dump '
                         'gives "https://source.example"',
                         database_not_replaced(['https://source.example'], 'http://new.example', 'new.example'))
        for address in ('', None, 'Error: no such option'):
            self.assertIsNotNone(database_not_replaced(['https://source.example'], address, 'new.example'))

    def test_without_an_address_from_the_dump_the_plain_databases_address_must_at_least_be_gone(self):
        for none in ([], None):
            self.assertIsNone(database_not_replaced(none, 'https://source.example', 'new.example'))
            for address in ('http://new.example', 'https://www.new.example/blog', '', None):
                self.assertIn('as the plain installation did', database_not_replaced(none, address, 'new.example'))


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
        self.assertEqual('wordpressInstallNew', services['ApplicationInstaller'].call_args[0][0])
        return services['ApplicationInstaller'].call_args[0][1]

    def test_a_restore_marks_its_site_as_one_that_must_not_exist_yet(self):
        self.assertEqual(1, self.create(newWebsiteOnly=1)['newWebsiteOnly'])

    def test_the_wordpress_deployment_page_may_still_install_into_a_website_the_user_owns(self):
        self.assertEqual(0, self.create()['newWebsiteOnly'])
        self.assertEqual(0, self.create(newWebsiteOnly=0)['newWebsiteOnly'])


if __name__ == '__main__':
    unittest.main()
