import pathlib
import unittest


class FreeWordPressNavigationTests(unittest.TestCase):

    def test_free_flow_selects_an_existing_website(self):
        repository = pathlib.Path(__file__).parents[1]
        template = (
            repository
            / 'websiteFunctions'
            / 'templates'
            / 'websiteFunctions'
            / 'freeWordpressInstall.html'
        ).read_text(encoding='utf-8')
        self.assertIn('{% for domain in websiteList %}', template)
        self.assertIn("{% url 'wordpressInstall' domain %}", template)
        self.assertNotIn("{% url 'pricing' %}", template)

    def test_wordpress_create_no_longer_redirects_free_users_to_pricing(self):
        repository = pathlib.Path(__file__).parents[1]
        source = (repository / 'websiteFunctions' / 'website.py').read_text(encoding='utf-8')
        method = source[source.index('    def WPCreate('):source.index('    def ListWPSites(')]
        self.assertIn('freeWordpressInstall.html', method)
        self.assertNotIn("reverse('pricing')", method)


if __name__ == '__main__':
    unittest.main()
