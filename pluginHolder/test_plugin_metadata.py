"""Plugin-list failures stay local to metadata; no plugin code is executed."""
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from pluginHolder import plugin_metadata as metadata


class PluginMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.registry = self.root / 'registry'
        self.application = self.root / 'applications'
        self.registry.mkdir()
        self.application.mkdir()
        logger = patch.object(metadata, 'logger')
        self.log = logger.start()
        self.addCleanup(logger.stop)

    def plugin(self, folder, content=None):
        (self.registry / folder).touch()
        target = self.application / folder
        target.mkdir()
        if content is not None:
            (target / 'meta.xml').write_text(content)
        # Listing must not import an installed module to obtain its description.
        (target / '__init__.py').write_text("raise RuntimeError('plugin code executed')")
        return target / 'meta.xml'

    def valid(self, folder, description='Description'):
        return self.plugin(folder, '<plugin><name>' + folder + '</name>'
                           '<type>Utility</type><description>' + description +
                           '</description><version>1.2</version></plugin>')

    def read(self):
        return metadata.installed_plugin_metadata(str(self.registry), str(self.application))

    def test_valid_metadata_keeps_existing_display_fields(self):
        self.valid('example')
        result = self.read()
        self.assertFalse(result['pluginListUnavailable'])
        self.assertEqual([{'name': 'example', 'type': 'Utility', 'desc': 'Description',
                           'version': '1.2', 'metadata_available': True}], result['plugins'])
        self.log.warning.assert_not_called()

    def test_bad_metadata_does_not_hide_valid_plugins_before_or_after_it(self):
        self.valid('a_valid')
        self.valid('z_valid')
        bad = self.plugin('m_bad')
        for content in (None, '<plugin', '<?xml version="1.0" encoding="not-an-encoding"?><plugin/>',
                        '<plugin><name>Incomplete</name></plugin>',
                        '<plugin><name> </name><type>Utility</type><description />'
                        '<version>1</version></plugin>'):
            with self.subTest(content=content):
                if bad.exists():
                    bad.unlink()
                if content is not None:
                    bad.write_text(content)
                result = self.read()
                self.assertFalse(result['pluginListUnavailable'])
                self.assertEqual(['a_valid', 'm_bad', 'z_valid'],
                                 [item['name'] for item in result['plugins']])
                self.assertEqual([True, False, True],
                                 [item['metadata_available'] for item in result['plugins']])
                self.assertEqual('', result['plugins'][1]['desc'])

    def test_unreadable_metadata_is_local_and_does_not_leak_exception(self):
        bad = self.valid('a_bad')
        self.valid('z_valid')
        real_parse = metadata.ElementTree.parse
        def parse(path):
            if Path(path) == bad:
                raise PermissionError('private-path and private-detail')
            return real_parse(path)
        with patch.object(metadata.ElementTree, 'parse', side_effect=parse):
            result = self.read()
        self.assertEqual([False, True], [item['metadata_available'] for item in result['plugins']])
        self.assertNotIn('private-', repr(result))
        self.log.warning.assert_called_once()

    def test_empty_description_is_valid(self):
        self.valid('example', '')
        self.assertTrue(self.read()['plugins'][0]['metadata_available'])

    def test_missing_registry_means_no_installed_plugins(self):
        self.registry.rmdir()
        self.assertEqual({'plugins': [], 'pluginListUnavailable': False}, self.read())

    def test_unreadable_or_invalid_registry_is_not_reported_as_empty_success(self):
        for error in (PermissionError('private detail'), NotADirectoryError('private detail')):
            with self.subTest(error=type(error).__name__):
                with patch.object(metadata.os, 'listdir', side_effect=error):
                    self.assertEqual({'plugins': [], 'pluginListUnavailable': True}, self.read())

    def test_broken_registry_link_is_unavailable_instead_of_empty(self):
        self.registry.rmdir()
        self.registry.symlink_to(self.root / 'missing-registry')
        self.assertEqual({'plugins': [], 'pluginListUnavailable': True}, self.read())

    def test_view_keeps_admin_gate_and_passes_listing_state(self):
        path = Path(__file__).with_name('views.py')
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'installed')
        context = {'plugins': [], 'pluginListUnavailable': True}
        request = object()
        response = object()
        renderer = Mock(return_value=NS(render=Mock(return_value=response)))
        check_home = Mock()
        namespace = {'mailUtilities': NS(checkHome=check_home), 'httpProc': renderer,
                     'installed_plugin_metadata': Mock(return_value=context)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        self.assertIs(response, namespace['installed'](request))
        check_home.assert_called_once_with()
        renderer.assert_called_once_with(request, 'pluginHolder/plugins.html', context, 'admin')


if __name__ == '__main__':
    unittest.main()
