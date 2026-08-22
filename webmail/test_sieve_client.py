import unittest

from webmail.services.sieve_client import SieveClient


class SieveRuleGenerationTests(unittest.TestCase):

    @staticmethod
    def rule(action_type, action_value):
        return {
            'name': 'Forward invoices',
            'condition_field': 'subject',
            'condition_type': 'contains',
            'condition_value': 'Invoice',
            'action_type': action_type,
            'action_value': action_value,
        }

    def test_redirect_is_emitted_without_invalid_require_extension(self):
        script = SieveClient.rules_to_sieve([
            self.rule('forward', 'archive@example.com'),
        ])

        self.assertIn('redirect "archive@example.com";', script)
        self.assertNotIn('require', script)

    def test_redirect_does_not_pollute_other_required_extensions(self):
        script = SieveClient.rules_to_sieve([
            self.rule('move', 'Invoices'),
            self.rule('forward', 'archive@example.com'),
        ])

        self.assertIn('require ["fileinto"];', script)
        self.assertNotIn('"redirect"', script)


if __name__ == '__main__':
    unittest.main()
