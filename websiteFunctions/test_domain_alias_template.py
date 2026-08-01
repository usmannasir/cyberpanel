import pathlib
import re
import unittest


class DomainAliasTemplateTest(unittest.TestCase):
    def test_domain_alias_template_uses_alias_actions(self):
        template_path = pathlib.Path(__file__).with_name("templates") / "websiteFunctions" / "domainAlias.html"
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("removeAlias('{{ masterDomain }}', '{{ alias }}')", template)
        self.assertIn("issueSSL('{{ masterDomain }}', '{{ alias }}')", template)
        self.assertIn("{% for alias in aliases %}", template)
        self.assertIn('ng-click="addAliasFunc()"', template)
        self.assertIn('ng-model="aliasDomain"', template)
        self.assertIn("Are you sure you want to delete this alias?", template)
        self.assertNotIn("deleteChildDomain(record.childDomain)", template)
        self.assertNotIn("record in childDomains", template)
        # Create form must not call child-domain creation
        self.assertIsNone(
            re.search(r'ng-click="createDomain\(\)"', template),
            "Create Alias must call addAliasFunc(), not createDomain()",
        )
        self.assertIsNone(
            re.search(r'ng-model="domainNameCreate"', template),
            "Create Alias input must bind aliasDomain, not domainNameCreate",
        )


if __name__ == "__main__":
    unittest.main()
