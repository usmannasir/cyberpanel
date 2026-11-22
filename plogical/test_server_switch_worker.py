"""Switching a website to Apache reloads the shared PHP-FPM service instead of stopping it."""
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from plogical.test_server_switch_mail_php import method


class ServerSwitchWorkerTests(unittest.TestCase):
    def run_switch(self, child=False):
        master = NS(domain='example.test', adminEmail='owner@example.test', externalApp='testuser', state=1)
        website = Mock(domain='shop.example.test' if child else 'example.test', phpSelection='PHP 8.1',
                       adminEmail='owner@example.test', externalApp='testuser',
                       path='/home/example.test/shop', master=master, state=1)
        websites, children = Mock(), Mock()
        if child:
            websites.objects.get.side_effect = LookupError()
            children.objects.get.return_value = website
        else:
            websites.objects.get.return_value = website
        self.apache = Mock(fpmReload='reload-or-restart', serviceName='apache2')
        self.apache.fpmServiceCommand.side_effect = lambda action, selection: ['systemctl', action, '--', 'php-unit']
        self.process, self.logger = Mock(), Mock()
        controller = Mock()
        controller.checkIfApacheInstalled.return_value = 1
        switch = method('_switchServer', dict(
            Websites=websites, ChildDomains=children, logging=self.logger, vhost=Mock(Server_root='/usr/local/lsws'),
            os=os, sslUtilities=Mock(), ApacheVhost=self.apache, ApacheController=controller, PHPManager=Mock(),
            ProcessUtilities=self.process, installUtilities=Mock(), virtualHostUtilities=Mock(apache=1)))
        with patch('os.path.exists', return_value=False), patch('os.remove'):
            switch(website.domain, 'PHP 8.3', 1, '/unused')
        self.assertIn('[200]', self.logger.CyberCPLogFileWriter.statusWriter.call_args[0][1])

    def test_switch_to_apache_reloads_php_fpm_and_does_not_stop_it(self):
        for child in (False, True):
            with self.subTest(child=child):
                self.run_switch(child)
                self.assertEqual([('reload-or-restart', 'PHP 8.3')],
                                 [call[0] for call in self.apache.fpmServiceCommand.call_args_list])
                self.assertEqual([['systemctl', 'reload-or-restart', '--', 'php-unit'], 'systemctl restart apache2'],
                                 [call[0][0] for call in self.process.normalExecutioner.call_args_list])


if __name__ == '__main__':
    unittest.main()
