import os
import unittest


class FirewallStaticBundleTests(unittest.TestCase):

    def test_collected_bundle_matches_application_source(self):
        root = os.path.dirname(os.path.dirname(__file__))
        source = os.path.join(root, 'firewall', 'static', 'firewall', 'firewall.js')
        collected = os.path.join(root, 'static', 'firewall', 'firewall.js')
        with open(source, 'rb') as source_file, open(collected, 'rb') as collected_file:
            self.assertEqual(source_file.read(), collected_file.read())

    def test_templates_use_current_firewall_asset_revision(self):
        root = os.path.dirname(os.path.dirname(__file__))
        templates = (
            os.path.join(root, 'baseTemplate', 'templates', 'baseTemplate', 'index.html'),
            os.path.join(root, 'firewall', 'templates', 'firewall', 'imunify.html'),
            os.path.join(root, 'firewall', 'templates', 'firewall', 'imunifyAV.html'),
            os.path.join(root, 'firewall', 'templates', 'firewall', 'notAvailableAV.html'),
            os.path.join(root, 'firewall', 'templates', 'firewall', 'modSecurityRulesPacks.html'),
        )
        expected = "{% static 'firewall/firewall.js' %}?v={{ CP_VERSION }}-2"
        for template in templates:
            with self.subTest(template=template), open(template, encoding='utf-8') as template_file:
                self.assertIn(expected, template_file.read())


if __name__ == '__main__':
    unittest.main()
