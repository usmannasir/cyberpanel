import pathlib
import unittest


class DomainAliasTemplateTest(unittest.TestCase):
    def test_domain_alias_template_uses_alias_actions(self):
        template_path = pathlib.Path(__file__).with_name("templates") / "websiteFunctions" / "domainAlias.html"
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("removeAlias('{{ masterDomain }}', '{{ alias }}')", template)
        self.assertIn("issueSSL('{{ masterDomain }}', '{{ alias }}')", template)
        self.assertIn("{% for alias in aliases %}", template)
        self.assertNotIn("deleteChildDomain(record.childDomain)", template)
        self.assertNotIn("record in childDomains", template)


if __name__ == "__main__":
    unittest.main()
