"""Render the real plugin list with an isolated parent template."""
from pathlib import Path
import unittest

from django.conf import settings
from django.template import Context, Engine
from django.test import SimpleTestCase, override_settings


@override_settings(USE_I18N=False)
class PluginMetadataTemplateTests(SimpleTestCase):
    def render(self, context):
        source = (Path(__file__).parent / 'templates/pluginHolder/plugins.html').read_text()
        engine = Engine(loaders=[('django.template.loaders.locmem.Loader', {
            'baseTemplate/index.html': '{% block content %}{% endblock %}'})],
            libraries={'i18n': 'django.templatetags.i18n',
                       'static': 'django.templatetags.static'})
        return engine.from_string(source).render(Context(context, autoescape=True))

    def test_mixed_list_keeps_valid_metadata_and_escapes_unavailable_plugin_name(self):
        html = self.render({'pluginListUnavailable': False, 'plugins': [
            {'name': 'Good plugin', 'type': 'Utility', 'desc': 'Valid description',
             'version': '1.2', 'metadata_available': True},
            {'name': '<script>bad</script>', 'type': '', 'desc': '',
             'version': '', 'metadata_available': False}]})
        self.assertEqual(2, html.count('Metadata unavailable'))
        self.assertEqual(2, html.count('Valid description'))
        self.assertEqual(2, html.count('Good plugin'))
        self.assertEqual(2, html.count('&lt;script&gt;bad&lt;/script&gt;'))
        self.assertNotIn('<script>bad</script>', html)
        self.assertNotIn('No Plugins Installed', html)

    def test_unavailable_registry_does_not_claim_no_plugins(self):
        html = self.render({'plugins': [], 'pluginListUnavailable': True})
        self.assertIn('The installed plugin list is unavailable', html)
        self.assertNotIn('No Plugins Installed', html)

    def test_empty_registry_keeps_normal_empty_state(self):
        html = self.render({'plugins': [], 'pluginListUnavailable': False})
        self.assertIn('No Plugins Installed', html)
        self.assertNotIn('The installed plugin list is unavailable', html)


if __name__ == '__main__':
    if not settings.configured:
        settings.configure(USE_I18N=False)
    unittest.main()
