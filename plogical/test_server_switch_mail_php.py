"""Regression coverage for server switching and mail child runtime selection."""
import ast
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def method(name, namespace):
    path = Path(__file__).with_name('virtualHostUtilities.py')
    cls = next(n for n in ast.parse(path.read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == 'virtualHostUtilities')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class MailPHPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.websites = Mock()
        self.websites.objects.get.return_value.phpSelection = 'PHP 8.3'
        self.php = Mock()
        self.php.findPHPVersions.return_value = ['PHP 7.3', 'PHP 8.4', 'PHP 8.3']
        self.php.getPHPString.side_effect = lambda value: value[4:].replace('.', '')
        self.select = method('installedMailPHPVersion', dict(
            Websites=self.websites, PHPManager=self.php, os=os, re=re,
            virtualHostUtilities=SimpleNamespace(Server_root=str(self.root))))

    def runtime(self, version, executable=True):
        path = self.root / ('lsphp' + version) / 'bin' / 'lsphp'
        path.parent.mkdir(parents=True)
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755 if executable else 0o644)

    def test_parent_runtime_preferred_even_when_newer_installed(self):
        self.runtime('83'); self.runtime('84')
        self.assertEqual('PHP 8.3', self.select('example.test'))

    def test_missing_parent_uses_newest_executable(self):
        self.runtime('84')
        self.assertEqual('PHP 8.4', self.select('example.test'))

    def test_rejects_fallback_list_without_real_binaries(self):
        with self.assertRaisesRegex(ValueError, 'No installed executable PHP'):
            self.select('example.test')

    def test_nonexecutable_runtime_not_selected(self):
        self.runtime('83', executable=False); self.runtime('84')
        self.assertEqual('PHP 8.4', self.select('example.test'))

    def test_numeric_versions_sorted_correctly(self):
        self.php.findPHPVersions.return_value = ['PHP 8.9', 'PHP 8.10']
        self.runtime('89'); self.runtime('810')
        self.assertEqual('PHP 8.10', self.select('example.test'))

    def test_autodiscover_passes_selected_version_to_creation(self):
        host = Mock()
        host.emailServicesInstalled.return_value = True
        host.hasUsableMailTLS.side_effect = [True, False]
        host.installedMailPHPVersion.return_value = 'PHP 8.4'
        host.createDomain.return_value = (1, 'None')
        setup = method('setupAutoDiscover', dict(
            virtualHostUtilities=host, logging=Mock(), sslUtilities=Mock(),
            os=os, randint=lambda a, b: a, ProcessUtilities=Mock()))
        with patch('os.path.exists', return_value=False):
            setup(True, '/unused', 'example.test', SimpleNamespace(userName='admin'))
        self.assertEqual('PHP 8.4', host.createDomain.call_args.args[2])


class ServerSwitchTests(unittest.TestCase):
    def run_switch(self, child=True, ssl=True, ssl_result=1, server=2):
        website = Mock(phpSelection='PHP 8.1', adminEmail='owner@example.test',
                       externalApp='testuser', path='/home/example.test/child')
        website.master = SimpleNamespace(domain='example.test', adminEmail='owner@example.test', externalApp='testuser')
        websites, children = Mock(), Mock()
        if child:
            websites.objects.get.side_effect = LookupError()
            children.objects.get.return_value = website
        else:
            websites.objects.get.return_value = website
        tls, logger = Mock(), Mock()
        tls.sslUtilities.installSSLForDomain.return_value = ssl_result
        vhost, apache = Mock(), Mock()
        vhost.Server_root = '/usr/local/lsws'
        switch = method('switchServer', dict(
            Websites=websites, ChildDomains=children, logging=logger, vhost=vhost,
            os=os, sslUtilities=tls, ApacheVhost=apache, ApacheController=Mock(),
            PHPManager=Mock(), ProcessUtilities=Mock(), installUtilities=Mock(),
            virtualHostUtilities=SimpleNamespace(apache=1)))
        with patch('os.path.exists', return_value=ssl), patch('os.remove'):
            switch('child.example.test' if child else 'example.test', 'PHP 8.3', server, '/unused')
        return website, tls, logger, vhost

    def test_child_switch_preserves_ssl_and_saves_selected_php(self):
        website, tls, logger, vhost = self.run_switch()
        self.assertEqual('PHP 8.3', website.phpSelection)
        website.save.assert_called_once_with(update_fields=['phpSelection'])
        tls.sslUtilities.installSSLForDomain.assert_called_once_with('child.example.test', 'owner@example.test')
        self.assertIn('[200]', logger.CyberCPLogFileWriter.statusWriter.call_args.args[1])

    def test_master_switch_saves_selected_php_and_preserves_ssl(self):
        website, tls, logger, vhost = self.run_switch(child=False)
        self.assertEqual('PHP 8.3', website.phpSelection)
        tls.sslUtilities.installSSLForDomain.assert_called_once_with('example.test', 'owner@example.test')

    def test_no_certificate_does_not_install_ssl(self):
        website, tls, logger, vhost = self.run_switch(ssl=False)
        tls.sslUtilities.installSSLForDomain.assert_not_called()
        website.save.assert_called_once()

    def test_ssl_failure_is_not_reported_as_success(self):
        website, tls, logger, vhost = self.run_switch(ssl_result=0)
        website.save.assert_not_called()
        self.assertIn('[404]', logger.CyberCPLogFileWriter.statusWriter.call_args.args[1])

    def test_apache_switch_also_saves_selected_php(self):
        website, tls, logger, vhost = self.run_switch(server=1)
        self.assertEqual('PHP 8.3', website.phpSelection)
        website.save.assert_called_once_with(update_fields=['phpSelection'])


if __name__ == '__main__':
    unittest.main()
