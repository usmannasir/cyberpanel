"""Schema checks plus real secure-file tests (filesystem cases require root)."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Replaced with the owning project's package at installation time.
from CyberCP import gdriveSettings as config


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.panel = {'version': 1, 'enabled': True,
                      'platform_origin': 'https://platform.example', 'installation_key': 'a' * 43}
        self.platform = {'version': 1, 'enabled': True,
                         'platform_origin': 'https://platform.example',
                         'database': '/var/lib/cyberhosting/gdrive/handoffs.sqlite3',
                         'installations': [{'origin': 'https://panel.example:8090', 'key': 'a' * 43}]}

    def test_project_settings_import_the_loader_mapping(self):
        import ast
        role = 'platform' if config.__name__.startswith('CommonUtils.') else 'panel'
        project = 'CyberHosting' if role == 'platform' else 'CyberCP'
        source_path = Path(__file__).resolve().parents[1] / project / 'settings.py'
        tree = ast.parse(source_path.read_text())
        selected = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and any(alias.asname == '_load_gdrive_settings' for alias in node.names):
                selected.append(node)
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == '_gdrive_settings' or node.targets[0].id.startswith('GDRIVE_'):
                    selected.append(node)
        namespace = {}
        document = self.platform if role == 'platform' else self.panel
        with patch.object(config, '_read_private_json', return_value=document) as reader:
            exec(compile(ast.Module(body=selected, type_ignores=[]), str(source_path), 'exec'), namespace)
        reader.assert_called_once_with(config.CONFIG_PATHS[role])
        self.assertTrue(namespace['GDRIVE_HANDOFF_ENABLED'])
        for key, value in config._validate(document, role).items():
            self.assertEqual(namespace[key], value)

    def test_public_default_never_overrides_invalid_or_disabled_file(self):
        with patch.object(config, '_read_private_json', return_value={'version':1,'enabled':False}):
            result = config.load_gdrive_settings('panel')
            self.assertFalse(result['GDRIVE_HANDOFF_ENABLED'])
            self.assertFalse(result['GDRIVE_HANDOFF_PUBLIC'])
        for exception in (PermissionError(), ValueError(), OSError()):
            with patch.object(config, '_read_private_json', side_effect=exception):
                with self.assertLogs(config.__name__, level='WARNING'):
                    result = config.load_gdrive_settings('panel')
                self.assertFalse(result['GDRIVE_HANDOFF_ENABLED'])
                self.assertFalse(result['GDRIVE_HANDOFF_PUBLIC'])

    def test_panel_settings(self):
        result = config._validate(self.panel, 'panel')
        self.assertTrue(result['GDRIVE_HANDOFF_ENABLED'])
        self.assertEqual(result['GDRIVE_HANDOFF_REGISTRATION_KEY'], 'a' * 43)
        self.assertFalse(result['GDRIVE_HANDOFF_PUBLIC'])

    def test_platform_generates_exact_both_callback_pair(self):
        result = config._validate(self.platform, 'platform')
        expected = ['https://panel.example:8090/backup/gDriveSetup',
                    'https://panel.example:8090/IncrementalBackups/ConfigureV2BackupSetup']
        self.assertEqual(result['GDRIVE_HANDOFF_CALLBACKS'], expected)
        self.assertEqual(result['GDRIVE_HANDOFF_CLIENT_KEYS'], {url: 'a' * 43 for url in expected})

    def test_disabled_configuration_needs_no_keys(self):
        for role in config.CONFIG_PATHS:
            result = config._validate({'version': 1, 'enabled': False}, role)
            self.assertFalse(result['GDRIVE_HANDOFF_ENABLED'])

    def test_wrong_types_unknown_and_missing_fields_rejected(self):
        for update in ({'enabled': 'true'}, {'version': True}, {'version': 2}, {'callbacks': ['https://evil.example']},
                       {'installation_key': 'short'}, {'installation_key': 123}):
            candidate = dict(self.panel, **update)
            with self.assertRaises(ValueError):
                config._validate(candidate, 'panel')
        candidate = dict(self.panel)
        del candidate['platform_origin']
        with self.assertRaises(ValueError):
            config._validate(candidate, 'panel')

    def test_untrusted_callback_shapes_rejected(self):
        for origin in ('http://panel.example', 'https://*.example', 'https://user@panel.example',
                       'https://panel.example/path', 'https://panel.example/', 'https://panel.example?callback=evil',
                       'https://panel.example#fragment', 'https://panel.example\\evil',
                       'https://panel.example\n', 'https://panel.example:99999', 'https://Panel.example',
                       'https://panel.example?', 'https://panel.example#', 'https://panel.example:'):
            candidate = copy.deepcopy(self.platform)
            candidate['installations'][0]['origin'] = origin
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                config._validate(candidate, 'platform')

    def test_installation_key_reuse_and_duplicate_origin_rejected(self):
        for entry in ({'origin': 'https://other.example', 'key': 'a' * 43},
                      {'origin': 'https://panel.example:8090', 'key': 'b' * 43},
                      {'origin': 'https://other.example', 'key': 'b' * 43, 'callback': 'https://evil.example'}):
            candidate = copy.deepcopy(self.platform)
            candidate['installations'].append(entry)
            with self.assertRaises(ValueError):
                config._validate(candidate, 'platform')

    def test_no_installations_or_nonabsolute_database_rejected(self):
        for update in ({'installations': []}, {'installations': {}}, {'database': 'relative.db'},
                       {'database': '/var/../tmp/private.db'}, {'database': '/'}):
            with self.assertRaises(ValueError):
                config._validate(dict(self.platform, **update), 'platform')

    def test_missing_and_invalid_config_fail_closed_without_secrets_in_logs(self):
        for role in config.CONFIG_PATHS:
            with patch.object(config, '_read_private_json', side_effect=FileNotFoundError):
                self.assertEqual(config.load_gdrive_settings(role)['GDRIVE_HANDOFF_ENABLED'], role == 'panel')
            with patch.object(config, '_read_private_json', side_effect=ValueError('SECRET TEST VALUE')):
                with self.assertLogs(config.__name__, level='WARNING') as logs:
                    self.assertFalse(config.load_gdrive_settings(role)['GDRIVE_HANDOFF_ENABLED'])
                self.assertNotIn('SECRET TEST VALUE', str(logs.output))

    def test_environment_cannot_override_fixed_config_path_or_enable_gate(self):
        with patch.dict(os.environ, {'GDRIVE_HANDOFF_ENABLED': 'true',
                                     'GDRIVE_HANDOFF_CONFIG': '/tmp/untrusted.json'}):
            with patch.object(config, '_read_private_json', side_effect=FileNotFoundError) as reader:
                result = config.load_gdrive_settings('panel')
                self.assertTrue(result['GDRIVE_HANDOFF_ENABLED'])
                self.assertEqual(result['GDRIVE_PLATFORM_BASE_URL'], 'https://platform.cyberpersons.com')
                self.assertTrue(result['GDRIVE_HANDOFF_PUBLIC'])
                self.assertEqual(result['GDRIVE_HANDOFF_REGISTRATION_KEY'], '')
                reader.assert_called_once_with('/etc/cyberpanel/gdrive-handoff.json')


@unittest.skipUnless(os.geteuid() == 0, 'real root-owned file integration tests')
class SecureFileTests(unittest.TestCase):
    def setUp(self):
        # Use the root test runner's private home. /tmp is intentionally
        # rejected by the loader even when the final file is 0600.
        self.temp = tempfile.TemporaryDirectory(prefix='.gdrive-test-', dir=os.path.expanduser('~'))
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'handoff.json'
        self.path.write_text(json.dumps({'version': 1, 'enabled': False}))
        self.path.chmod(0o600)

    def test_real_private_and_group_readable_files(self):
        for mode in (0o600, 0o640, 0o400, 0o440):
            self.path.chmod(mode)
            self.assertEqual(config._read_private_json(str(self.path)), {'version': 1, 'enabled': False})

    def test_public_writable_executable_or_nonroot_owned_files_rejected(self):
        for mode in (0o644, 0o660, 0o700, 0o4600):
            self.path.chmod(mode)
            with self.assertRaises(ValueError):
                config._read_private_json(str(self.path))
        self.path.chmod(0o600)
        os.chown(self.path, 65534, 65534)
        with self.assertRaises(ValueError):
            config._read_private_json(str(self.path))

    def test_symlinks_hardlinks_and_nonregular_files_rejected(self):
        link = self.path.parent / 'link'
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            config._read_private_json(str(link))
        link.unlink()
        os.link(self.path, link)
        with self.assertRaises(ValueError):
            config._read_private_json(str(self.path))
        link.unlink()
        os.mkfifo(link, 0o600)
        with self.assertRaises(ValueError):
            config._read_private_json(str(link))

    def test_writable_and_symlink_ancestors_rejected(self):
        self.path.parent.chmod(0o770)
        with self.assertRaises(ValueError):
            config._read_private_json(str(self.path))
        self.path.parent.chmod(0o700)
        link = self.path.parent / 'nested'
        link.symlink_to(self.path.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            config._read_private_json(str(link / self.path.name))

    def test_oversized_duplicate_keys_invalid_utf8_and_constants_rejected(self):
        for content in (b' ' * (config.MAX_BYTES + 1), b'{"enabled":false,"enabled":true}',
                        b'\xff', b'{"version":NaN}'):
            self.path.write_bytes(content)
            with self.assertRaises((ValueError, UnicodeError)):
                config._read_private_json(str(self.path))

    def test_actual_file_to_valid_enabled_settings_and_private_callback_pair(self):
        value = {'version': 1, 'enabled': True, 'platform_origin': 'https://platform.example',
                 'database': '/var/lib/cyberhosting/gdrive/handoffs.sqlite3',
                 'installations': [{'origin': 'https://panel.example:8090', 'key': 'z' * 43}]}
        self.path.write_text(json.dumps(value))
        result = config.load_gdrive_settings('platform', str(self.path))
        self.assertTrue(result['GDRIVE_HANDOFF_ENABLED'])
        self.assertEqual(len(result['GDRIVE_HANDOFF_CALLBACKS']), 2)

    def test_loaded_panel_settings_reach_actual_registration_client(self):
        from django.conf import settings
        if not settings.configured:
            settings.configure(SECRET_KEY='synthetic-config-integration', DEFAULT_CHARSET='utf-8')
        from django.test import override_settings
        from IncBackups import gdrive_oauth
        from unittest.mock import Mock
        document = {'version': 1, 'enabled': True, 'platform_origin': 'https://platform.example',
                    'installation_key': 'z' * 43}
        self.path.write_text(json.dumps(document))
        configured = config.load_gdrive_settings('panel', str(self.path))
        result = Mock(status_code=200)
        result.json.return_value = {'status': 1}
        with override_settings(**configured, SESSION_ENGINE='django.contrib.sessions.backends.db'):
            self.assertEqual(gdrive_oauth._base(), 'https://platform.example')
            with patch.object(gdrive_oauth.requests, 'post', return_value=result) as send:
                gdrive_oauth._post(gdrive_oauth._base(), '/gDrive/register', {'flow_type': 'normal'})
            self.assertEqual(send.call_args.kwargs['headers']['X-GDrive-Installation-Key'], 'z' * 43)
            self.assertFalse(send.call_args.kwargs['allow_redirects'])
        document['enabled'] = False
        self.path.write_text(json.dumps(document))
        with override_settings(**config.load_gdrive_settings('panel', str(self.path))):
            with self.assertRaises(RuntimeError):
                gdrive_oauth._base()
