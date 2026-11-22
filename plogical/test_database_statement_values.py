"""Statements that create a database account carry the caller's values as parameters."""
import unittest
from unittest import mock

from plogical.mysqlUtilities import mysqlUtilities


class StatementTests(unittest.TestCase):
    def test_account_statement_carries_its_values_as_parameters(self):
        connection, cursor = mock.Mock(), mock.Mock()
        with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.createDBUser("pa`nel", "pass' OR '1"))
        self.assertEqual([mock.call('CREATE DATABASE `pa``nel`'),
                          mock.call('CREATE USER %s@%s IDENTIFIED BY %s',
                                    ("pa`nel", mysqlUtilities.LOCALHOST, "pass' OR '1"))],
                         cursor.execute.call_args_list)

    def test_unused_statement_builder_is_gone(self):
        self.assertFalse(hasattr(mysqlUtilities, 'UpdateWPTempPassword'))


if __name__ == '__main__':
    unittest.main()
