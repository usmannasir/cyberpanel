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


if __name__ == '__main__':
    unittest.main()
