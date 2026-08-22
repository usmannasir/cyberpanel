#!/usr/bin/env python3
"""
Tests for the installer's environment generation.

These cover the remote MySQL path reported in pull request #1772. They run
without root, without systemd, without network access, and write only inside a
temporary directory.

    python3 -m unittest install.test_env_generator -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env_generator import (  # noqa: E402
    DatabaseConfigError,
    LOCAL_DATABASE_CONFIG,
    build_mysql_client_config,
    build_database_config,
    create_env_file,
    format_env_value,
)


def parse_env(path):
    """Read a .env the way python-dotenv does, so the test asserts on the
    value Django would actually receive."""
    try:
        from dotenv import dotenv_values
        return dict(dotenv_values(path))
    except ImportError:
        values = {}
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, raw = line.partition('=')
                if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
                    raw = (raw[1:-1]
                           .replace('\\n', '\n')
                           .replace('\\r', '\r')
                           .replace('\\"', '"')
                           .replace('\\\\', '\\'))
                values[key.strip()] = raw
        return values


class BuildDatabaseConfigTests(unittest.TestCase):
    def test_local_mode_is_unchanged(self):
        self.assertEqual(build_database_config(remote=False),
                         LOCAL_DATABASE_CONFIG)

    def test_remote_moves_both_connections(self):
        config = build_database_config(
            remote=True, host='db.example.com', port='3307',
            root_db='mysql', root_user='cpadmin')
        self.assertEqual(config['db_host'], 'db.example.com')
        self.assertEqual(config['root_db_host'], 'db.example.com')
        self.assertEqual(config['db_port'], '3307')
        self.assertEqual(config['root_db_port'], '3307')
        self.assertEqual(config['root_db_user'], 'cpadmin')
        self.assertEqual(config['root_db_name'], 'mysql')
        # The application identity is fixed; --mysqluser is administrative only.
        self.assertEqual(config['db_user'], 'cyberpanel')
        self.assertEqual(config['db_name'], 'cyberpanel')

    def test_mysqldb_only_controls_the_administrative_database(self):
        config = build_database_config(
            remote=True, host='10.0.0.5', port='3306',
            root_db='adminmeta', root_user='root')
        self.assertEqual(config['root_db_name'], 'adminmeta')
        self.assertEqual(config['db_name'], 'cyberpanel')

    def test_port_is_never_folded_into_the_host(self):
        config = build_database_config(
            remote=True, host='db.example.com', port='3307',
            root_db='mysql', root_user='root')
        self.assertNotIn(':', config['db_host'])
        self.assertNotIn(':', config['root_db_host'])

    def test_ipv4_ipv6_and_dns_hosts(self):
        for given, expected in (
            ('192.0.2.10', '192.0.2.10'),
            ('2001:db8::5', '2001:db8::5'),
            ('[2001:db8::5]', '2001:db8::5'),
            ('db-01.internal.example', 'db-01.internal.example'),
        ):
            config = build_database_config(
                remote=True, host=given, port='3306',
                root_db='mysql', root_user='root')
            self.assertEqual(config['db_host'], expected)
            self.assertEqual(config['root_db_host'], expected)

    def test_missing_values_fail_before_anything_is_written(self):
        base = dict(remote=True, host='db.example.com', port='3306',
                    root_db='mysql', root_user='root')
        for field in ('host', 'root_db', 'root_user'):
            broken = dict(base, **{field: ''})
            with self.assertRaises(DatabaseConfigError):
                build_database_config(**broken)

    def test_invalid_ports_are_rejected(self):
        for port in ('0', '65536', 'abc', '33 06', '-1'):
            with self.assertRaises(DatabaseConfigError):
                build_database_config(
                    remote=True, host='db.example.com', port=port,
                    root_db='mysql', root_user='root')

    def test_empty_port_defaults_to_3306(self):
        config = build_database_config(
            remote=True, host='db.example.com', port='',
            root_db='mysql', root_user='root')
        self.assertEqual(config['db_port'], '3306')

    def test_host_with_whitespace_is_rejected(self):
        with self.assertRaises(DatabaseConfigError):
            build_database_config(
                remote=True, host='db.example.com extra', port='3306',
                root_db='mysql', root_user='root')

    def test_host_with_shell_syntax_or_folded_port_is_rejected(self):
        for host in ('db.example.com;id', 'db$(id)', "db'host",
                     'db.example.com:3306'):
            with self.assertRaises(DatabaseConfigError):
                build_database_config(
                    remote=True, host=host, port='3306',
                    root_db='mysql', root_user='root')


class FormatEnvValueTests(unittest.TestCase):
    def test_simple_values_stay_unquoted(self):
        for value in ('cyberpanel', 'localhost', '3306', 'AbC123xyz'):
            self.assertEqual(format_env_value(value), value)

    def test_values_needing_quotes_round_trip(self):
        awkward = [
            'pa#ss', 'pa ss', 'pa"ss', "pa'ss", 'pa\\ss', 'pa$ss',
            'pa`ss', ' leading', 'trailing ', 'a#b$c"d\\e f',
            'pa${HOME}ss',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, '.env')
            with open(path, 'w', encoding='utf-8') as handle:
                for index, value in enumerate(awkward):
                    handle.write('K%d=%s\n' % (index, format_env_value(value)))
            parsed = parse_env(path)
        for index, value in enumerate(awkward):
            self.assertEqual(parsed['K%d' % index], value,
                             'value %r did not survive the .env round trip'
                             % (value,))


class MySQLClientConfigTests(unittest.TestCase):
    def test_local_config_keeps_socket_defaults(self):
        rendered = build_mysql_client_config('RootPw123')
        self.assertIn('[client]\n', rendered)
        self.assertIn('user=root\n', rendered)
        self.assertIn('password="RootPw123"\n', rendered)
        self.assertNotIn('host=', rendered)
        self.assertNotIn('port=', rendered)
        self.assertNotIn('protocol=', rendered)

    def test_remote_config_uses_the_administrative_endpoint(self):
        rendered = build_mysql_client_config(
            'RemotePw123', remote=True, host='db.example.com', port='3307',
            user='cpadmin')
        self.assertIn('user="cpadmin"\n', rendered)
        self.assertIn('host="db.example.com"\n', rendered)
        self.assertIn('port=3307\n', rendered)
        self.assertIn('protocol=TCP\n', rendered)
        self.assertNotIn('user=root\n', rendered)

    def test_option_values_are_escaped_and_single_line(self):
        rendered = build_mysql_client_config(
            'a"b\\c', remote=True, host='2001:db8::5', port='3306',
            user='cpadmin')
        self.assertIn('password="a\\"b\\\\c"\n', rendered)
        with self.assertRaises(DatabaseConfigError):
            build_mysql_client_config(
                'password\nextra=1', remote=True, host='db.example.com',
                port='3306', user='cpadmin')


class CreateEnvFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

        # ALLOWED_HOSTS detection reaches out to public IP services. Stub it so
        # the suite is genuinely offline and does not pause on socket timeouts.
        import env_generator
        for name, stub in (('get_public_ip', lambda: '198.51.100.7'),
                           ('get_local_ip', lambda: '10.0.0.7')):
            original = getattr(env_generator, name)
            setattr(env_generator, name, stub)
            self.addCleanup(setattr, env_generator, name, original)

    def _write(self, **kwargs):
        create_env_file(self.path, 'RootPw123', 'AppPw456', **kwargs)
        return parse_env(os.path.join(self.path, '.env'))

    def test_local_install_keeps_the_previous_values(self):
        values = self._write()
        self.assertEqual(values['DB_NAME'], 'cyberpanel')
        self.assertEqual(values['DB_USER'], 'cyberpanel')
        self.assertEqual(values['DB_HOST'], 'localhost')
        self.assertEqual(values['DB_PORT'], '3306')
        self.assertEqual(values['ROOT_DB_NAME'], 'mysql')
        self.assertEqual(values['ROOT_DB_USER'], 'root')
        self.assertEqual(values['ROOT_DB_HOST'], 'localhost')
        self.assertEqual(values['ROOT_DB_PORT'], '3306')

    def test_passwords_land_in_their_own_connections(self):
        values = self._write()
        self.assertEqual(values['DB_PASSWORD'], 'AppPw456')
        self.assertEqual(values['ROOT_DB_PASSWORD'], 'RootPw123')

    def test_remote_install_writes_the_remote_endpoint(self):
        config = build_database_config(
            remote=True, host='db.example.com', port='3307',
            root_db='mysql', root_user='cpadmin')
        values = self._write(database_config=config)
        self.assertEqual(values['DB_HOST'], 'db.example.com')
        self.assertEqual(values['DB_PORT'], '3307')
        self.assertEqual(values['ROOT_DB_HOST'], 'db.example.com')
        self.assertEqual(values['ROOT_DB_PORT'], '3307')
        self.assertEqual(values['ROOT_DB_USER'], 'cpadmin')

    def test_awkward_passwords_survive(self):
        raw_root = 'r#o ot"pw\\1$x'
        raw_app = "app'pw #2 `x"
        create_env_file(self.path, raw_root, raw_app)
        values = parse_env(os.path.join(self.path, '.env'))
        self.assertEqual(values['ROOT_DB_PASSWORD'], raw_root)
        self.assertEqual(values['DB_PASSWORD'], raw_app)

    def test_env_file_is_not_world_readable(self):
        self._write()
        mode = os.stat(os.path.join(self.path, '.env')).st_mode & 0o777
        self.assertEqual(mode & 0o007, 0,
                         '.env must not be readable by other accounts')

    def test_incomplete_config_is_rejected(self):
        with self.assertRaises(DatabaseConfigError):
            create_env_file(self.path, 'a', 'b',
                            database_config={'db_host': 'x'})

    def test_credentials_are_not_printed(self):
        import io
        from contextlib import redirect_stdout
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            create_env_file(self.path, 'SuperSecretRoot', 'SuperSecretApp')
        printed = buffer.getvalue()
        self.assertNotIn('SuperSecretRoot', printed)
        self.assertNotIn('SuperSecretApp', printed)


if __name__ == '__main__':
    unittest.main()
