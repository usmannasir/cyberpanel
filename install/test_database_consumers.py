#!/usr/bin/env python3
"""Regression tests for remote-database service consumers."""

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import installCyberPanel  # noqa: E402
from database_consumers import (  # noqa: E402
    DatabaseConsumerConfigError,
    configure_phpmyadmin_signon,
    dovecot_connect_line,
    render_phpmyadmin_signon,
)


class RemoteClientPackageTests(unittest.TestCase):
    def _installer(self, distro):
        return installCyberPanel.InstallCyberPanel(
            '/usr/local/lsws/', '/tmp', distro, 0,
            remotemysql='ON', mysqlhost='db.example.com', mysqlport='3307')

    def test_remote_ubuntu_installs_only_the_client(self):
        installer = self._installer(installCyberPanel.ubuntu)
        with mock.patch.object(installCyberPanel.install_utils, 'call') as call:
            installer.installMySQL('One')
        command = call.call_args.args[0]
        self.assertIn('mariadb-client', command)
        self.assertNotIn('mariadb-server', command)

    def test_remote_rhel_installs_only_the_client(self):
        installer = self._installer(installCyberPanel.cent8)
        with mock.patch.object(installCyberPanel.install_utils, 'call') as call:
            installer.installMySQL('One')
        self.assertEqual('dnf install mariadb -y', call.call_args.args[0])

    def test_phpmyadmin_setup_does_not_interpolate_host_into_shell(self):
        installer_source = pathlib.Path(
            installCyberPanel.__file__).with_name('install.py').read_text(
                encoding='utf-8')
        self.assertNotIn("sed -i 's|'localhost'|'%s'", installer_source)


class DovecotConsumerTests(unittest.TestCase):
    def test_remote_endpoint_replaces_legacy_local_defaults(self):
        line = dovecot_connect_line(
            'application-password', remote=True,
            host='db.example.com', port='3307')
        self.assertIn('host=db.example.com', line)
        self.assertIn('port=3307', line)
        self.assertNotIn('host=localhost', line)

    def test_local_endpoints_are_unchanged(self):
        self.assertIn(
            'host=localhost',
            dovecot_connect_line('password', mysql='One'),
        )
        two = dovecot_connect_line('password', mysql='Two')
        self.assertIn('host=127.0.0.1', two)
        self.assertIn('port=3307', two)


class PhpMyAdminConsumerTests(unittest.TestCase):
    template = """<?php
        $_SESSION['PMA_single_signon_host'] = 'localhost';
        $_SESSION['PMA_single_signon_port'] = 3306;
"""

    def test_remote_host_and_non_default_port_are_written(self):
        rendered = render_phpmyadmin_signon(
            self.template, 'db.example.com', '3307')
        self.assertIn("host'] = 'db.example.com';", rendered)
        self.assertIn("port'] = 3307;", rendered)

    def test_old_script_without_port_is_upgraded(self):
        rendered = render_phpmyadmin_signon(
            self.template.replace(
                "        $_SESSION['PMA_single_signon_port'] = 3306;\n", ''),
            '2001:db8::5', 4406)
        self.assertIn("host'] = '2001:db8::5';", rendered)
        self.assertIn("port'] = 4406;", rendered)

    def test_host_is_php_quoted_without_shell_interpolation(self):
        rendered = render_phpmyadmin_signon(
            self.template, "db'\\server$NAME", 3306)
        self.assertIn("'db\\'\\\\server$NAME'", rendered)

    def test_invalid_endpoint_is_rejected(self):
        for host, port in (('', 3306), ('db\nname', 3306), ('db', 0),
                           ('db', 65536), ('db', 'not-a-port')):
            with self.assertRaises(DatabaseConsumerConfigError):
                render_phpmyadmin_signon(self.template, host, port)

    def test_file_update_is_atomic_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'phpmyadminsignin.php'
            path.write_text(self.template, encoding='utf-8')
            path.chmod(0o640)
            configure_phpmyadmin_signon(str(path), 'db.example.com', 3307)
            self.assertEqual(0o640, path.stat().st_mode & 0o777)
            self.assertIn("port'] = 3307;", path.read_text(encoding='utf-8'))

            link = pathlib.Path(directory) / 'signin-link.php'
            link.symlink_to(path)
            with self.assertRaises(DatabaseConsumerConfigError):
                configure_phpmyadmin_signon(str(link), 'db.example.com', 3307)


if __name__ == '__main__':
    unittest.main()
