"""Regression tests for message ordering and list flags."""
import unittest
from email.header import Header

from webmail.services.imap_client import IMAPClient


class ListingIMAP:
    def select(self, folder):
        return 'OK', [b'2']

    def uid(self, command, *args):
        if command == 'sort':
            return 'OK', [b'20 10']
        if command == 'fetch':
            # Servers commonly return FETCH records in mailbox order, not in
            # the order of the requested UID set.
            return 'OK', [
                (b'1 (UID 10 FLAGS (\\Seen) RFC822.SIZE 10)',
                 b'From: old@example.com\r\nSubject: Old\r\nDate: Tue, 1 Sep 2026 10:00:00 +0000\r\n\r\n'),
                (b'2 (UID 20 FLAGS (\\Seen \\Answered) RFC822.SIZE 20)',
                 b'From: new@example.com\r\nSubject: New\r\nDate: Wed, 2 Sep 2026 10:00:00 +0000\r\n\r\n'),
            ]
        raise AssertionError(command)


class MessageListingTests(unittest.TestCase):
    def test_long_encoded_subject_keeps_headers_metadata_and_sort_order(self):
        subject = 'v308 owned mail punctuation & اردو العربية ' * 3
        encoded_subject = Header(subject, 'utf-8').encode(linesep='\r\n').encode('ascii')
        self.assertIn(b'\r\n ', encoded_subject)
        headers = (b'From: Sender <new@example.com>\r\n'
                   b'To: Recipient <recipient@example.com>\r\nSubject: ' + encoded_subject +
                   b'\r\nDate: Sun, 18 Oct 2026 12:49:10 +0000\r\n\r\n')

        class LiteralIMAP(ListingIMAP):
            def uid(self, command, *args):
                if command != 'fetch':
                    return super().uid(command, *args)
                self.fetch_attributes = args[1]
                records = [super().uid(command, *args)[1][0]]
                metadata = b'2 (UID 20 FLAGS (\\Seen \\Flagged \\Answered) RFC822.SIZE 2140 '
                if 'ENVELOPE' in self.fetch_attributes:
                    # imaplib returns one tuple per literal. Dovecot may encode
                    # the envelope subject as a literal before the header body;
                    # only that first tuple contains the UID/FLAGS/size prefix.
                    records.extend([
                        (metadata + b'ENVELOPE ("date" {' + str(len(encoded_subject)).encode() + b'}',
                         encoded_subject),
                        (b' NIL NIL NIL NIL NIL NIL NIL NIL) BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)] {' +
                         str(len(headers)).encode() + b'}', headers),
                    ])
                else:
                    records.append((metadata + b'BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)] {' +
                                    str(len(headers)).encode() + b'}', headers))
                return 'OK', records + [b')']

        client = object.__new__(IMAPClient)
        client.conn = LiteralIMAP()
        result = client.list_messages()

        self.assertEqual(['20', '10'], [message['uid'] for message in result['messages']])
        message = result['messages'][0]
        self.assertEqual(subject, message['subject'])
        self.assertEqual('Sender <new@example.com>', message['from'])
        self.assertEqual('Recipient <recipient@example.com>', message['to'])
        self.assertEqual('Sun, 18 Oct 2026 12:49:10 +0000', message['date'])
        self.assertEqual(2140, message['size'])
        self.assertTrue(message['is_read'])
        self.assertTrue(message['is_flagged'])
        self.assertTrue(message['is_answered'])
        self.assertEqual((2, 1, 1), (result['total'], result['page'], result['pages']))
        # Listing must continue to use PEEK rather than mark the mail as read.
        self.assertIn('BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)]', client.conn.fetch_attributes)

    def test_sort_order_survives_fetch_and_answered_flag_is_exposed(self):
        client = object.__new__(IMAPClient)
        client.conn = ListingIMAP()

        result = client.list_messages()

        self.assertEqual(['20', '10'], [message['uid'] for message in result['messages']])
        self.assertTrue(result['messages'][0]['is_answered'])
        self.assertFalse(result['messages'][1]['is_answered'])


if __name__ == '__main__':
    unittest.main()
