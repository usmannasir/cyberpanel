"""Failed issuance preserves existing certificate and key material."""
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from plogical import sslUtilities as module
from plogical.sslUtilities import sslUtilities, issueSSLForDomain


class FallbackTests(unittest.TestCase):
    def run_case(self, days=3, parsed=True, install=1, present=('fullchain.pem', 'privkey.pem'), openssl=0):
        cert = mock.Mock()
        cert.get_notAfter.return_value = (datetime.now(timezone.utc) + timedelta(days=days)).strftime('%Y%m%d%H%M%SZ').encode()
        cert.get_notBefore.return_value = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y%m%d%H%M%SZ').encode()
        cert.get_issuer.return_value.get_components.return_value = [(b'C', b'US'), (b'O', b'Issuer')]
        cert.get_subject.return_value.get_components.return_value = [(b'CN', b'example.com')]
        with mock.patch.object(module.os.path, 'exists', side_effect=lambda path: any(path.endswith(name) for name in present)), \
                mock.patch.object(module.os.path, 'lexists', return_value=False), \
                mock.patch('builtins.open', mock.mock_open(read_data=b'certificate')), \
                mock.patch('OpenSSL.crypto.load_certificate', side_effect=None if parsed else ValueError('bad certificate'), return_value=cert), \
                mock.patch.object(sslUtilities, 'obtainSSLForADomain', return_value=0), \
                mock.patch.object(sslUtilities, 'installSSLForDomain', return_value=install) as deployment, \
                mock.patch.object(module.subprocess, 'call', return_value=openssl) as process, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            result = issueSSLForDomain('example.com', 'admin@example.com', '/home/example.com/public_html')
        return result, deployment, process

    def test_valid_existing_is_not_fresh_success(self):
        result, _, _ = self.run_case()
        self.assertEqual(2, result[0])
        self.assertEqual('valid', result[2]['certificate_validity'])

    def test_expired_existing_is_not_success(self):
        result, deploy, process = self.run_case(-2)
        self.assertEqual(0, result[0])
        deploy.assert_not_called()
        process.assert_not_called()

    def test_unreadable_existing_is_preserved(self):
        result, deploy, process = self.run_case(parsed=False)
        self.assertEqual(0, result[0])
        deploy.assert_not_called()
        process.assert_not_called()

    def test_existing_install_failure_is_not_overwritten(self):
        result, _, process = self.run_case(install=0)
        self.assertEqual(0, result[0])
        process.assert_not_called()

    def test_lone_key_or_certificate_is_not_overwritten(self):
        for present in (('privkey.pem',), ('fullchain.pem',)):
            result, deploy, process = self.run_case(present=present)
            self.assertEqual(0, result[0])
            self.assertIn('incomplete', result[1])
            deploy.assert_not_called()
            process.assert_not_called()

    def test_failed_self_signed_command_does_not_install_or_claim_success(self):
        result, deploy, process = self.run_case(present=(), openssl=1)
        self.assertEqual(0, result[0])
        process.assert_called_once()
        deploy.assert_not_called()

    def test_successful_self_signed_fallback_is_still_not_public_issuance(self):
        result, deploy, process = self.run_case(present=())
        self.assertEqual(2, result[0])
        self.assertEqual('self_signed', result[2]['outcome'])
        deploy.assert_called_once()
