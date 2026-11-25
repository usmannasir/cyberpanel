"""The mail SSL checks believe only OpenSSL's own "certificate trusted" result."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'plogical' / 'mailUtilities.py'


def mail_ssl_verified():
    tree = ast.parse(SOURCE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'mailUtilities')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'mailSSLVerified')
    method.decorator_list = []
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['mailSSLVerified']


class MailSSLVerifiedTests(unittest.TestCase):

    def setUp(self):
        self.verified = mail_ssl_verified()

    def test_self_signed_in_openssl_3_and_1_1_wording(self):
        # OpenSSL 3.5 on Ubuntu 26.04 and AlmaLinux 10, then OpenSSL 1.1.
        self.assertFalse(self.verified('verify error:num=18:self-signed certificate\n'
                                       '    Verify return code: 18 (self-signed certificate)\n'))
        self.assertFalse(self.verified('    Verify return code: 18 (self signed certificate)\n'))
        self.assertFalse(self.verified('    Verify return code: 19 (self-signed certificate in certificate chain)\n'))

    def test_expired_untrusted_or_no_connection_are_not_valid(self):
        self.assertFalse(self.verified('    Verify return code: 10 (certificate has expired)\n'))
        self.assertFalse(self.verified('    Verify return code: 20 (unable to get local issuer certificate)\n'))
        self.assertFalse(self.verified('connect:errno=111\n'))
        self.assertFalse(self.verified(''))
        self.assertFalse(self.verified(None))

    def test_a_trusted_certificate(self):
        self.assertTrue(self.verified('SSL handshake has read 4567 bytes\n    Verify return code: 0 (ok)\n'))

    def test_every_check_uses_it(self):
        root = SOURCE.parents[1]
        for path in ('plogical/mailUtilities.py', 'mailServer/mailserverManager.py'):
            text = (root / path).read_text()
            self.assertNotIn('self signed certificate)', text, path)
            self.assertEqual(2, text.count('mailUtilities.mailSSLVerified(result)'), path)
            self.assertEqual(2, text.count('</dev/null'), path)


if __name__ == '__main__':
    unittest.main()
