import base64
import unittest

from webmail.services.imap_client import IMAPClient


def modified_utf7(text):
    encoded = base64.b64encode(text.encode('utf-16-be')).decode('ascii')
    return '&%s-' % encoded.rstrip('=').replace('/', ',')


class FolderDisplayNameTests(unittest.TestCase):
    def setUp(self):
        self.client = object.__new__(IMAPClient)

    def test_arabic_mailbox_name_is_decoded_for_display(self):
        self.assertEqual(
            'العربية',
            self.client._display_name('INBOX.' + modified_utf7('العربية')),
        )

    def test_ascii_and_literal_ampersand_are_preserved(self):
        self.assertEqual('Projects & Reports', self.client._display_name('INBOX.Projects &- Reports'))

    def test_malformed_sequence_remains_visible(self):
        self.assertEqual('Broken &***-', self.client._display_name('INBOX.Broken &***-'))



class RecordingConnection:
    """Records the mailbox arguments imaplib would put on the wire."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name,) + args)
            return 'OK', [b'']
        return call


class FolderQuotingTests(unittest.TestCase):
    def setUp(self):
        self.client = object.__new__(IMAPClient)
        self.client.conn = RecordingConnection()

    def test_every_folder_command_sends_a_quoted_name(self):
        name = 'INBOX.Say "hi" \\ there'
        wire = '"INBOX.Say \\"hi\\" \\\\ there"'
        self.client._select(name)
        self.client.create_folder(name)
        self.client.rename_folder(name, name)
        self.client.delete_folder(name)
        self.client.append_message(name, b'message')

        self.assertEqual([
            ('select', wire),
            ('create', wire),
            ('rename', wire, wire),
            ('delete', wire),
            ('append', wire, None, None, b'message'),
        ], self.client.conn.calls)

    def test_listed_names_are_read_back_exactly(self):
        lines = {
            b'(\\HasNoChildren) "." "INBOX.Say \\"hi\\" \\\\ there"': 'INBOX.Say "hi" \\ there',
            b'(\\HasNoChildren) "." "INBOX.QA Space"': 'INBOX.QA Space',
            b'(\\HasNoChildren) "." INBOX.Sent': 'INBOX.Sent',
            (b'(\\HasNoChildren) "." {14}', b'INBOX.Lit "x"'): 'INBOX.Lit "x"',
        }
        for line, name in lines.items():
            self.assertEqual(name, self.client._parse_folder_list(line)['name'], line)
            # What is listed is what the next command sends back.
            self.assertEqual(name, self.client._parse_folder_list(
                b'() "." ' + self.client._quote_mailbox(name).encode('utf-8'))['name'])
        self.assertIsNone(self.client._parse_folder_list(b')'))

    def test_line_breaks_in_folder_names_are_refused(self):
        for action in (lambda: self.client._select('INBOX\r\nA1 DELETE INBOX'),
                       lambda: self.client.create_folder('x\ny'),
                       lambda: self.client.append_message('Sent\r\n', b'm')):
            with self.assertRaises(ValueError):
                action()
        self.assertEqual([], self.client.conn.calls)

    def test_message_uids_must_be_numbers(self):
        for uids in (['1 +FLAGS (\\Deleted)'], ['1\r\nA1 EXPUNGE'], [True], ['0']):
            with self.assertRaises(ValueError):
                self.client.mark_read('INBOX', uids)
        with self.assertRaises(ValueError):
            self.client.get_message('INBOX', '1:*')
        self.assertEqual([], self.client.conn.calls)

    def test_search_text_cannot_hold_line_breaks(self):
        with self.assertRaises(ValueError):
            self.client.search_messages('INBOX', 'x\r\nA1 DELETE INBOX')


if __name__ == '__main__':
    unittest.main()
