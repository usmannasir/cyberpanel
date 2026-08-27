import pathlib
import unittest
from unittest.mock import patch

from plogical.virtualHostUtilities import virtualHostUtilities


class DovecotSNIConfigurationTests(unittest.TestCase):

    def test_email_services_require_postfix_configuration(self):
        with patch('plogical.virtualHostUtilities.os.path.exists', return_value=True), \
                patch('plogical.virtualHostUtilities.os.path.isfile', return_value=False):
            self.assertFalse(virtualHostUtilities.emailServicesInstalled())

    def test_email_services_are_available_with_marker_and_configuration(self):
        with patch('plogical.virtualHostUtilities.os.path.exists', return_value=True), \
                patch('plogical.virtualHostUtilities.os.path.isfile', return_value=True):
            self.assertTrue(virtualHostUtilities.emailServicesInstalled())

    def test_dovecot_24_sni_uses_plain_file_paths(self):
        block = virtualHostUtilities.getDovecotSNIBlock(
            ['mail.example.com'],
            'dovecot_config_version = 2.4.0\n',
        )

        self.assertIn(
            'ssl_server_cert_file = '
            '/etc/letsencrypt/live/mail.example.com/fullchain.pem',
            block,
        )
        self.assertIn(
            'ssl_server_key_file = '
            '/etc/letsencrypt/live/mail.example.com/privkey.pem',
            block,
        )
        self.assertNotIn('ssl_server_cert_file = <', block)
        self.assertNotIn('ssl_server_key_file = <', block)

    def test_dovecot_24_existing_sni_paths_are_normalized(self):
        content = """dovecot_config_version = 2.4.0
local_name mail.example.com {
    ssl_server_cert_file = </etc/letsencrypt/live/mail.example.com/fullchain.pem
    ssl_server_key_file = </etc/letsencrypt/live/mail.example.com/privkey.pem
}
"""

        normalized = virtualHostUtilities.normalizeDovecotSNIPaths(content)

        self.assertNotIn(' = <', normalized)
        self.assertIn(
            'ssl_server_cert_file = '
            '/etc/letsencrypt/live/mail.example.com/fullchain.pem',
            normalized,
        )

    def test_legacy_dovecot_keeps_inline_file_marker(self):
        content = """ssl = required
local_name mail.example.com {
    ssl_cert = </etc/letsencrypt/live/mail.example.com/fullchain.pem
    ssl_key = </etc/letsencrypt/live/mail.example.com/privkey.pem
}
"""
        block = virtualHostUtilities.getDovecotSNIBlock(
            ['mail.example.com'],
            content,
        )

        self.assertIn('ssl_cert = </etc/letsencrypt/', block)
        self.assertIn('ssl_key = </etc/letsencrypt/', block)
        self.assertEqual(
            content,
            virtualHostUtilities.normalizeDovecotSNIPaths(content),
        )

    def test_upgrade_repairs_dovecot_24_sni_before_mail_restarts(self):
        upgrade_source = (
            pathlib.Path(__file__).with_name('upgrade.py')
        ).read_text(encoding='utf-8')

        repair_call = upgrade_source.index(
            'Upgrade.repairDovecot24SNIPaths()'
        )
        webmail_call = upgrade_source.index('Upgrade.setupWebmail()', repair_call)
        sieve_call = upgrade_source.index('Upgrade.setupSieve()', repair_call)

        self.assertLess(repair_call, webmail_call)
        self.assertLess(repair_call, sieve_call)


if __name__ == '__main__':
    unittest.main()
