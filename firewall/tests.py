import json
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from firewall.firewallManager import FirewallManager


class ImunifyInstallEndpointTests(SimpleTestCase):

    @mock.patch(
        'plogical.imunify_integration.ensure_install_status_file',
        side_effect=OSError('status path is unavailable'),
    )
    @mock.patch(
        'firewall.firewallManager.logging.CyberCPLogFileWriter.statusWriter'
    )
    @mock.patch(
        'firewall.firewallManager.ACLManager.loadedACL',
        return_value={'admin': 1},
    )
    def test_imunifyav_start_failure_returns_json_instead_of_http_500(
        self, unused_acl, unused_log, unused_status
    ):
        request = SimpleNamespace(session={'userID': 1}, body=b'{}')

        response = FirewallManager(request).submitinstallImunifyAV()

        self.assertEqual(200, response.status_code)
        body = json.loads(response.content)
        self.assertEqual(0, body['status'])
        self.assertIn('installation log', body['error_message'])

    @mock.patch(
        'firewall.firewallManager.logging.CyberCPLogFileWriter.statusWriter'
    )
    @mock.patch(
        'firewall.firewallManager.ACLManager.loadedACL',
        return_value={'admin': 0},
    )
    def test_unauthorized_imunifyav_start_returns_json(
        self, unused_acl, unused_log
    ):
        request = SimpleNamespace(session={'userID': 1}, body=b'{}')

        response = FirewallManager(request).submitinstallImunifyAV()

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, json.loads(response.content)['status'])

# Create your tests here.
