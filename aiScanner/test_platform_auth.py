"""Machine enrollment uses the current administrator's saved credentials."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from aiScanner.platform_auth import saved_scanner_auth_headers


class ScannerPlatformAuthTests(unittest.TestCase):
    def setUp(self):
        self.admin = object()
        self.scanner_model = Mock()
        self.mail_model = Mock()
        self.scanner_model.objects.filter.return_value.first.return_value = None
        self.mail_model.objects.filter.return_value.first.return_value = None
        self.modules = {
            'aiScanner.models': SimpleNamespace(AIScannerSettings=self.scanner_model),
            'emailDelivery.models': SimpleNamespace(CyberMailAccount=self.mail_model),
        }
        self.patcher = patch.dict(sys.modules, self.modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_existing_scanner_key_is_selected_only_for_current_admin(self):
        self.scanner_model.objects.filter.return_value.first.return_value = SimpleNamespace(api_key='cp_saved_fixture')
        self.assertEqual(saved_scanner_auth_headers(self.admin), {'X-API-Key': 'cp_saved_fixture'})
        self.scanner_model.objects.filter.assert_called_once_with(admin=self.admin)
        self.mail_model.objects.filter.assert_not_called()

    def test_connected_cybermail_key_can_bootstrap_same_owner_scanner(self):
        self.mail_model.objects.filter.return_value.first.return_value = SimpleNamespace(api_key='cpk_saved_fixture')
        self.assertEqual(saved_scanner_auth_headers(self.admin), {'X-CP-API-Key': 'cpk_saved_fixture'})
        self.mail_model.objects.filter.assert_called_once_with(admin=self.admin, is_connected=True)

    def test_unrelated_mail_key_is_not_treated_as_installation_auth(self):
        self.mail_model.objects.filter.return_value.first.return_value = SimpleNamespace(api_key='unrelated_fixture')
        self.assertEqual(saved_scanner_auth_headers(self.admin), {})

    def test_no_credentials_never_manufactures_auth_from_ip_or_email(self):
        self.assertEqual(saved_scanner_auth_headers(self.admin), {})

    def test_no_administrator_cannot_use_another_users_key(self):
        self.assertEqual(saved_scanner_auth_headers(None), {})
        self.scanner_model.objects.filter.assert_not_called()
        self.mail_model.objects.filter.assert_not_called()
