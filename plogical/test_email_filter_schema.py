import unittest
from unittest.mock import MagicMock

from plogical.schemaMigration import ensure_email_filter_tables


class EmailFilterSchemaTests(unittest.TestCase):
    def test_legacy_and_current_domain_collations_are_preserved(self):
        for charset, collation in (('latin1', 'latin1_swedish_ci'),
                                   ('utf8mb3', 'utf8mb3_general_ci'),
                                   ('utf8mb4', 'utf8mb4_unicode_ci')):
            with self.subTest(charset=charset):
                connection, cursor = MagicMock(), MagicMock()
                cursor.fetchone.return_value = (charset, collation)
                ensure_email_filter_tables(connection, cursor)
                statements = [call.args[0] for call in cursor.execute.call_args_list]
                creates = [sql for sql in statements if sql.startswith('CREATE TABLE')]
                self.assertEqual(4, len(creates))
                for sql in creates:
                    self.assertIn('DEFAULT CHARSET=%s COLLATE=%s' % (charset, collation), sql)
                self.assertEqual(4, sum(sql.startswith('SELECT 1 FROM') for sql in statements))
                connection.commit.assert_called_once()

    def test_missing_or_invalid_metadata_is_rejected_before_ddl(self):
        for metadata in (None, ('utf8mb4', 'invalid;DROP'), (None, None)):
            cursor = MagicMock()
            cursor.fetchone.return_value = metadata
            with self.assertRaisesRegex(RuntimeError, 'Cannot determine'):
                ensure_email_filter_tables(MagicMock(), cursor)
            self.assertEqual(1, cursor.execute.call_count)

    def test_create_error_identifies_the_table_and_does_not_claim_success(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ('utf8mb3', 'utf8mb3_general_ci')
        cursor.execute.side_effect = [None, RuntimeError('foreign key incompatible')]
        connection = MagicMock()
        with self.assertRaisesRegex(RuntimeError, 'e_catchall.*foreign key incompatible'):
            ensure_email_filter_tables(connection, cursor)
        connection.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
