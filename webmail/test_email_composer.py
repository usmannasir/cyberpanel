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


class FakeSMTP:
    """Records what smtplib's send_message() would hand to the server."""

    def __init__(self):
        self.sent = None

    def send(self, message):
        import smtplib

        class Recorder(smtplib.SMTP):
            def __init__(inner):
                inner.does_esmtp = False
                inner.esmtp_features = {}
                inner.helo_resp = b'ok'
                inner.ehlo_resp = None

            def sendmail(inner, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
                self.sent = (from_addr, list(to_addrs), msg)
                return {}

        Recorder().send_message(message)
        return self.sent


class RecipientTests(unittest.TestCase):
    def test_bcc_recipients_are_on_the_envelope_but_not_in_the_sent_copy(self):
        message = EmailComposer.compose(
            'user@example.com', 'to@example.net', 'Test', body_html='<p>x</p>',
            cc_addrs='cc@example.net', bcc_addrs='hidden@example.org, Dee <dee@example.org>')

        from_addr, envelope, wire = FakeSMTP().send(message)

        self.assertEqual('user@example.com', from_addr)
        self.assertEqual(sorted(['to@example.net', 'cc@example.net', 'hidden@example.org', 'dee@example.org']),
                         sorted(envelope))
        delivered = email.message_from_bytes(wire if isinstance(wire, bytes) else wire.encode('utf-8'))
        self.assertIsNone(delivered['Bcc'])
        self.assertNotIn(b'hidden@example.org', wire if isinstance(wire, bytes) else wire.encode('utf-8'))
        # The sender's own copy (saved to Sent) still shows who was copied.
        self.assertEqual('hidden@example.org, Dee <dee@example.org>', message['Bcc'])

    def test_bcc_with_attachments_is_delivered_the_same_way(self):
        message = EmailComposer.compose(
            'user@example.com', 'to@example.net', 'Test', bcc_addrs='hidden@example.org',
            attachments=[('a.txt', 'text/plain', b'attachment')])

        unused, envelope, wire = FakeSMTP().send(message)

        self.assertEqual(sorted(['to@example.net', 'hidden@example.org']), sorted(envelope))
        self.assertNotIn(b'hidden@example.org', wire if isinstance(wire, bytes) else wire.encode('utf-8'))

    def test_no_bcc_header_without_bcc_recipients(self):
        self.assertIsNone(EmailComposer.compose('user@example.com', 'to@example.net', 'Test')['Bcc'])

    def test_recipient_lists_cannot_inject_headers(self):
        for field in ('to_addrs', 'cc_addrs', 'bcc_addrs'):
            for value in ('a@example.net\r\nX-Injected: 1', 'a@example.net\nX: 1', 'a@example.net\rX: 1'):
                values = {'to_addrs': 'to@example.net'}
                values[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    EmailComposer.compose('user@example.com', subject='Test', **values)
