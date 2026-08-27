import os
import pathlib
import shlex
import stat
import tempfile
import unittest
from unittest import mock

from plogical.imunify_integration import (
    CLSCRIPT_OPTIONS,
    IMUNIFY_360_UI,
    IMUNIFY_AV_UI,
    build_deploy_commands,
    build_install_worker_command,
    build_imunify360_integration_conf,
    build_imunifyav_integration_conf,
    chmod_imunify_execute_files,
    detect_imunify_product,
    ensure_install_status_file,
    ensure_clscripts_executable,
    integration_conf_needs_repair,
    read_install_status,
    repair_integration_conf,
    run_deploy_commands,
)


class ImunifyIntegrationTests(unittest.TestCase):

    def test_cagefs_prefers_cyberpanel_modules_over_system_packages(self):
        cagefs_source = (
            pathlib.Path(__file__).parents[1] / 'CLManager' / 'CageFS.py'
        ).read_text(encoding='utf-8')
        path_setup = "sys.path.insert(0, '/usr/local/CyberCP')"
        self.assertIn(path_setup, cagefs_source)
        self.assertLess(cagefs_source.index(path_setup), cagefs_source.index('django.setup()'))

    def test_detects_ui_path_independent_of_equals_spacing(self):
        for separator in ('=', '= ', ' =', ' = '):
            av_config = '[paths]\nui_path%s%s\n' % (separator, IMUNIFY_AV_UI)
            full_config = '[paths]\nui_path%s%s\n' % (separator, IMUNIFY_360_UI)
            self.assertEqual('av', detect_imunify_product(av_config))
            self.assertEqual('360', detect_imunify_product(full_config))

    def test_detection_only_uses_the_ui_path_setting(self):
        config = '[paths]\nui_path = /srv/security\n# old imunifyav path\n'
        self.assertIsNone(detect_imunify_product(config))

    def test_generated_configs_include_required_panel_integrations(self):
        for config in (
            build_imunifyav_integration_conf(),
            build_imunify360_integration_conf(),
        ):
            self.assertIn('[integration_scripts]', config)
            self.assertIn('panel_info = /usr/local/CyberCP/CLScript/panel_info.py', config)
            self.assertIn('users = /usr/local/CyberCP/CLScript/CloudLinuxUsers.py', config)
            self.assertIn('domains = /usr/local/CyberCP/CLScript/CloudLinuxDomains.py', config)
            self.assertIn('[malware]', config)
            self.assertIn('[web_server]', config)

    def test_repair_preserves_the_detected_product(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, 'integration.conf')
            pathlib.Path(config_path).write_text(
                '[paths]\nui_path = %s\n' % IMUNIFY_AV_UI,
                encoding='utf-8',
            )

            self.assertTrue(integration_conf_needs_repair(config_path))
            self.assertEqual('av', repair_integration_conf(config_path))
            repaired = pathlib.Path(config_path).read_text(encoding='utf-8')
            self.assertEqual('av', detect_imunify_product(repaired))
            self.assertFalse(integration_conf_needs_repair(config_path))

    def test_unknown_config_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, 'integration.conf')
            original = '[paths]\nui_path = /srv/security\n'
            pathlib.Path(config_path).write_text(original, encoding='utf-8')

            self.assertIsNone(repair_integration_conf(config_path))
            self.assertEqual(
                original,
                pathlib.Path(config_path).read_text(encoding='utf-8'),
            )

    def test_deploy_commands_pass_the_license_key_as_one_argument(self):
        key = 'license-key; touch /tmp/should-not-run'
        commands = build_deploy_commands('360', key=key, deploy_tmp='/tmp/imunify test')
        install_args = commands[-1]

        self.assertEqual('bash', install_args[0])
        self.assertEqual('/tmp/imunify test/i360deploy.sh', install_args[1])
        self.assertEqual(key, install_args[3])
        self.assertEqual(5, len(install_args))

        worker_args = shlex.split(build_install_worker_command('360', key=key))
        self.assertEqual('/usr/local/CyberCP/CLManager/CageFS.py', worker_args[1])
        self.assertEqual(key, worker_args[-1])
        self.assertEqual(6, len(worker_args))

    def test_deploy_runner_rejects_a_failed_install(self):
        commands = build_deploy_commands('av')
        return_codes = [0, 1, 0, 2]
        with tempfile.TemporaryFile(mode='w+') as status_file:
            with mock.patch(
                'plogical.imunify_integration.subprocess.call',
                side_effect=return_codes,
            ) as process_call:
                with self.assertRaisesRegex(RuntimeError, 'installation failed'):
                    with mock.patch(
                        'plogical.imunify_integration.os.path.isfile',
                        return_value=True,
                    ), mock.patch(
                        'plogical.imunify_integration.os.path.getsize',
                        return_value=4096,
                    ):
                        run_deploy_commands(commands, status_file)
                self.assertNotIn('shell', process_call.call_args.kwargs)

    def test_download_uses_retries_and_does_not_uninstall_first(self):
        commands = build_deploy_commands('av')
        download = commands[2]

        self.assertIn('--tries=3', download)
        self.assertIn('--timeout=30', download)
        self.assertFalse(any('--uninstall' in command for command in commands))

    def test_deploy_runner_rejects_an_incomplete_download(self):
        commands = build_deploy_commands('av')
        with tempfile.TemporaryFile(mode='w+') as status_file:
            with mock.patch(
                'plogical.imunify_integration.subprocess.call',
                side_effect=[0, 1, 0],
            ), mock.patch(
                'plogical.imunify_integration.os.path.isfile',
                return_value=True,
            ), mock.patch(
                'plogical.imunify_integration.os.path.getsize',
                return_value=12,
            ):
                with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                    run_deploy_commands(commands, status_file)

    def test_status_file_and_ui_executables_receive_safe_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            status_path = os.path.join(directory, 'status', 'install.log')
            self.assertIsNone(read_install_status(status_path))
            ensure_install_status_file(status_path, owner=None)
            self.assertTrue(os.path.isfile(status_path))
            self.assertEqual(0o644, stat.S_IMODE(os.stat(status_path).st_mode))
            pathlib.Path(status_path).write_text('working\n', encoding='utf-8')
            self.assertEqual('working\n', read_install_status(status_path))
            ensure_install_status_file(status_path, owner=None, reset=True)
            self.assertEqual('', read_install_status(status_path))

            execute_path = os.path.join(directory, 'ui', 'bin', 'execute.py')
            os.makedirs(os.path.dirname(execute_path))
            pathlib.Path(execute_path).write_text('#!/usr/bin/env python3\n', encoding='utf-8')
            os.chmod(execute_path, 0o640)
            chmod_imunify_execute_files(os.path.join(directory, 'ui'))
            self.assertEqual(0o755, stat.S_IMODE(os.stat(execute_path).st_mode))

            script_dir = os.path.join(directory, 'scripts')
            os.makedirs(script_dir)
            for _option, filename in CLSCRIPT_OPTIONS:
                script_path = os.path.join(script_dir, filename)
                pathlib.Path(script_path).write_text('#!/usr/bin/env python3\n', encoding='utf-8')
                os.chmod(script_path, 0o640)
            ensure_clscripts_executable(script_dir)
            self.assertEqual(
                0o751,
                stat.S_IMODE(os.stat(os.path.join(script_dir, 'panel_info.py')).st_mode),
            )


if __name__ == '__main__':
    unittest.main()
