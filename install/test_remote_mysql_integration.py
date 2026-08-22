#!/usr/bin/env python3
"""
Integration coverage for the remote MySQL installation path (#1772).

The unit tests prove the generated .env *says* the right thing. These prove a
real MySQL server on a non-default port actually accepts the values that end
up in that file, which is the part the pull request was about: before the fix,
create_env_file() hardcoded localhost:3306 and the remote endpoint never
reached Django at all.

A server is required. Point the suite at one with:

    CP_TEST_MYSQL_HOST=127.0.0.1 \\
    CP_TEST_MYSQL_PORT=33306 \\
    CP_TEST_MYSQL_ROOT_USER=root \\
    CP_TEST_MYSQL_ROOT_PASSWORD='...' \\
    python3 -m unittest install.test_remote_mysql_integration -v

Every test is skipped when those are absent or the server is unreachable, so
the suite stays safe to run anywhere. Nothing outside the throwaway database
is touched.
"""

import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env_generator import build_database_config, create_env_file  # noqa: E402
from test_env_generator import parse_env  # noqa: E402

HOST = os.environ.get('CP_TEST_MYSQL_HOST')
PORT = os.environ.get('CP_TEST_MYSQL_PORT')
ROOT_USER = os.environ.get('CP_TEST_MYSQL_ROOT_USER', 'root')
ROOT_PASSWORD = os.environ.get('CP_TEST_MYSQL_ROOT_PASSWORD')


def _client():
    try:
        import MySQLdb
        return MySQLdb
    except ImportError:
        try:
            import pymysql
            return pymysql
        except ImportError:
            return None


MYSQL = _client()


def _reachable():
    if not (HOST and PORT and ROOT_PASSWORD and MYSQL):
        return False
    try:
        conn = MYSQL.connect(host=HOST, port=int(PORT), user=ROOT_USER,
                             passwd=ROOT_PASSWORD, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


REASON = ('set CP_TEST_MYSQL_HOST/PORT/ROOT_PASSWORD and install a MySQL '
          'client to run the remote installation tests')


@unittest.skipUnless(_reachable(), REASON)
class RemoteMySQLInstallationTests(unittest.TestCase):
    """Walk the installer's configuration path against a live server."""

    @classmethod
    def setUpClass(cls):
        cls.suffix = uuid.uuid4().hex[:8]
        cls.db_name = 'cptest_%s' % cls.suffix
        cls.db_user = 'cpuser_%s' % cls.suffix
        # Deliberately awkward: a '#' would start a comment and a space would
        # truncate the value if .env were written without quoting.
        cls.db_password = 'App#pw %s$x' % cls.suffix

        cls.admin = MYSQL.connect(host=HOST, port=int(PORT), user=ROOT_USER,
                                  passwd=ROOT_PASSWORD, connect_timeout=10)
        cursor = cls.admin.cursor()
        cursor.execute('CREATE DATABASE `%s`' % cls.db_name)
        cursor.execute("CREATE USER %s@'%%' IDENTIFIED BY %s",
                       (cls.db_user, cls.db_password))
        # Identifiers cannot be bound, and both are generated from a uuid, so
        # the statement is built directly. No arguments are passed, so the
        # driver does no '%' interpolation on the host wildcard.
        cursor.execute("GRANT ALL PRIVILEGES ON `%s`.* TO '%s'@'%%'"
                       % (cls.db_name, cls.db_user))
        cursor.execute('FLUSH PRIVILEGES')
        cursor.close()
        cls.admin.commit()

    @classmethod
    def tearDownClass(cls):
        cursor = cls.admin.cursor()
        cursor.execute('DROP DATABASE IF EXISTS `%s`' % cls.db_name)
        cursor.execute("DROP USER IF EXISTS %s@'%%'", (cls.db_user,))
        cursor.execute('FLUSH PRIVILEGES')
        cursor.close()
        cls.admin.commit()
        cls.admin.close()

    def _generate_env(self):
        """Run the installer's generation path and return the parsed .env."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        import env_generator
        for name, stub in (('get_public_ip', lambda: '198.51.100.7'),
                           ('get_local_ip', lambda: '10.0.0.7')):
            original = getattr(env_generator, name)
            setattr(env_generator, name, stub)
            self.addCleanup(setattr, env_generator, name, original)

        config = build_database_config(
            remote=True, host=HOST, port=PORT,
            root_db='mysql', root_user=ROOT_USER)
        create_env_file(tmp.name, ROOT_PASSWORD, self.db_password,
                        database_config=config)
        return parse_env(os.path.join(tmp.name, '.env'))

    def test_generated_admin_credentials_connect_to_the_remote_server(self):
        values = self._generate_env()
        conn = MYSQL.connect(
            host=values['ROOT_DB_HOST'],
            port=int(values['ROOT_DB_PORT']),
            user=values['ROOT_DB_USER'],
            passwd=values['ROOT_DB_PASSWORD'],
            db=values['ROOT_DB_NAME'],
            connect_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor.close()
        conn.close()

    def test_generated_application_credentials_connect_to_the_remote_server(self):
        values = self._generate_env()
        # The installer fixes the application identity; only the endpoint and
        # the password come from the generated file, so substitute the
        # throwaway account this test created on the same server.
        conn = MYSQL.connect(
            host=values['DB_HOST'],
            port=int(values['DB_PORT']),
            user=self.db_user,
            passwd=values['DB_PASSWORD'],
            db=self.db_name,
            connect_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute('SELECT DATABASE()')
        self.assertEqual(cursor.fetchone()[0], self.db_name)
        cursor.close()
        conn.close()

    def test_password_with_shell_metacharacters_survives_to_the_server(self):
        """The escaping fix, proven end to end rather than by re-parsing."""
        values = self._generate_env()
        self.assertEqual(values['DB_PASSWORD'], self.db_password)
        conn = MYSQL.connect(host=values['DB_HOST'],
                             port=int(values['DB_PORT']),
                             user=self.db_user,
                             passwd=values['DB_PASSWORD'],
                             db=self.db_name, connect_timeout=10)
        conn.close()

    def test_endpoint_is_the_remote_server_not_localhost(self):
        """The regression itself. A generated file that still said
        localhost:3306 would connect to whatever is on the installing host —
        or nothing — and the remote server would never be used."""
        values = self._generate_env()
        self.assertEqual(values['DB_HOST'], HOST)
        self.assertEqual(values['DB_PORT'], str(PORT))
        self.assertEqual(values['ROOT_DB_HOST'], HOST)
        self.assertEqual(values['ROOT_DB_PORT'], str(PORT))
        self.assertNotEqual(str(PORT), '3306',
                            'run this against a non-default port so the '
                            'assertion can distinguish the fix from the bug')

    def test_django_settings_resolve_to_the_remote_endpoint(self):
        """Load the generated file the way CyberCP/settings.py does and check
        the values Django would put in DATABASES."""
        try:
            from dotenv import dotenv_values
        except ImportError:
            self.skipTest('python-dotenv is not installed')

        values = self._generate_env()
        del values
        import env_generator
        for name, stub in (('get_public_ip', lambda: '198.51.100.7'),
                           ('get_local_ip', lambda: '10.0.0.7')):
            original = getattr(env_generator, name)
            setattr(env_generator, name, stub)
            self.addCleanup(setattr, env_generator, name, original)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        config = build_database_config(
            remote=True, host=HOST, port=PORT,
            root_db='mysql', root_user=ROOT_USER)
        create_env_file(tmp.name, ROOT_PASSWORD, self.db_password,
                        database_config=config)

        env = dotenv_values(os.path.join(tmp.name, '.env'))
        default = {
            'NAME': env.get('DB_NAME', 'cyberpanel'),
            'USER': env.get('DB_USER', 'cyberpanel'),
            'PASSWORD': env.get('DB_PASSWORD', ''),
            'HOST': env.get('DB_HOST', 'localhost'),
            'PORT': env.get('DB_PORT', '3306'),
        }
        rootdb = {
            'NAME': env.get('ROOT_DB_NAME', 'mysql'),
            'USER': env.get('ROOT_DB_USER', 'root'),
            'PASSWORD': env.get('ROOT_DB_PASSWORD', ''),
            'HOST': env.get('ROOT_DB_HOST', 'localhost'),
            'PORT': env.get('ROOT_DB_PORT', '3306'),
        }
        self.assertEqual(default['HOST'], HOST)
        self.assertEqual(default['PORT'], str(PORT))
        self.assertEqual(rootdb['HOST'], HOST)
        self.assertEqual(rootdb['PORT'], str(PORT))
        self.assertEqual(rootdb['USER'], ROOT_USER)
        self.assertEqual(default['PASSWORD'], self.db_password)


if __name__ == '__main__':
    unittest.main()
