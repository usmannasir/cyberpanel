"""Deleting a database drops the accounts that exist for it alone; other accounts only lose their grant on it."""
import unittest
from unittest import mock

from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities
from plogical.test_database_restore_accounts import Cursor, applied, panel


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

    def delete_with(self, granted, refuse, user_rows=()):
        """Delete shop_db on a server that answers some statements with an error."""
        self.cursor = Cursor(granted)
        execute = self.cursor.execute

        def answer(query, args=None):
            if query.startswith('SELECT 1 FROM mysql.user'):
                self.cursor.statements.append((query, args))
                self.cursor.rows = [(1,)] if tuple(args) in user_rows else []
                return None
            error = refuse(query, args)
            if error is not None:
                self.cursor.statements.append((query, args))
                raise error
            return execute(query, args)

        self.cursor.execute = answer
        with applied(panel()), \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(mock.Mock(), self.cursor)), \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile') as log:
            result = mysqlUtilities.deleteDatabase('shop_db', 'shop_user')
        self.logged = [call[0][0] for call in log.call_args_list]
        return result

    def test_account_whose_grant_cannot_be_taken_does_not_keep_the_deletion_from_finishing(self):
        # Before, one refused revoke made the deletion fail at every attempt: the database was
        # already dropped, its registration stayed and the website could not be deleted either.
        # The database and its own accounts decide whether the deletion is done; an account of
        # somebody else that keeps a grant on the name is reported in the panel log.
        granted = (('shop\\_db', 'reseller', 'localhost', False), ('shop\\_db', 'shop_user', 'localhost', False),
                   ('shop\\_db', 'agency', '%', False))
        refused = lambda query, args: (RuntimeError('server went away')
                                       if query.startswith('REVOKE') and args[0] == 'reseller' else None)
        self.assertEqual(1, self.delete_with(granted, refused))
        self.assertEqual([('DROP DATABASE IF EXISTS `shop_db`', None),
                          ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('reseller', 'localhost')),
                          ('DROP USER IF EXISTS %s@%s', ('shop_user', 'localhost')),
                          ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('agency', '%'))],
                         self.cursor.changes())
        self.assertEqual(1, len(self.logged))
        self.assertIn('reseller@localhost could not be taken its grant: server went away', self.logged[0])

    def test_grant_row_of_an_account_the_server_does_not_have_is_removed(self):
        granted = (('shop\\_db', 'gone_user', 'localhost', False), ('shop\\_db', 'shop_user', 'localhost', False))
        no_such_grant = lambda query, args: (
            RuntimeError(1141, "There is no such grant defined for user 'gone_user' on host 'localhost'")
            if query.startswith('REVOKE') else None)
        self.assertEqual(1, self.delete_with(granted, no_such_grant))
        self.assertEqual([('DROP DATABASE IF EXISTS `shop_db`', None),
                          ('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('gone_user', 'localhost')),
                          ('DROP USER IF EXISTS %s@%s', ('gone_user', 'localhost')),
                          ('DROP USER IF EXISTS %s@%s', ('shop_user', 'localhost'))], self.cursor.changes())
        self.assertEqual([], self.logged)

    def test_account_the_server_has_is_never_dropped_for_a_refused_revoke(self):
        granted = (('shop\\_db', 'reseller', 'localhost', False),)
        no_such_grant = lambda query, args: RuntimeError(1141, 'no such grant') if query.startswith('REVOKE') else None
        self.assertEqual(1, self.delete_with(granted, no_such_grant, user_rows=(('reseller', 'localhost'),)))
        self.assertEqual([], [query for query, args in self.cursor.changes() if query.startswith('DROP USER')])
        self.assertEqual(1, len(self.logged))
        # Any other error never leads to a drop either.
        other = lambda query, args: RuntimeError(1227, 'Access denied') if query.startswith('REVOKE') else None
        self.assertEqual(1, self.delete_with(granted, other))
        self.assertEqual([], [query for query, args in self.cursor.changes() if query.startswith('DROP USER')])

    def test_own_account_that_cannot_be_dropped_leaves_the_deletion_to_be_tried_again(self):
        granted = (('shop\\_db', 'shop_user', 'localhost', False), ('shop\\_db', 'shop_user', '127.0.0.1', False),
                   ('shop\\_db', 'reseller', 'localhost', False))
        refused = lambda query, args: (RuntimeError('server went away')
                                       if query.startswith('DROP USER') and args[1] == 'localhost' else None)
        result = self.delete_with(granted, refused)
        self.assertNotEqual(1, result)
        self.assertIn('shop_user@localhost', result)
        # The other accounts were dealt with all the same.
        self.assertIn(('DROP USER IF EXISTS %s@%s', ('shop_user', '127.0.0.1')), self.cursor.changes())
        self.assertIn(('REVOKE ALL PRIVILEGES ON `shop\\_db`.* FROM %s@%s', ('reseller', 'localhost')),
                      self.cursor.changes())

    def test_database_that_cannot_be_dropped_is_still_a_failed_deletion(self):
        refused = lambda query, args: RuntimeError('database is in use') if query.startswith('DROP DATABASE') else None
        self.assertEqual('database is in use', self.delete_with(self.GRANTED, refused))
        self.assertEqual(1, len(self.cursor.changes()))


if __name__ == '__main__':
    unittest.main()
