"""The platform is told to call this panel back for a scan at the panel's own address, not at whatever a request names."""
import json
from types import SimpleNamespace
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from aiScanner.aiScannerManager import AIScannerManager


class Missing(Exception):
    pass


class PanelAddressTests(SimpleTestCase):

    def setUp(self):
        self.admin = SimpleNamespace(pk=7, userName='owner', email='owner@example.com')
        self.acl = {'admin': 0}
        # panel.example.net is the server's own site; shop.example.org belongs to the signed-in user.
        self.sites = {'panel.example.net': 0, 'shop.example.org': 1}
        for target, value in (
                ('plogical.acl.ACLManager.loadedACL', lambda userID: self.acl),
                ('plogical.acl.ACLManager.fetchIP', lambda: '203.0.113.10'),
                ('plogical.acl.ACLManager.checkOwnership', lambda domain, admin, acl: self.sites.get(domain, 0)),
                ('aiScanner.panel_address.panel_port', lambda: '8090'),
                ('aiScanner.panel_address.names_a_website', lambda hostname: hostname in self.sites),
        ):
            patcher = mock.patch(target, side_effect=value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

    def address(self, host):
        from aiScanner.panel_address import panel_address
        request = RequestFactory().get('/aiscanner/', HTTP_HOST=host)
        return panel_address(request, self.admin, self.acl)

    def test_a_user_who_is_no_administrator_always_gets_the_servers_own_address(self):
        # panel.example.net and other.example.org are websites of other accounts on this panel.
        self.sites['other.example.org'] = 0
        for host in ('203.0.113.10:8090', '203.0.113.10', 'panel.example.net:8090', 'panel.example.net',
                     'panel.example.net:443', 'other.example.org:8090', 'shop.example.org:8090',
                     'collector.example.com', '198.51.100.7:8090', 'a b', ''):
            self.assertEqual('203.0.113.10:8090', self.address(host), host)

    def test_for_an_administrator_the_servers_own_address_and_port_are_used_as_given(self):
        self.acl = {'admin': 1}
        self.assertEqual('203.0.113.10:8090', self.address('203.0.113.10:8090'))
        self.assertEqual('203.0.113.10', self.address('203.0.113.10'))

    def test_for_an_administrator_the_name_of_a_website_on_this_panel_is_used(self):
        self.acl = {'admin': 1}
        self.assertEqual('panel.example.net:8090', self.address('panel.example.net:8090'))
        self.assertEqual('panel.example.net:8090', self.address('PANEL.example.net:8090'))
        self.assertEqual('panel.example.net', self.address('panel.example.net'))
        self.assertEqual('panel.example.net:443', self.address('panel.example.net:443'))
        self.assertEqual('shop.example.org:8090', self.address('shop.example.org:8090'))

    def test_for_an_administrator_any_other_host_or_port_becomes_the_servers_own_address(self):
        self.acl = {'admin': 1}
        for host in ('collector.example.com', 'collector.example.com:8090', '198.51.100.7:8090',
                     'localhost:8090', '127.0.0.1:8090', 'panel.example.net:22', '203.0.113.10:9999',
                     'panel.example.net@collector.example.com', 'a b', ''):
            self.assertEqual('203.0.113.10:8090', self.address(host), host)

    def start_scan(self, host):
        manager = AIScannerManager()
        submitted = {}

        def submit(api_key, domain, scan_type, callback_url, token, base_url, scan_id, server_ip):
            submitted.update(callback_url=callback_url, base_url=base_url)
            return 'platform-scan'

        website = SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(
            get=lambda domain: SimpleNamespace(domain=domain, externalApp='shope1234')))
        request = RequestFactory().post('/aiscanner/start-scan/', data=json.dumps({'domain': 'shop.example.org'}),
                                        content_type='application/json', HTTP_HOST=host)
        request.session = {'userID': 7}
        with mock.patch('aiScanner.aiScannerManager.Administrator',
                        SimpleNamespace(objects=SimpleNamespace(get=lambda pk: self.admin))), \
                mock.patch('aiScanner.aiScannerManager.AIScannerSettings', SimpleNamespace(
                    DoesNotExist=Missing, objects=SimpleNamespace(get=lambda admin: SimpleNamespace(
                        is_payment_configured=True, api_key='cp_key')))), \
                mock.patch('aiScanner.aiScannerManager.ScanHistory') as scans, \
                mock.patch('aiScanner.aiScannerManager.FileAccessToken'), \
                mock.patch('websiteFunctions.models.Websites', website), \
                mock.patch.object(manager, 'check_vps_free_scans', return_value={'success': False}), \
                mock.patch.object(manager, 'submit_wordpress_scan', side_effect=submit):
            scans.SCAN_TYPE_CHOICES = [('full', 'Full Scan')]
            response = manager.startScan(request, 7)
        self.assertTrue(json.loads(response.content.decode('utf-8'))['success'])
        return submitted

    def test_a_scan_started_by_a_user_is_called_back_at_the_server_whatever_name_the_request_bears(self):
        for host in ('collector.example.com:8090', 'shop.example.org:8090', 'panel.example.net:8090'):
            self.assertEqual({'callback_url': 'https://203.0.113.10:8090/api/ai-scanner/callback',
                              'base_url': 'https://203.0.113.10:8090/api/ai-scanner/'}, self.start_scan(host))

    def test_a_scan_started_by_an_administrator_under_the_panels_name_is_called_back_there(self):
        self.acl = {'admin': 1}
        self.assertEqual({'callback_url': 'https://panel.example.net:8090/api/ai-scanner/callback',
                          'base_url': 'https://panel.example.net:8090/api/ai-scanner/'},
                         self.start_scan('panel.example.net:8090'))
        self.assertEqual({'callback_url': 'https://203.0.113.10:8090/api/ai-scanner/callback',
                          'base_url': 'https://203.0.113.10:8090/api/ai-scanner/'},
                         self.start_scan('collector.example.com:8090'))
