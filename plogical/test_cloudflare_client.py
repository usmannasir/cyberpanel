#!/usr/bin/env python
import os, sys, unittest
sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
import django
django.setup()
from plogical.dnsUtilities import DNS

class CloudFlareClientTests(unittest.TestCase):
    def test_api_token_auth(self):
        cf = DNS.createCloudFlareClient('', 'tok_abc', 'api_token')
        self.assertIsNotNone(cf)

    def test_global_key_requires_email(self):
        with self.assertRaises(ValueError):
            DNS.createCloudFlareClient('', 'key', 'global_key')

    def test_invalid_auth_type_falls_back(self):
        cf = DNS.createCloudFlareClient('a@b.com', 'secret', 'bogus')
        self.assertIsNotNone(cf)

if __name__ == '__main__':
    unittest.main()
