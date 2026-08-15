import unittest
from types import SimpleNamespace
from xml.etree import ElementTree

from plogical.backupMetadataBuilder import (
    build_dns_records_xml,
    build_email_accounts_xml,
)


class OptionalBackupMetadataTests(unittest.TestCase):

    def test_missing_dns_and_email_features_produce_empty_sections(self):
        dns = build_dns_records_xml(None)
        emails = build_email_accounts_xml(None)

        self.assertEqual('<dnsrecords />', ElementTree.tostring(dns, encoding='unicode'))
        self.assertEqual('<emails />', ElementTree.tostring(emails, encoding='unicode'))

    def test_present_dns_and_email_records_are_preserved(self):
        dns = build_dns_records_xml([
            SimpleNamespace(type='A', name='example.com', content='192.0.2.1', prio=0),
        ])
        emails = build_email_accounts_xml([
            SimpleNamespace(email='hello@example.com', password='stored-hash'),
        ])

        self.assertEqual('A', dns.findtext('./dnsrecord/type'))
        self.assertEqual('192.0.2.1', dns.findtext('./dnsrecord/content'))
        self.assertEqual('hello@example.com', emails.findtext('./emailAccount/email'))
        self.assertEqual('stored-hash', emails.findtext('./emailAccount/password'))
