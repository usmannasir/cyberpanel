import pathlib
import tempfile
import unittest

from pluginInstaller.pluginInstaller import pluginInstaller


class PluginURLUpdateTests(unittest.TestCase):

    @staticmethod
    def write_urls(directory, content):
        urls_path = pathlib.Path(directory) / 'urls.py'
        urls_path.write_text(content, encoding='utf-8')
        return urls_path

    def test_inserted_plugin_route_is_valid_python_without_carriage_return(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            urls_path = self.write_urls(
                temporary_directory,
                'from django.urls import include, path\n\n'
                'urlpatterns = [\n'
                "    path('manageservices/', include('manageServices.urls')),\n"
                ']\n',
            )

            pluginInstaller.upgradingURLs('examplePlugin', str(urls_path))

            updated = urls_path.read_text(encoding='utf-8')
            self.assertNotIn('\r', updated)
            self.assertIn(
                "    path('examplePlugin/', include('examplePlugin.urls')),\n",
                updated,
            )
            compile(updated, str(urls_path), 'exec')

    def test_removal_only_deletes_exact_current_plugin_route(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            urls_path = self.write_urls(
                temporary_directory,
                'from django.urls import include, path\n\n'
                '# examplePlugin is documented here and must remain.\n'
                'urlpatterns = [\n'
                "    path('examplePlugin/', include('examplePlugin.urls')),\n"
                "    path('examplePluginTools/', include('examplePluginTools.urls')),\n"
                ']\n',
            )

            self.assertTrue(pluginInstaller.removeFromURLs('examplePlugin', str(urls_path)))

            updated = urls_path.read_text(encoding='utf-8')
            self.assertNotIn("path('examplePlugin/', include('examplePlugin.urls'))", updated)
            self.assertIn('# examplePlugin is documented here and must remain.', updated)
            self.assertIn(
                "path('examplePluginTools/', include('examplePluginTools.urls'))",
                updated,
            )
            compile(updated, str(urls_path), 'exec')

    def test_removal_supports_legacy_url_route(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            urls_path = self.write_urls(
                temporary_directory,
                'from django.conf.urls import include, url\n\n'
                'urlpatterns = [\n'
                '    url(r"^examplePlugin/", include("examplePlugin.urls")),\n'
                ']\n',
            )

            self.assertTrue(pluginInstaller.removeFromURLs('examplePlugin', str(urls_path)))

            updated = urls_path.read_text(encoding='utf-8')
            self.assertNotIn('examplePlugin.urls', updated)
            compile(updated, str(urls_path), 'exec')

    def test_removal_rejects_invalid_or_missing_plugin_without_rewrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            urls_path = self.write_urls(
                temporary_directory,
                'from django.urls import include, path\n\n'
                'urlpatterns = [\n'
                "    path('examplePlugin/', include('examplePlugin.urls')),\n"
                ']\n',
            )
            original = urls_path.read_bytes()

            self.assertFalse(pluginInstaller.removeFromURLs('examplePlugin;bad', str(urls_path)))
            self.assertEqual(original, urls_path.read_bytes())
            self.assertFalse(pluginInstaller.removeFromURLs('missingPlugin', str(urls_path)))
            self.assertEqual(original, urls_path.read_bytes())


SIDEBAR_WITH_MARKER = (
    '{% load i18n %}\n'
    '        <div class="section-header">{% trans "HOSTING" %}</div>\n'
    '\n'
    '        <a href="{% url \'listWebsites\' %}" class="menu-item">\n'
    '            <div class="icon-wrapper"><i class="fas fa-globe"></i></div>\n'
    '            <span>{% trans "Websites" %}</span>\n'
    '        </a>\n'
    '        {# pluginsList #}\n'
    '\n'
    '        <!-- Build Services -->\n'
)

LEGACY_SIDEBAR_ENTRY = (
    '                                <li><a href="{% url \'legacyPlugin\' %}" '
    'title="{% trans \'legacyPlugin\' %}"><span>{% trans "legacyPlugin" %}</span></a></li>\n'
)


class PluginSidebarLinkTests(unittest.TestCase):

    @staticmethod
    def write_sidebar(directory, content):
        template_path = pathlib.Path(directory) / 'index.html'
        template_path.write_text(content, encoding='utf-8')
        return template_path

    def test_add_appends_flat_menu_item_after_marker(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            template_path = self.write_sidebar(temporary_directory, SIDEBAR_WITH_MARKER)

            self.assertTrue(pluginInstaller.addInterfaceLink('softaculous', str(template_path)))

            lines = template_path.read_text(encoding='utf-8').splitlines()
            marker_index = lines.index('        {# pluginsList #}')
            injected = lines[marker_index + 1]
            self.assertIn("<a href=\"{% url 'softaculous' %}\" class=\"menu-item\">", injected)
            self.assertIn('<div class="icon-wrapper"><i class="fas fa-puzzle-piece"></i></div>', injected)
            self.assertIn('<span>{% trans "softaculous" %}</span></a>', injected)
            # Everything except the one injected line is unchanged.
            self.assertEqual(
                lines[:marker_index + 1] + lines[marker_index + 2:],
                SIDEBAR_WITH_MARKER.splitlines(),
            )

    def test_add_without_marker_reports_failure_and_touches_nothing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            template_path = self.write_sidebar(
                temporary_directory,
                SIDEBAR_WITH_MARKER.replace('        {# pluginsList #}\n', ''),
            )
            original = template_path.read_bytes()

            self.assertFalse(pluginInstaller.addInterfaceLink('softaculous', str(template_path)))
            self.assertEqual(original, template_path.read_bytes())

    def test_add_rejects_invalid_plugin_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            template_path = self.write_sidebar(temporary_directory, SIDEBAR_WITH_MARKER)
            original = template_path.read_bytes()

            self.assertFalse(pluginInstaller.addInterfaceLink('bad;name', str(template_path)))
            self.assertEqual(original, template_path.read_bytes())

    def test_remove_deletes_only_the_plugins_own_entry(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            template_path = self.write_sidebar(
                temporary_directory,
                SIDEBAR_WITH_MARKER
                + '        <a href="{% url \'softaculous\' %}" class="menu-item">'
                  '<div class="icon-wrapper"><i class="fas fa-puzzle-piece"></i></div>'
                  '<span>{% trans "softaculous" %}</span></a>\n'
                + LEGACY_SIDEBAR_ENTRY,
            )

            self.assertTrue(pluginInstaller.removeInterfaceLink('softaculous', str(template_path)))
            self.assertTrue(pluginInstaller.removeInterfaceLink('legacyPlugin', str(template_path)))

            updated = template_path.read_text(encoding='utf-8')
            self.assertNotIn('softaculous', updated)
            self.assertNotIn('legacyPlugin', updated)
            # The sidebar otherwise returns to its pre-install content.
            self.assertEqual(updated, SIDEBAR_WITH_MARKER)

    def test_remove_rejects_invalid_plugin_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            template_path = self.write_sidebar(temporary_directory, SIDEBAR_WITH_MARKER)
            original = template_path.read_bytes()

            self.assertFalse(pluginInstaller.removeInterfaceLink('soft;aculous', str(template_path)))
            self.assertEqual(original, template_path.read_bytes())


if __name__ == '__main__':
    unittest.main()
