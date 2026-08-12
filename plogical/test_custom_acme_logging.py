import unittest
from unittest.mock import MagicMock, patch

from plogical.customACME import CustomACME


class CustomACMELoggingTests(unittest.TestCase):

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
