#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit checks for DNS.UpsertSpfForName / RecreateDNSForDomain helpers."""
from __future__ import print_function

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')


class UpsertSpfForNameTests(unittest.TestCase):
    def setUp(self):
        from plogical.dnsUtilities import DNS
        self.DNS = DNS

    def test_empty_hostname(self):
        changed, err = self.DNS.UpsertSpfForName('')
        self.assertEqual(changed, 0)
        self.assertEqual(err, 'Empty hostname')

    def test_recreate_missing_domain(self):
        admin = mock.Mock()
        status, message = self.DNS.RecreateDNSForDomain('', admin)
        self.assertEqual(status, 0)
        self.assertIn('Missing', message)

    def test_upsert_updates_wrong_spf(self):
        Domains = mock.Mock()
        Records = mock.Mock()
        zone = mock.Mock()
        Domains.objects.filter.return_value.first.return_value = zone

        wrong = mock.Mock()
        wrong.content = 'v=spf1 include:spf.cyberpersons.com ~all'
        Records.objects.filter.return_value = [wrong]

        with mock.patch.object(self.DNS, '_powerdns_models', return_value=(Domains, Records)):
            with mock.patch.object(self.DNS, 'buildSpfRecord', return_value='v=spf1 a mx ip4:203.0.113.10 ~all'):
                with mock.patch.object(self.DNS, 'bumpSOASerial'):
                    changed, err = self.DNS.UpsertSpfForName('example.com')

        self.assertIsNone(err)
        self.assertGreaterEqual(changed, 1)
        self.assertEqual(wrong.content, 'v=spf1 a mx ip4:203.0.113.10 ~all')
        wrong.save.assert_called()


if __name__ == '__main__':
    unittest.main()
