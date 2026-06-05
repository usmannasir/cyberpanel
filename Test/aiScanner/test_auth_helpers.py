"""
Tests for AI Scanner authentication helpers.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, RequestFactory
from django.utils import timezone

from aiScanner.auth_helpers import (
    scan_allows_api_key_file_write,
    validate_scan_callback_credentials,
)


class ScanCallbackAuthTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_callback_rejects_missing_api_key(self):
        request = self.factory.post(
            '/aiscanner/callback/',
            data='{"scan_id":"test-scan"}',
            content_type='application/json',
        )
        _, _, error_response = validate_scan_callback_credentials(request, 'test-scan')
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 401)

    def test_callback_rejects_missing_scan_id(self):
        request = self.factory.post(
            '/aiscanner/callback/',
            data='{}',
            content_type='application/json',
            HTTP_X_API_KEY='cp_test_key',
        )
        _, _, error_response = validate_scan_callback_credentials(request, None)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)


class FileWriteGraceTests(SimpleTestCase):
    @patch('aiScanner.auth_helpers.FileAccessToken.objects.filter')
    def test_api_key_write_denied_without_token_or_recent_scan(self, mock_filter):
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_filter.return_value = mock_qs

        scan = MagicMock()
        scan.scan_id = 'old-scan'
        scan.started_at = timezone.now() - timedelta(hours=100)
        scan.status = 'completed'

        allowed, error = scan_allows_api_key_file_write(scan, 'api_key')
        self.assertFalse(allowed)
        self.assertIn('not authorized', error)

    def test_file_token_auth_always_allowed(self):
        scan = MagicMock()
        allowed, error = scan_allows_api_key_file_write(scan, 'file_token')
        self.assertTrue(allowed)
        self.assertIsNone(error)
