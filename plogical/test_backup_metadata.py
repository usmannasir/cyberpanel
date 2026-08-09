import unittest
from xml.etree import ElementTree

from plogical.backupMetadata import backup_includes_mail_domain


class BackupMetadataTests(unittest.TestCase):

    def test_detects_mail_child_domain(self):
        metadata = ElementTree.fromstring('''
            <metaFile>
              <ChildDomains>
                <domain><domain>mail.example.com</domain></domain>
              </ChildDomains>
            </metaFile>
        ''')
        self.assertTrue(backup_includes_mail_domain(metadata, 'example.com'))

    def test_does_not_invent_missing_mail_child_domain(self):
        metadata = ElementTree.fromstring('''
            <metaFile>
              <ChildDomains>
                <domain><domain>shop.example.com</domain></domain>
              </ChildDomains>
            </metaFile>
        ''')
        self.assertFalse(backup_includes_mail_domain(metadata, 'example.com'))

    def test_supports_backups_without_child_domain_metadata(self):
        metadata = ElementTree.fromstring('<metaFile />')
        self.assertFalse(backup_includes_mail_domain(metadata, 'example.com'))


if __name__ == '__main__':
    unittest.main()
