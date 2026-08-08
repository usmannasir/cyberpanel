# -*- coding: utf-8 -*-


from django.test import SimpleTestCase
from unittest.mock import Mock, patch

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
