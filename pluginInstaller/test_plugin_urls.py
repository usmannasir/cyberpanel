import pathlib
import tempfile
import unittest

from pluginInstaller.pluginInstaller import pluginInstaller


class PluginURLUpdateTests(unittest.TestCase):

    def test_inserted_plugin_route_is_valid_python_without_carriage_return(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            urls_path = pathlib.Path(temporary_directory) / 'urls.py'
            urls_path.write_text(
                'from django.urls import include, path\n\n'
                'urlpatterns = [\n'
                "    path('manageservices/', include('manageServices.urls')),\n"
                ']\n',
                encoding='utf-8',
            )

            pluginInstaller.upgradingURLs('examplePlugin', str(urls_path))

            updated = urls_path.read_text(encoding='utf-8')
            self.assertNotIn('\r', updated)
            self.assertIn(
                "    path('examplePlugin/', include('examplePlugin.urls')),\n",
                updated,
            )
            compile(updated, str(urls_path), 'exec')


if __name__ == '__main__':
    unittest.main()
