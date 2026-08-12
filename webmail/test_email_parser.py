import unittest

from webmail.services.email_parser import EmailParser
from webmail.services.imap_client import IMAPClient


class MimeDecodingTests(unittest.TestCase):

    def test_unknown_header_charset_uses_safe_fallback(self):
        value = '=?unknown-8bit?Q?Invoice_=E9?='

        self.assertEqual(EmailParser._decode_header_value(value), 'Invoice �')
        self.assertEqual(IMAPClient._decode_header_value(None, value), 'Invoice �')

    def test_unknown_body_charset_does_not_break_message_view(self):
        message = (
            b'Subject: =?unknown-8bit?Q?Invoice_=E9?=\r\n'
            b'Content-Type: text/plain; charset="unknown-8bit"\r\n'
            b'Content-Transfer-Encoding: 8bit\r\n'
            b'\r\n'
            b'Payment received: \xe9\r\n'
        )

        parsed = EmailParser.parse_message(message)

        self.assertEqual(parsed['subject'], 'Invoice �')
        self.assertEqual(parsed['body_text'], 'Payment received: �\r\n')

    def test_valid_declared_charset_remains_supported(self):
        message = (
            b'Content-Type: text/plain; charset="iso-8859-1"\r\n'
            b'Content-Transfer-Encoding: 8bit\r\n'
            b'\r\n'
            b'Payment received: \xe9\r\n'
        )

        self.assertEqual(
            EmailParser.parse_message(message)['body_text'],
            'Payment received: é\r\n',
        )
