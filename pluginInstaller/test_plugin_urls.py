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


if __name__ == '__main__':
    unittest.main()
