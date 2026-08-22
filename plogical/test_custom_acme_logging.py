import unittest
from unittest.mock import MagicMock, patch

from plogical.customACME import CustomACME


class CustomACMELoggingTests(unittest.TestCase):

    @patch('plogical.customACME.os.makedirs')
    @patch('plogical.customACME.logging.CyberCPLogFileWriter.writeToFile')
    @patch('plogical.customACME.requests.post')
    def test_download_does_not_log_response_headers_or_url(
            self, post, write_log, make_dirs):
        response = MagicMock(
            status_code=200,
            content=b'-----BEGIN CERTIFICATE-----\ndata\n-----END CERTIFICATE-----\n',
        )
        response.headers = {'Replay-Nonce': 'private-nonce-value'}
        post.return_value = response
        acme = CustomACME('example.com', 'admin@example.com')
        acme.certificate_url = 'https://acme.invalid/private-certificate-url'

        with patch.object(acme, '_get_nonce', return_value=True), \
                patch.object(acme, '_create_jws', return_value='{}'):
            self.assertEqual(response.content, acme._download_certificate())

        log_output = '\n'.join(call.args[0] for call in write_log.call_args_list)
        self.assertNotIn('private-nonce-value', log_output)
        self.assertNotIn('private-certificate-url', log_output)
        self.assertIn('Certificate download response status: 200', log_output)

    @patch('plogical.customACME.os.makedirs')
    @patch('plogical.customACME.logging.CyberCPLogFileWriter.writeToFile')
    @patch('plogical.customACME.requests.post')
    def test_existing_acme_account_response_is_accepted(
            self, post, write_log, make_dirs):
        response = MagicMock(status_code=200)
        response.headers = {'Location': 'https://acme.invalid/existing-account'}
        post.return_value = response
        acme = CustomACME('example.com', 'admin@example.com')
        acme.directory = {'newAccount': 'https://acme.invalid/new-account'}

        with patch.object(acme, '_create_jws', return_value='{}'), \
                patch.object(acme, '_save_account_key', return_value=True):
            self.assertTrue(acme._create_account())

        self.assertEqual(
            'https://acme.invalid/existing-account', acme.account_url)

    @patch('plogical.customACME.os.makedirs')
    @patch('plogical.customACME.logging.CyberCPLogFileWriter.writeToFile')
    def test_loaded_account_key_is_not_replaced(self, write_log, make_dirs):
        acme = CustomACME('example.com', 'admin@example.com')

        with patch.object(acme, '_load_account_key', return_value=True), \
                patch.object(acme, '_check_dns_record', return_value=True), \
                patch.object(acme, '_generate_account_key') as generate_key, \
                patch.object(acme, '_get_directory', return_value=False):
            self.assertFalse(acme.issue_certificate(['example.com']))

        generate_key.assert_not_called()

    @patch('plogical.customACME.os.makedirs')
    @patch('plogical.customACME.logging.CyberCPLogFileWriter.writeToFile')
    @patch('plogical.customACME.requests.post')
    def test_zerossl_eab_secret_is_not_logged(self, post, write_log, make_dirs):
        secret = 'eab-secret-value'
        response = MagicMock(status_code=200, text='{"eab_hmac_key": "%s"}' % secret)
        response.json.return_value = {
            'eab_kid': 'account-id',
            'eab_hmac_key': secret,
        }
        post.return_value = response
        acme = CustomACME('example.com', 'admin@example.com', provider='zerossl')

        self.assertEqual(('account-id', secret), acme._get_zerossl_eab_credentials())

        log_output = '\n'.join(call.args[0] for call in write_log.call_args_list)
        self.assertNotIn(secret, log_output)
        self.assertIn('ZeroSSL EAB credentials response received', log_output)

    @patch('plogical.customACME.os.makedirs')
    @patch('plogical.customACME.logging.CyberCPLogFileWriter.writeToFile')
    def test_acme_request_contents_are_not_logged(self, write_log, make_dirs):
        secret = 'request-secret-value'
        acme = CustomACME('example.com', 'admin@example.com')
        acme.directory = {'newAccount': 'https://acme.invalid/new-account'}
        acme._generate_account_key()

        with patch.object(acme, '_get_nonce', return_value=True):
            acme.nonce = 'nonce-value'
            self.assertIsNotNone(
                acme._create_jws({'secret': secret}, 'https://acme.invalid/order')
            )

        log_output = '\n'.join(call.args[0] for call in write_log.call_args_list)
        self.assertNotIn(secret, log_output)
        self.assertNotIn('nonce-value', log_output)
        self.assertIn('ACME JWS request created', log_output)


if __name__ == '__main__':
    unittest.main()
