# -*- coding: utf-8 -*-


import json

from django.test import SimpleTestCase
from unittest.mock import Mock, patch

from dns.dnsManager import DNSManager
from plogical.dnsUtilities import DNS


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


@patch('dns.dnsManager.DNS.incrementSOASerial')
@patch('dns.dnsManager.Domains.objects.get')
@patch('dns.dnsManager.Records.objects.get')
@patch('dns.dnsManager.Administrator.objects.get')
@patch('dns.dnsManager.ACLManager')
class ExternalRecordTests(SimpleTestCase):
    def setUp(self):
        self.zone = Mock()
        self.zone.name = 'example.com'
        self.record = Mock(domainOwner=None, domain_id=7, type='A')
        self.update_data = {
            'id': 11, 'selectedZone': self.zone.name, 'nameNow': None,
            'ttlNow': 300, 'priorityNow': None, 'contentNow': '192.0.2.42',
        }

    def test_delete_checks_resolved_zone_and_updates_serial(self, acl, admin, records, domains, serial):
        records.return_value = self.record
        domains.return_value = self.zone
        acl.checkOwnershipZone.return_value = 1

        response = DNSManager().deleteDNSRecord(userID=1, data={'id': 11})

        self.assertEqual(json.loads(response.content)['delete_status'], 1)
        domains.assert_called_once_with(pk=7)
        acl.checkOwnershipZone.assert_called_once_with(
            self.zone.name, admin.return_value, acl.loadedACL.return_value
        )
        self.record.delete.assert_called_once_with()
        serial.assert_called_once_with(self.zone)

    def test_update_checks_resolved_zone_and_updates_serial(self, acl, admin, records, domains, serial):
        records.return_value = self.record
        domains.return_value = self.zone
        acl.loadedACL.return_value = {'admin': 0}
        acl.checkOwnershipZone.return_value = 1

        response = DNSManager().updateRecord(userID=1, data=self.update_data)

        self.assertEqual(json.loads(response.content)['status'], 1)
        domains.assert_called_once_with(pk=7)
        self.assertEqual(self.record.content, '192.0.2.42')
        self.record.save.assert_called_once_with()
        serial.assert_called_once_with(self.zone)

    def test_update_rejects_record_in_another_zone(self, acl, admin, records, domains, serial):
        records.return_value = self.record
        domains.return_value = self.zone
        acl.loadedACL.return_value = {'admin': 0}
        acl.checkOwnershipZone.return_value = 1
        self.update_data['selectedZone'] = 'other.example.com'

        self.assertIs(DNSManager().updateRecord(userID=1, data=self.update_data),
                      acl.loadErrorJson.return_value)
        self.record.save.assert_not_called()
        serial.assert_not_called()

    def test_delete_denies_unowned_zone(self, acl, admin, records, domains, serial):
        records.return_value = self.record
        domains.return_value = self.zone
        acl.checkOwnershipZone.return_value = 0

        self.assertIs(DNSManager().deleteDNSRecord(userID=1, data={'id': 11}),
                      acl.loadError.return_value)
        self.record.delete.assert_not_called()
        serial.assert_not_called()
