#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit checks for DNS / Cloudflare lifecycle helpers (no live Cloudflare API)."""
from __future__ import print_function

import os
import sys
import types
import unittest

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')


class FakeZones(object):
    def __init__(self, zone_map):
        # zone_map: exact name -> {id, name}
        self.zone_map = zone_map

    def get(self, params=None):
        name = (params or {}).get('name', '').rstrip('.').lower()
        z = self.zone_map.get(name)
        if not z:
            return []
        return [z]


class FakeCF(object):
    def __init__(self, zone_map):
        self.zones = FakeZones(zone_map)


class ResolveZoneTests(unittest.TestCase):
    def test_parent_walk_finds_apex(self):
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        cf = FakeCF({
            'example.com': {'id': 'zid1', 'name': 'example.com'},
        })
        zid, zname = CloudflareDnsSync.resolve_zone(cf, 'blog.example.com')
        self.assertEqual(zid, 'zid1')
        self.assertEqual(zname, 'example.com')

    def test_nested_parent_walk(self):
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        cf = FakeCF({
            'example.com': {'id': 'zid1', 'name': 'example.com'},
        })
        zid, zname = CloudflareDnsSync.resolve_zone(cf, 'a.b.example.com')
        self.assertEqual(zid, 'zid1')
        self.assertEqual(zname, 'example.com')

    def test_exact_zone_match(self):
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        cf = FakeCF({
            'example.com': {'id': 'zid1', 'name': 'example.com'},
        })
        zid, zname = CloudflareDnsSync.resolve_zone(cf, 'example.com')
        self.assertEqual(zid, 'zid1')
        self.assertEqual(zname, 'example.com')


class HostScopedDeleteSelectionTests(unittest.TestCase):
    def test_apex_and_child_use_same_filter(self):
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        zone_name = 'example.com'
        records = [
            {'id': '1', 'name': 'example.com', 'type': 'A'},
            {'id': '2', 'name': 'www.example.com', 'type': 'CNAME'},
            {'id': '3', 'name': 'blog.example.com', 'type': 'A'},
            {'id': '4', 'name': 'mail.blog.example.com', 'type': 'A'},
        ]

        def select(base_fqdn):
            out = []
            for record in records:
                fqdn = CloudflareDnsSync.record_to_fqdn(record.get('name'), zone_name)
                if fqdn == base_fqdn or fqdn.endswith('.' + base_fqdn):
                    out.append(record['id'])
            return out

        # Apex host-scoped: everything under example.com
        apex_ids = select('example.com')
        self.assertEqual(set(apex_ids), {'1', '2', '3', '4'})

        # Child host-scoped: blog + mail.blog
        child_ids = select('blog.example.com')
        self.assertEqual(set(child_ids), {'3', '4'})


class CfTemplateEnableGateTests(unittest.TestCase):
    def test_disable_returns_without_sync(self):
        from plogical.dnsUtilities import DNS

        dns = DNS()
        dns.admin = types.SimpleNamespace(userName='unit-test-cf-gate')
        dns.email = 'x@example.com'
        dns.key = 'token'
        dns.status = 'Disable'
        dns.loadCFKeys = lambda: 1

        ok, msg = dns.cfTemplate('example.com', dns.admin, enableCheck=True)
        self.assertEqual(ok, 0)
        self.assertIn('Sync not enabled', msg or '')


class BumpSoaNativeTests(unittest.TestCase):
    def test_bump_accepts_native_zone_object(self):
        """bumpSOASerial no longer rejects NATIVE zones at the type gate."""
        import inspect
        from plogical.dnsUtilities import DNS
        src = inspect.getsource(DNS.bumpSOASerial)
        self.assertNotIn("!= 'MASTER'", src)
        self.assertIn('if zone is None:', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
