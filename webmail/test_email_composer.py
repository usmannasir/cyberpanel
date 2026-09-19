"""Sender header serialization without SMTP connections."""
import email
from email import policy
from email.utils import parseaddr
import unittest

from webmail.services.email_composer import EmailComposer


class SenderHeaderTests(unittest.TestCase):
    def test_display_names_round_trip_without_changing_mailbox_or_message_id_domain(self):
        for name in ('', 'Hasan Khan', 'Doe, Jane', 'Hasan "Support"', 'حسن خان', 'Name <other@example.net>'):
            with self.subTest(name=name):
                message = EmailComposer.compose('user@example.com', 'to@example.net', 'Test', display_name=name)
                parsed = email.message_from_bytes(message.as_bytes(), policy=policy.default)
                self.assertEqual((name, 'user@example.com'), parseaddr(str(parsed['From'])))
                self.assertTrue(parsed['Message-ID'].endswith('@example.com>'))
                self.assertEqual(1, len(parsed['From'].addresses))

    def test_display_name_cannot_inject_headers(self):
        for name in ('Hasan\r\nBcc: attacker@example.net', 'Hasan\nInjected', 'Hasan\rInjected'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                EmailComposer.compose('user@example.com', 'to@example.net', 'Test', display_name=name)
