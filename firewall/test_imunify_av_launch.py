import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
import django
django.setup()
from django.test import RequestFactory
from firewall.views import submitinstallImunifyAV
from serverStatus.views import switchTOLSWSStatus
from serverStatus.serverStatusUtil import ServerStatusUtil


class ImunifyAVLaunchTests(unittest.TestCase):
    def patch(self, patcher):
        self.addCleanup(patcher.stop)
        return patcher.start()

    def setUp(self):
        self.request = RequestFactory().post('/firewall/submitinstallImunifyAV', '{}',
                                             content_type='application/json')
        self.request.session = {'userID': 1}
        self.acl = self.patch(mock.patch(
            'firewall.firewallManager.ACLManager.loadedACL', return_value={'admin': 1}))
        self.status = self.patch(mock.patch(
            'plogical.imunify_integration.ensure_install_status_file'))
        self.command = self.patch(mock.patch(
            'plogical.imunify_integration.build_install_worker_command', return_value='worker-command'))
        self.launch = self.patch(mock.patch(
            'firewall.firewallManager.ProcessUtilities.popenExecutioner'))
        self.log = self.patch(mock.patch(
            'firewall.firewallManager.logging.CyberCPLogFileWriter.statusWriter'))

    def payload(self):
        response = submitinstallImunifyAV(self.request)
        self.assertIsNotNone(response, 'The view must return an HTTP response')
        self.assertEqual(200, response.status_code)
        return json.loads(response.content)

    def test_status_preparation_error_returns_json_instead_of_none(self):
        self.status.side_effect = OSError('status file unavailable')
        payload = self.payload()
        self.assertEqual(0, payload['status'])
        self.assertIn('status file unavailable', payload['error_message'])
        self.launch.assert_not_called()

    def test_launcher_error_returns_json_even_when_status_logging_fails(self):
        self.launch.side_effect = RuntimeError('could not start worker')
        self.log.side_effect = OSError('cannot write status')
        payload = self.payload()
        self.assertEqual(0, payload['status'])
        self.assertIn('could not start worker', payload['error_message'])

    def test_unicode_error_message_survives_json_response(self):
        self.status.side_effect = ValueError('installation failed: café')
        self.assertEqual('installation failed: café', self.payload()['error_message'])

    def test_unauthorized_request_does_not_overwrite_install_status(self):
        self.acl.return_value = {'admin': 0}
        self.assertEqual(0, self.payload()['status'])
        self.status.assert_not_called()
        self.log.assert_not_called()
        self.launch.assert_not_called()

    def test_success_starts_one_worker_with_checked_launch(self):
        self.assertEqual(1, self.payload()['status'])
        self.status.assert_called_once_with(reset=True)
        self.command.assert_called_once_with('av')
        self.launch.assert_called_once_with('worker-command', raise_errors=True)

    def test_status_poll_preserves_success_marker_in_non_ascii_installer_output(self):
        real_open = open

        def ascii_default(path, mode='r', *args, **kwargs):
            if 'b' not in mode:
                kwargs.setdefault('encoding', 'ascii')
            return real_open(path, mode, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'status.log'
            path.write_bytes('Installation café '.encode('utf-8') + b'\xff [200]\n')
            with mock.patch.object(ServerStatusUtil, 'lswsInstallStatusPath', str(path)), \
                    mock.patch('builtins.open', side_effect=ascii_default):
                response = switchTOLSWSStatus(self.request)
            payload = json.loads(response.content)
            self.assertEqual(1, payload['status'])
            self.assertEqual(1, payload['installed'])
            self.assertIn('café', payload['requestStatus'])


if __name__ == '__main__':
    unittest.main()
