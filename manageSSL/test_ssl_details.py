"""Certificate lifetime regressions for the authenticated SSL details endpoint."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory
from OpenSSL import crypto

from manageSSL import views


NOW = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class SSLDetailsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = crypto.PKey()
        cls.key.generate_key(crypto.TYPE_RSA, 2048)

    def certificate(self, starts, expires, minimal_issuer=False):
        certificate = crypto.X509()
        certificate.set_serial_number(1)
        subject = certificate.get_subject()
        if not minimal_issuer:
            subject.C = 'US'
            subject.O = 'SSL Metadata Test'
        subject.CN = 'ssl-status.example'
        certificate.set_issuer(subject)
        certificate.set_pubkey(self.key)
        certificate.set_notBefore(starts.strftime('%Y%m%d%H%M%SZ').encode('ascii'))
        certificate.set_notAfter(expires.strftime('%Y%m%d%H%M%SZ').encode('ascii'))
        certificate.sign(self.key, 'sha256')
        return crypto.dump_certificate(crypto.FILETYPE_PEM, certificate)

    def details(self, certificate=None, read_error=None):
        request = RequestFactory().post(
            '/manageSSL/getSSLDetails',
            json.dumps({'virtualHost': 'ssl-status.example'}),
            content_type='application/json',
        )
        request.session = {'userID': 7}
        opened = mock.mock_open(read_data=certificate or b'')
        if read_error:
            opened.side_effect = read_error
        with mock.patch.object(views.Administrator.objects, 'get',
                               return_value=SimpleNamespace(pk=7)), \
                mock.patch.object(views.ACLManager, 'loadedACL',
                                  return_value={'admin': 1}), \
                mock.patch.object(views.ACLManager, 'checkOwnership', return_value=1), \
                mock.patch.object(views.ChildDomains.objects, 'get',
                                  side_effect=views.ChildDomains.DoesNotExist), \
                mock.patch.object(views.Websites.objects, 'get',
                                  return_value=SimpleNamespace(domain='ssl-status.example')), \
                mock.patch.object(views, 'datetime', FixedDateTime, create=True), \
                mock.patch.object(views, 'open', opened, create=True):
            response = views.getSSLDetails(request)
        opened.assert_called_once_with(
            '/etc/letsencrypt/live/ssl-status.example/fullchain.pem', 'rb')
        return json.loads(response.content)

    def assert_validity(self, starts, expires, expected, days):
        details = self.details(self.certificate(starts, expires))
        self.assertEqual(details['status'], 1)
        self.assertTrue(details['hasSSL'], 'Parsed certificates must retain certificate presence')
        self.assertEqual(details.get('validityStatus'), expected)
        self.assertEqual(details['days'], str(days))
        self.assertEqual(details['expiryDate'], expires.strftime('%Y-%m-%d %H:%M:%S'))
        return details

    def test_valid_certificate_is_active(self):
        self.assert_validity(NOW - timedelta(days=1), NOW + timedelta(days=60), 'valid', 60)

    def test_expired_certificate_remains_present_but_is_not_active(self):
        self.assert_validity(NOW - timedelta(days=60), NOW - timedelta(days=31), 'expired', -31)

    def test_exact_expiry_is_expired_even_when_days_is_zero(self):
        self.assert_validity(NOW - timedelta(days=1), NOW, 'expired', 0)

    def test_one_second_after_expiry_is_expired(self):
        self.assert_validity(NOW - timedelta(days=1), NOW - timedelta(seconds=1), 'expired', -1)

    def test_less_than_one_day_remaining_is_still_valid(self):
        self.assert_validity(NOW - timedelta(days=1), NOW + timedelta(hours=12), 'valid', 0)

    def test_one_second_before_expiry_is_still_valid(self):
        self.assert_validity(NOW - timedelta(days=1), NOW + timedelta(seconds=1), 'valid', 0)

    def test_future_certificate_is_not_yet_valid(self):
        self.assert_validity(NOW + timedelta(seconds=1), NOW + timedelta(days=30), 'not_yet_valid', 30)

    def test_exact_start_of_validity_is_valid(self):
        self.assert_validity(NOW, NOW + timedelta(days=30), 'valid', 30)

    def test_short_issuer_does_not_hide_an_expired_certificate(self):
        details = self.details(self.certificate(
            NOW - timedelta(days=60), NOW - timedelta(days=31), minimal_issuer=True))
        self.assertTrue(details['hasSSL'])
        self.assertEqual(details['validityStatus'], 'expired')
        self.assertEqual(details['authority'], 'ssl-status.example')

    def test_self_signed_certificate_validity_does_not_claim_trust(self):
        details = self.assert_validity(
            NOW - timedelta(days=1), NOW + timedelta(days=30), 'valid', 30)
        self.assertEqual(details['authority'], 'SSL Metadata Test')
        self.assertNotIn('trusted', details)

    def test_missing_certificate_does_not_claim_presence(self):
        details = self.details(read_error=FileNotFoundError('fixture certificate missing'))
        self.assertEqual(details['status'], 1)
        self.assertFalse(details['hasSSL'])
        self.assertNotEqual(details.get('validityStatus'), 'valid')

    def test_malformed_certificate_does_not_claim_presence(self):
        details = self.details(b'not a PEM certificate')
        self.assertEqual(details['status'], 1)
        self.assertFalse(details['hasSSL'])
        self.assertNotEqual(details.get('validityStatus'), 'valid')


if __name__ == '__main__':
    unittest.main()
