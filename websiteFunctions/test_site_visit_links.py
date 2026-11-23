"""No link on a website page starts with a bare host name.

A browser resolves href="example.com" or href="example.com/blog" against the
page that holds it, so such a link opens a path inside the panel instead of the
website. Every href and ng-href under websiteFunctions/templates/ that begins
with an interpolated value is checked: a site address must carry its scheme,
and a scope value the script assigns must be absolute, root-relative or come
from siteVisitURL().
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'websiteFunctions' / 'templates'
SCRIPTS = (
    ROOT / 'websiteFunctions' / 'static' / 'websiteFunctions' / 'websiteFunctions.js',
    ROOT / 'static' / 'websiteFunctions' / 'websiteFunctions.js',
)

LINK = re.compile(r'''\b(ng-href|href)\s*=\s*(["'])(.*?)\2''', re.S)
LEADING_VALUE = re.compile(r'^\s*(?:\{\$|\{\{)\s*([A-Za-z_$][\w$.]*)\s*(?:\$\}|\}\})')
# A value that holds a host name: web.domain, childDomain, wpsite.FinalURL, site.url.
SITE_ADDRESS = re.compile(r'(?:domain|domainname|finalurl|siteurl)$|^url$', re.I)
SAFE_START = re.compile(r'''^\s*(?:["'](?:https?://|/)|siteVisitURL\()''')


def template_links():
    for template in sorted(TEMPLATES.rglob('*.html')):
        text = template.read_text(encoding='utf-8', errors='replace')
        for match in LINK.finditer(text):
            line = text.count('\n', 0, match.start()) + 1
            yield template.relative_to(ROOT), line, match.group(1), match.group(3)


def assignments(script_text, name):
    pattern = re.compile(r'\$scope\.%s\s*=(?!=)\s*([^;\n]*)' % re.escape(name))
    return [value.strip() for value in pattern.findall(script_text)]


class SiteVisitLinkTests(unittest.TestCase):
    def test_no_template_link_starts_with_a_bare_site_address(self):
        scripts = [path.read_text(encoding='utf-8') for path in SCRIPTS]
        problems = []
        checked = 0
        for template, line, attribute, value in template_links():
            leading = LEADING_VALUE.match(value)
            if not leading:
                continue
            name = leading.group(1)
            where = '%s:%d %s="%s"' % (template, line, attribute, value)
            if SITE_ADDRESS.search(name.split('.')[-1]):
                problems.append('%s starts with a host name and no scheme' % where)
                continue
            if '.' in name:
                continue
            for script_path, script in zip(SCRIPTS, scripts):
                for assigned in assignments(script, name):
                    checked += 1
                    if not SAFE_START.match(assigned):
                        problems.append('%s takes $scope.%s = %s (%s), which is relative to the page'
                                        % (where, name, assigned, script_path.relative_to(ROOT)))
        self.assertGreater(checked, 0)
        self.assertEqual(problems, [])

    def test_success_links_of_the_installers_use_ng_href(self):
        for name in ('installWordPress.html', 'installPrestaShop.html', 'installMautic.html'):
            with self.subTest(template=name):
                text = (TEMPLATES / 'websiteFunctions' / name).read_text(encoding='utf-8')
                self.assertIn('<a ng-href="{$ installationURL $}" target="_blank" rel="noopener noreferrer"', text)
                self.assertNotIn('href="{$ installationURL $}" target', text.replace('ng-href', ''))

    def test_every_installer_result_address_comes_from_site_visit_url(self):
        for script_path in SCRIPTS:
            with self.subTest(script=str(script_path.relative_to(ROOT))):
                values = assignments(script_path.read_text(encoding='utf-8'), 'installationURL')
                self.assertEqual(len(values), 7)
                for value in values:
                    self.assertTrue(value.startswith('siteVisitURL(domain'), value)

    def test_both_script_copies_define_the_same_helper(self):
        helpers = []
        for script_path in SCRIPTS:
            text = script_path.read_text(encoding='utf-8')
            start = text.index('function siteVisitURL(')
            helpers.append(text[start:text.index('\n}\n', start)])
        self.assertEqual(helpers[0], helpers[1])


if __name__ == '__main__':
    unittest.main()
