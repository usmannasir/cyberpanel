#!/usr/bin/env python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
import django
django.setup()
from CyberCP.secMiddleware import CONTENT_SECURITY_POLICY

class CSPInsightsTests(unittest.TestCase):
    def test_cloudflare_insights_allowed(self):
        self.assertIn('static.cloudflareinsights.com', CONTENT_SECURITY_POLICY)

if __name__ == '__main__':
    unittest.main()
