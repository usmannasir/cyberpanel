import unittest

from plogical.schemaMigration import ensure_administrator_default_site


class FakeConnection:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakeCursor:
    def __init__(self, column_exists=False, alter_creates_column=True):
        self.column_exists = column_exists
        self.alter_creates_column = alter_creates_column
        self.executed = []

    def execute(self, statement):
        self.executed.append(statement)
        if statement.startswith('ALTER TABLE') and self.alter_creates_column:
            self.column_exists = True

    def fetchone(self):
        return ('defaultSite',) if self.column_exists else None


class AdministratorDefaultSiteMigrationTests(unittest.TestCase):
    def test_existing_column_is_left_unchanged(self):
        connection = FakeConnection()
        cursor = FakeCursor(column_exists=True)

        ensure_administrator_default_site(connection, cursor)

        self.assertEqual(connection.commits, 0)
        self.assertFalse(any(sql.startswith('ALTER TABLE') for sql in cursor.executed))

    def test_missing_column_is_created_and_verified(self):
        connection = FakeConnection()
        cursor = FakeCursor(column_exists=False)

        ensure_administrator_default_site(connection, cursor)

        self.assertEqual(connection.commits, 1)
        self.assertTrue(any(sql.startswith('ALTER TABLE') for sql in cursor.executed))

    def test_failed_column_creation_stops_the_upgrade(self):
        connection = FakeConnection()
        cursor = FakeCursor(column_exists=False, alter_creates_column=False)

        with self.assertRaisesRegex(RuntimeError, 'defaultSite is missing'):
            ensure_administrator_default_site(connection, cursor)


if __name__ == '__main__':
    unittest.main()
