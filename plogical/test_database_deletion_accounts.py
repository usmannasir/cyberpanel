"""Deleting a database drops the accounts that exist for it alone; other accounts only lose their grant on it."""
import unittest
from unittest import mock

from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities
from plogical.test_database_restore_accounts import Cursor, panel


class DeletedDatabaseAccountTests(unittest.TestCase):
    GRANTED = (('shop\\_db', 'shop_user', 'localhost', False), ('shop\\_db', 'shop_user', '127.0.0.1', False),
               ('shop_db', 'shop_user', '203.0.113.9', False),
               ('shop\\_db', 'reseller', 'localhost', False), ('shop\\_db', 'agency', '%', True),
               ('other\\_db', 'agency', '%', False))

    def delete(self, user='shop_user', granted=GRANTED, **registered):
        self.cursor = Cursor(granted)
        connection = mock.Mock()
        patches = panel(**registered)
        with patches[0], patches[1], patches[2], \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, self.cursor)):
            return mysqlUtilities.deleteDatabase('shop_db', user)

    def test_only_the_accounts_of_this_database_are_dropped(self):
        self.assertEqual(1, self.delete(phpmyadmin=('reseller',)))
        self.assertEqual([
            ('DROP DATABASE IF EXISTS `shop_db`', None),
            ('DROP USER IF EXISTS %s@%s', ('shop_user', 'localhost')),
            ('DROP USER IF EXISTS %s@%s', ('shop_user', '127.0.0.1')),
            ('DROP USER IF EXISTS %s@%s', ('shop_user', '203.0.113.9')),
            ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('reseller', 'localhost')),
            ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('agency', '%')),
            ('REVOKE GRANT OPTION ON `shop\\_db`.* FROM %s@%s', ('agency', '%')),
        ], self.cursor.changes())

    def test_user_shared_with_another_database_keeps_its_account_and_loses_this_grant(self):
        granted = (('shop_db', 'shared', 'localhost', False), ('blog\\_db', 'shared', 'localhost', False))
        self.assertEqual(1, self.delete('shared', granted, databases=(('shop_db', 'shared'), ('blog_db', 'shared'))))
        self.assertEqual([('DROP DATABASE IF EXISTS `shop_db`', None),
                          ('REVOKE ALL PRIVILEGES ON `shop_db`.* FROM %s@%s', ('shared', 'localhost'))],
                         self.cursor.changes())

    def test_registered_name_that_is_a_phpmyadmin_account_is_not_dropped(self):
        granted = (('shop\\_db', 'reseller', 'localhost', False),)
        self.assertEqual(1, self.delete('reseller', granted, databases=(('shop_db', 'reseller'),),
                                        phpmyadmin=('reseller',)))
        self.assertEqual([], [query for query, args in self.cursor.changes() if query.startswith('DROP USER')])
        self.assertEqual(1, len([query for query, args in self.cursor.changes() if query.startswith('REVOKE')]))

    def test_grant_stored_in_either_form_is_taken_away(self):
        granted = (('shop_db', 'reseller', 'localhost', False), ('shop\\_db', 'reseller', 'localhost', False))
        self.assertEqual(1, self.delete(granted=granted))
        self.assertEqual([('REVOKE ALL PRIVILEGES ON `shop_db`.* FROM %s@%s', ('reseller', 'localhost')),
                          ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('reseller', 'localhost'))],
                         self.cursor.changes()[1:])

    def test_additional_registered_user_goes_with_its_database(self):
        granted = (('shop\\_db', 'shop_reader', 'localhost', False),)
        self.assertEqual(1, self.delete(granted=granted, additional=(('shop_db', 'shop_reader'),)))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('shop_reader', 'localhost'))], self.cursor.changes()[1:])

    def test_database_that_is_no_longer_registered_still_drops_the_user_the_caller_names(self):
        granted = (('shop\\_db', 'shop_user', 'localhost', False),)
        self.assertEqual(1, self.delete(granted=granted, databases=()))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('shop_user', 'localhost'))], self.cursor.changes()[1:])

    def test_failed_revoke_fails_the_deletion_so_that_it_is_tried_again(self):
        self.cursor = Cursor((('shop\\_db', 'reseller', 'localhost', False),))
        execute = self.cursor.execute

        def refuse(query, args=None):
            if query.startswith('REVOKE'):
                raise RuntimeError('server went away')
            return execute(query, args)

        self.cursor.execute = refuse
        patches = panel()
        with patches[0], patches[1], patches[2], \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(mock.Mock(), self.cursor)), \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            self.assertEqual('server went away', mysqlUtilities.deleteDatabase('shop_db', 'shop_user'))


if __name__ == '__main__':
    unittest.main()
