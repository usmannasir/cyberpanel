"""Restoring an account must not depend on public certificate issuance."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from xml.etree import ElementTree

from plogical.backupMetadata import backup_includes_mail_domain


class RestoreSSLTests(unittest.TestCase):
    def test_restore_before_dns_cutover_can_create_account_and_database(self):
        source = Path(__file__).with_name('backupUtilities.py')
        cls = next(n for n in ast.parse(source.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'backupUtilities')
        method = next(n for n in cls.body
                      if isinstance(n, ast.FunctionDef) and n.name == 'createWebsiteFromBackup')
        method.decorator_list = []
        user = SimpleNamespace(userName='admin', email='admin@example.test')
        website = object()
        hosts = Mock()
        # Model the real failure when DNS still points to the original server.
        hosts.createVirtualHost.side_effect = lambda *a: ((0, 'ACME validation failed')
                                                        if a[4] else (1, 'None'))
        databases = Mock()
        databases.createDatabaseAndRegister.return_value = (1, 'None')
        dns = Mock()
        namespace = dict(os=os, ElementTree=ElementTree,
                         Administrator=SimpleNamespace(objects=Mock(get=Mock(return_value=user))),
                         Websites=SimpleNamespace(objects=Mock(get=Mock(return_value=website))),
                         ChildDomains=SimpleNamespace(objects=Mock()),
                         virtualHostUtilities=hosts, DNS=dns,
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=databases),
                         backup_includes_mail_domain=backup_includes_mail_domain,
                         backup_uses_database_users_schema=lambda *args: False)
        namespace['Websites'].objects.filter.return_value.count.return_value = 0
        namespace['ChildDomains'].objects.filter.return_value.count.return_value = 0
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        with tempfile.TemporaryDirectory() as scratch:
            archive = Path(scratch) / 'fixture.tar.gz'
            archive.touch()
            extracted = Path(scratch) / 'fixture'
            extracted.mkdir()
            (extracted / 'meta.xml').write_text('''<metaFile>
                <masterDomain>example.test</masterDomain><phpSelection>PHP 8.3</phpSelection>
                <externalApp>example</externalApp><VERSION>3.0</VERSION><BUILD>7</BUILD>
                <Databases><database><dbName>example_db</dbName><dbUser>example_user</dbUser>
                </database></Databases></metaFile>''')
            self.assertEqual(namespace['createWebsiteFromBackup'](str(archive), 'fixture'), (1, 'None'))
        databases.createDatabaseAndRegister.assert_called_once_with(
            'example_db', 'example_user', 'cyberpanel', website)
        dns.createDNSZone.assert_called_once_with('example.test', user)


if __name__ == '__main__':
    unittest.main()
