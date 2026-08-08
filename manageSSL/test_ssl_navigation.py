import pathlib
import unittest


class SSLNavigationTests(unittest.TestCase):

    def test_standard_ssl_links_do_not_open_premium_manager(self):
        repository = pathlib.Path(__file__).parents[1]
        templates = (
            repository / 'baseTemplate' / 'templates' / 'baseTemplate' / 'homePage.html',
            repository / 'baseTemplate' / 'templates' / 'baseTemplate' / 'index.html',
            repository / 'baseTemplate' / 'templates' / 'baseTemplate' / 'siteWorkspace.html',
            repository / 'baseTemplate' / 'templates' / 'baseTemplate' / 'hub.html',
            repository / 'websiteFunctions' / 'templates' / 'websiteFunctions' / 'website.html',
        )
        for template_path in templates:
            template = template_path.read_text(encoding='utf-8')
            self.assertTrue(
                "url 'manageSSL'" in template or 'url "manageSSL"' in template,
                str(template_path),
            )
            self.assertNotIn('v2ManageSSL', template, str(template_path))

    def test_premium_manager_remains_available_from_ssl_home(self):
        ssl_home = (
            pathlib.Path(__file__).with_name('templates')
            / 'manageSSL'
            / 'index.html'
        ).read_text(encoding='utf-8')
        self.assertIn("{% url 'v2ManageSSL' %}", ssl_home)
        self.assertIn('SSL v2', ssl_home)


if __name__ == '__main__':
    unittest.main()
