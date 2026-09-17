"""Regression tests for message ordering and list flags."""
import unittest

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
    def test_sort_order_survives_fetch_and_answered_flag_is_exposed(self):
        client = object.__new__(IMAPClient)
        client.conn = ListingIMAP()

        result = client.list_messages()

        self.assertEqual(['20', '10'], [message['uid'] for message in result['messages']])
        self.assertTrue(result['messages'][0]['is_answered'])
        self.assertFalse(result['messages'][1]['is_answered'])


if __name__ == '__main__':
    unittest.main()
