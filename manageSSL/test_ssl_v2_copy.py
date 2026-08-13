import pathlib
import unittest


class SSLV2CopyTests(unittest.TestCase):
    def test_automation_copy_names_only_supported_dns_integrations(self):
        template = (
            pathlib.Path(__file__).parent
            / 'templates'
            / 'manageSSL'
            / 'v2ManageSSL.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn('Namecheap', template)
        self.assertIn('Cloudflare', template)
        self.assertIn('PowerDNS', template)


if __name__ == '__main__':
    unittest.main()
