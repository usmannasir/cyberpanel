import unittest

from webmail.services.sieve_client import SieveClient, SieveRuleError


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



class SieveRuleInjectionTests(unittest.TestCase):

    def rule(self, **values):
        rule = {
            'name': 'Invoices',
            'condition_field': 'subject',
            'condition_type': 'contains',
            'condition_value': 'Invoice',
            'action_type': 'move',
            'action_value': 'Invoices',
        }
        rule.update(values)
        return rule

    def test_rule_name_cannot_leave_its_comment(self):
        script = SieveClient.rules_to_sieve([
            self.rule(name='x\nredirect "thief@example.net";\r\n#'),
        ])

        self.assertNotIn('\nredirect', script)
        self.assertEqual(1, script.count('if header'))
        self.assertTrue(script.splitlines()[2].startswith('# x redirect'))

    def test_values_are_quoted_strings(self):
        script = SieveClient.rules_to_sieve([
            self.rule(condition_value='a" "b" { discard; } if true {',
                      action_type='forward', action_value='x"@example.net'),
        ])

        self.assertIn('header :contains "Subject" "a\\" \\"b\\" { discard; } if true {"', script)
        self.assertIn('redirect "x\\"@example.net";', script)

    def test_unknown_fields_and_bad_sizes_never_reach_the_script(self):
        script = SieveClient.rules_to_sieve([
            self.rule(condition_field='From" "x"; discard; #'),
            self.rule(condition_field='size', condition_type='greater_than',
                      condition_value='1 { discard; } if true'),
            self.rule(condition_field='size', condition_type='greater_than', condition_value='5m'),
        ])

        self.assertNotIn('discard', script)
        self.assertIn('if size :over 5M {', script)
        self.assertEqual(1, script.count('if '))

    def test_validation_accepts_what_the_filter_page_offers(self):
        for values in (
            {},
            {'condition_field': 'from', 'condition_type': 'is'},
            {'condition_field': 'to', 'condition_type': 'matches', 'condition_value': '*@example.net'},
            {'condition_field': 'size', 'condition_type': 'greater_than', 'condition_value': '100K'},
            {'action_type': 'forward', 'action_value': 'archive@example.net'},
            {'action_type': 'discard', 'action_value': ''},
            {'action_type': 'flag', 'action_value': ''},
        ):
            self.assertTrue(SieveClient.validate_rule(self.rule(**values)), values)

    def test_validation_refuses_anything_else(self):
        for values in (
            {'condition_field': 'X-Spam'},
            {'condition_type': 'regex'},
            {'condition_type': 'greater_than'},
            {'condition_field': 'size', 'condition_type': 'contains', 'condition_value': '10'},
            {'condition_field': 'size', 'condition_type': 'greater_than', 'condition_value': '10 or more'},
            {'action_type': 'vacation'},
            {'action_type': 'forward', 'action_value': 'not an address'},
            {'action_type': 'forward', 'action_value': 'a@example.net, b@example.net'},
            {'action_type': 'forward', 'action_value': 'a@example.net,b@example.org'},
            {'action_type': 'forward', 'action_value': '<a@example.net>'},
            {'action_type': 'move', 'action_value': ''},
            {'name': 'two\nlines'},
            {'condition_value': 'Invoice\r\n'},
            {'condition_value': None},
        ):
            with self.assertRaises(SieveRuleError, msg=values):
                SieveClient.validate_rule(self.rule(**values))


if __name__ == '__main__':
    unittest.main()
