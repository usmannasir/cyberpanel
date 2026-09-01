#!/usr/bin/env python
import os, sys, unittest
sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

class DashboardPollingJsTests(unittest.TestCase):
    def test_system_status_js_polling_guard(self):
        paths = [
            '/home/Github/cyberPanel-repos/cyberpanel/baseTemplate/static/baseTemplate/custom-js/system-status.js',
            '/home/Github/cyberPanel-repos/cyberpanel/static/baseTemplate/custom-js/system-status.js',
        ]
        first = open(paths[0]).read()
        second = open(paths[1]).read()
        self.assertEqual(first, second, 'system-status.js copies must be byte-identical')
        self.assertIn('pollInFlight', first)
        self.assertIn('pollInterval = 5000', first)
        self.assertNotIn('sizeDisplayUnit', first)

if __name__ == '__main__':
    unittest.main()
