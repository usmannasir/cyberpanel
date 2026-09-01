#!/usr/bin/env python
import os, sys, unittest
sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
import django
django.setup()

class BannedIPsTests(unittest.TestCase):
    def test_rule_order_module(self):
        from firewall import ruleOrder
        self.assertTrue(callable(ruleOrder.next_sort_order))

    def test_bannedip_model(self):
        from firewall.models import BannedIPs
        self.assertTrue(hasattr(BannedIPs, 'ip_address'))

if __name__ == '__main__':
    unittest.main()
