# -*- coding: utf-8 -*-


import json

from django.test import SimpleTestCase
from unittest.mock import Mock, patch

from plogical.dnsUtilities import DNS
from plogical.acl import ACLManager
from dns.dnsManager import DNSManager


class SOASerialTests(SimpleTestCase):
    @patch('plogical.dnsUtilities.Records.objects.filter')
    def test_primary_zone_serial_is_incremented(self, records_filter):
        soa = Mock(content='ns1.example.com hostmaster.example.com 2026080801 10800 3600 604800 3600')
        records_filter.return_value = [soa]
        zone = Mock(type='MASTER', name='example.com')

        self.assertTrue(DNS.incrementSOASerial(zone))
        self.assertEqual(
            soa.content,
            'ns1.example.com hostmaster.example.com 2026080802 10800 3600 604800 3600'
        )
        soa.save.assert_called_once_with(update_fields=['content'])

    @patch('plogical.dnsUtilities.Records.objects.filter')
    def test_non_primary_zone_is_unchanged(self, records_filter):
        zone = Mock(type='NATIVE', name='example.com')

        self.assertFalse(DNS.incrementSOASerial(zone))
        records_filter.assert_not_called()


class DeleteNullOwnerRecordTests(SimpleTestCase):
    """Records created outside the panel (acme.sh, pdnsutil) have a NULL
    domainOwner. Deleting them must resolve the zone through the native
    PowerDNS domain_id instead of crashing on domainOwner.name."""

    @patch('dns.dnsManager.DNS.incrementSOASerial')
    @patch('dns.dnsManager.Records.objects.get')
    @patch('dns.dnsManager.Domains.objects.get')
    @patch('dns.dnsManager.ACLManager')
    @patch('dns.dnsManager.Administrator.objects.get')
    def test_delete_resolves_null_owner_zone_from_domain_id(
            self, admin_get, acl, domains_get, records_get, increment_soa):
        zone = Mock()
        zone.name = 'example.com'
        domains_get.return_value = zone

        record = Mock(domainOwner=None, domain_id=7, type='A')
        records_get.return_value = record

        acl.loadedACL.return_value = {}
        acl.currentContextPermission.return_value = 1
        acl.checkOwnershipZone.return_value = 1

        response = DNSManager().deleteDNSRecord(userID=1, data={'id': 11})
        result = json.loads(response.content)

        self.assertEqual(result['status'], 1)
        self.assertEqual(result['delete_status'], 1)
        record.delete.assert_called_once()
        domains_get.assert_called_once_with(id=7)
        acl.checkOwnershipZone.assert_called_once_with('example.com', admin_get.return_value, {})
        increment_soa.assert_called_once_with(zone)

    @patch('dns.dnsManager.DNS.incrementSOASerial')
    @patch('dns.dnsManager.Records.objects.get')
    @patch('dns.dnsManager.Domains.objects.get')
    @patch('dns.dnsManager.ACLManager')
    @patch('dns.dnsManager.Administrator.objects.get')
    def test_delete_uses_domainowner_when_present(
            self, admin_get, acl, domains_get, records_get, increment_soa):
        zone = Mock()
        zone.name = 'example.com'

        record = Mock(domain_id=7, type='A')
        record.domainOwner = zone
        records_get.return_value = record

        acl.loadedACL.return_value = {}
        acl.currentContextPermission.return_value = 1
        acl.checkOwnershipZone.return_value = 1

        response = DNSManager().deleteDNSRecord(userID=1, data={'id': 11})
        result = json.loads(response.content)

        self.assertEqual(result['status'], 1)
        record.delete.assert_called_once()
        domains_get.assert_not_called()
        acl.checkOwnershipZone.assert_called_once_with('example.com', admin_get.return_value, {})


class VerifyRecordOwnerTests(SimpleTestCase):
    @patch('dns.models.Domains.objects.get')
    def test_null_owner_record_matches_zone_via_domain_id(self, domains_get):
        zone = Mock()
        zone.name = 'example.com'
        domains_get.return_value = zone
        record = Mock(domainOwner=None, domain_id=7)

        self.assertEqual(ACLManager.VerifyRecordOwner({'admin': 0}, record, 'example.com'), 1)
        domains_get.assert_called_once_with(id=7)

    @patch('dns.models.Domains.objects.get')
    def test_null_owner_record_rejects_other_zone(self, domains_get):
        zone = Mock()
        zone.name = 'other.com'
        domains_get.return_value = zone
        record = Mock(domainOwner=None, domain_id=7)

        self.assertEqual(ACLManager.VerifyRecordOwner({'admin': 0}, record, 'example.com'), 0)

    def test_owned_record_still_matches_by_domain_owner(self):
        zone = Mock()
        zone.name = 'example.com'
        record = Mock(domain_id=7)
        record.domainOwner = zone

        self.assertEqual(ACLManager.VerifyRecordOwner({'admin': 0}, record, 'example.com'), 1)
        self.assertEqual(ACLManager.VerifyRecordOwner({'admin': 0}, record, 'other.com'), 0)
