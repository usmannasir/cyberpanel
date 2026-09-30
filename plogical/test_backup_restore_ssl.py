"""Restoring an account must not depend on public certificate issuance."""
import ast
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch
from xml.etree import ElementTree

from plogical.backupMetadata import backup_includes_mail_domain


def load_method(filename, classname, methodname, namespace):
    source = Path(__file__).with_name(filename)
    cls = next(n for n in ast.parse(source.read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == classname)
    method = next(n for n in cls.body
                  if isinstance(n, ast.FunctionDef) and n.name == methodname)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace[methodname]


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
        hosts.createVirtualHost.side_effect = lambda *a, **kw: ((0, 'ACME validation failed')
            if a[4] or kw.get('configureMail', True) else (1, 'None'))
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

    def test_creation_can_defer_mail_setup_without_changing_the_default(self):
        hosts = Mock(redisConf='/redis-unused')
        hosts.dkimServicesInstalled.return_value = False
        package = Mock(enforceDiskLimits=False)
        vhost = Mock(Server_root='/lsws')
        vhost.createDirectoryForVirtualHost.return_value = (1, 'None')
        vhost.createConfigInMainVirtualHostFile.return_value = (1, 'None')
        namespace = dict(
            os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: False)),
            logging=Mock(), Administrator=Mock(), Package=Mock(),
            virtualHostUtilities=hosts, vhost=vhost, installUtilities=Mock(),
            mailUtilities=Mock(), DNS=Mock())
        namespace['Package'].objects.get.return_value = package
        create = load_method('virtualHostUtilities.py', 'virtualHostUtilities',
                             'createVirtualHost', namespace)
        args = ('example.test', 'admin@example.test', 'PHP 8.3', 'example',
                0, 1, 0, 'admin', 'Default', 0)
        self.assertEqual((1, 'None'), create(*args, LimitsCheck=0, configureMail=False))
        hosts.setupAutoDiscover.assert_not_called()
        self.assertEqual((1, 'None'), create(*args, LimitsCheck=0))
        hosts.setupAutoDiscover.assert_called_once()
        namespace['mailUtilities'].setupDKIM.assert_not_called()
        namespace['DNS'].createDKIMRecords.assert_not_called()

    def test_partial_mail_installation_does_not_touch_configuration_or_run_commands(self):
        present = {'/home/cyberpanel/postfix', '/etc/dovecot/dovecot.conf'}
        hosts = Mock()
        namespace = dict(
            os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: path in present,
                                                     isfile=lambda path: path in present)),
            virtualHostUtilities=hosts, logging=Mock(), ProcessUtilities=Mock(),
            sslUtilities=Mock(), open=Mock(side_effect=AssertionError('Unexpected config access')))
        hosts.emailServicesInstalled = load_method('virtualHostUtilities.py', 'virtualHostUtilities',
                                                   'emailServicesInstalled', namespace)
        setup = load_method('virtualHostUtilities.py', 'virtualHostUtilities', 'setupAutoDiscover', namespace)
        for mail_domain in (0, 1):
            setup(mail_domain, None, 'example.test', Mock())
        namespace['open'].assert_not_called()
        namespace['ProcessUtilities'].executioner.assert_not_called()
        namespace['sslUtilities'].issueSSLForDomain.assert_not_called()
        hosts.createDomain.assert_not_called()
        present.add('/etc/postfix/main.cf')
        self.assertTrue(hosts.emailServicesInstalled())
        present.remove('/etc/dovecot/dovecot.conf')
        self.assertFalse(hosts.emailServicesInstalled())

    def test_dkim_requires_configuration_keys_directory_and_the_selected_executable(self):
        hosts = Mock()
        namespace = dict(virtualHostUtilities=hosts, shutil=Mock(),
                         os=SimpleNamespace(path=Mock()),
                         ProcessUtilities=Mock(centos=1, cent8=2))
        installed = load_method('virtualHostUtilities.py', 'virtualHostUtilities',
                                'dkimServicesInstalled', namespace)
        hosts.emailServicesInstalled.return_value = False
        self.assertFalse(installed())
        namespace['shutil'].which.assert_not_called()
        hosts.emailServicesInstalled.return_value = True
        namespace['os'].path.isdir.return_value = False
        self.assertFalse(installed())
        namespace['shutil'].which.assert_not_called()
        namespace['os'].path.isdir.return_value = True
        namespace['ProcessUtilities'].decideDistro.return_value = 2
        namespace['shutil'].which.return_value = None
        self.assertFalse(installed())
        namespace['shutil'].which.assert_called_with('/usr/sbin/opendkim-genkey')
        namespace['shutil'].which.return_value = '/usr/sbin/opendkim-genkey'
        self.assertTrue(installed())
        namespace['ProcessUtilities'].decideDistro.return_value = 3
        self.assertTrue(installed())
        namespace['shutil'].which.assert_called_with('opendkim-genkey')

    def run_mail_restore(self, mail_services=True, certificates=True):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            extracted = root / 'fixture'
            extracted.mkdir()
            domains = ('example.test', 'mail.example.test')
            (extracted / 'meta.xml').write_text('''<metaFile>
                <masterDomain>example.test</masterDomain><phpSelection>PHP 8.3</phpSelection>
                <externalApp>example</externalApp><VERSION>3.0</VERSION><BUILD>7</BUILD>
                <ChildDomains><domain><domain>mail.example.test</domain>
                <phpSelection>PHP 8.3</phpSelection><path>/home/example.test/mail.example.test</path>
                </domain></ChildDomains></metaFile>''')
            if certificates:
                for domain in domains:
                    for name in ('cert.pem', 'fullchain.pem', 'privkey.pem'):
                        (extracted / (domain + '.' + name)).write_text(domain + '.' + name)

            # Map server paths into a fresh filesystem, including absent SSL parents.
            def local(path):
                path = str(path)
                return path if path.startswith(scratch) else str(root / 'server' / path.lstrip('/'))

            path_api = SimpleNamespace(join=os.path.join,
                                       exists=lambda path: os.path.exists(local(path)),
                                       isfile=lambda path: os.path.isfile(local(path)))
            fake_os = SimpleNamespace(path=path_api, getpid=os.getpid,
                                      mkdir=lambda path: os.mkdir(local(path)),
                                      makedirs=lambda path, **kw: os.makedirs(local(path), **kw))
            user = SimpleNamespace(userName='admin', email='admin@example.test')
            hosts = Mock()
            hosts.createDomain.return_value = (1, 'None')
            hosts.emailServicesInstalled.return_value = mail_services
            ssl = Mock()
            copied = []

            def copy_certificate(source, destination):
                shutil.copyfile(local(source), local(destination))
                copied.append(destination)

            def setup_mail(enabled, status, domain, admin):
                self.assertEqual(0, enabled)  # Existing domain only; no ACME or child creation.
                for name in ('fullchain.pem', 'privkey.pem'):
                    self.assertIn('/etc/letsencrypt/live/' + domain + '/' + name, copied)

            hosts.setupAutoDiscover.side_effect = setup_mail
            log = Mock()
            websites = Mock()
            websites.objects.filter.return_value.first.return_value = None
            namespace = dict(os=fake_os, ElementTree=ElementTree, tarfile=MagicMock(),
                             safe_extract=Mock(), logging=SimpleNamespace(CyberCPLogFileWriter=log),
                             Websites=websites, Administrator=Mock(), virtualHostUtilities=hosts,
                             backupUtilities=Mock(Server_root='/lsws'), sslUtilities=ssl,
                             ProcessUtilities=Mock(OLS=1), installUtilities=Mock(),
                             backup_includes_mail_domain=backup_includes_mail_domain,
                             backup_uses_full_directory_layout=lambda *args: True,
                             copy=copy_certificate)
            namespace['Administrator'].objects.get.return_value = user
            namespace['backupUtilities'].createWebsiteFromBackup.return_value = (1, 'None')
            restore = load_method('backupUtilities.py', 'backupUtilities', 'startRestore', namespace)
            modules = {'ApachController.ApacheController': Mock(),
                       'filemanager.filemanager': Mock()}
            with patch.dict('sys.modules', modules):
                restore(str(root / 'fixture.tar.gz'), 'CLI')
            self.assertEqual('Done', log.statusWriter.call_args.args[1])
            hosts.createDomain.assert_called_once_with(
                'example.test', 'mail.example.test', 'PHP 8.3',
                '/home/example.test/mail.example.test', 0, 0, 0, 'admin', 0)
            ssl.issueSSLForDomain.assert_not_called()
            hosts.issueSSL.assert_not_called()
            if certificates:
                self.assertEqual(list(domains), [call.args[0] for call in ssl.installSSLForDomain.call_args_list])
                for domain in domains:
                    self.assertEqual(domain + '.privkey.pem',
                        Path(local('/etc/letsencrypt/live/' + domain + '/privkey.pem')).read_text())
            expected = domains if mail_services and certificates else ()
            self.assertEqual(list(expected), [call.args[2] for call in hosts.setupAutoDiscover.call_args_list])

    def test_restores_mail_child_and_certificate_before_configuring_sni(self):
        self.run_mail_restore()

    def test_restore_does_not_configure_absent_mail_services(self):
        self.run_mail_restore(mail_services=False)

    def test_restore_does_not_reference_missing_certificates(self):
        self.run_mail_restore(certificates=False)


if __name__ == '__main__':
    unittest.main()
