import pathlib
import shutil
import subprocess
import tempfile
import unittest

from install import install_utils


class DeveloperInstallerPythonTests(unittest.TestCase):

    def test_version_parsers_do_not_depend_on_fixed_json_offsets(self):
        root = pathlib.Path(__file__).parents[1]
        for script_path in (root / 'cyberpanel.sh', root / 'cyberpanel_upgrade.sh'):
            script = script_path.read_text(encoding='utf-8')
            self.assertNotIn('${Temp_Value:12:3}', script)
            self.assertNotIn('${Temp_Value:25:1}', script)
            self.assertIn('parse_panel_version', script)

            function_start = script.index('parse_panel_version()')
            function_end = script.index('\n}\n', function_start) + 3
            parser = script[function_start:function_end]
            command = parser + '\nparse_panel_version "$VERSION_DATA" && ' \
                'printf \'%s.%s\' "$Panel_Version" "$Panel_Build"'
            result = subprocess.run(
                ['bash', '-c', command],
                check=True,
                capture_output=True,
                text=True,
                env={
                    'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                    'VERSION_DATA': '{"version": "3.0", "build": 12}',
                },
            )
            self.assertEqual('3.0.12', result.stdout)

    def test_installer_writes_machine_readable_version_file(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'install/install.py').read_text(encoding='utf-8')
        self.assertIn("json.dump({'version': VERSION, 'build': BUILD}", installer)

    def test_installer_keeps_its_module_ahead_of_the_package(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'install/install.py').read_text(encoding='utf-8')
        source_root = (
            'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))'
        )
        self.assertIn(f'sys.path.insert(1, {source_root})', installer)
        self.assertNotIn(f'sys.path.insert(0, {source_root})', installer)

    def test_upgrade_updates_database_version_record(self):
        root = pathlib.Path(__file__).parents[1]
        upgrader = (root / 'plogical/upgrade.py').read_text(encoding='utf-8')
        self.assertIn('\n        Upgrade.upgradeVersion()\n', upgrader)
        self.assertNotIn('# Upgrade.upgradeVersion()', upgrader)

    def test_upgrade_stages_runtime_version_module_with_upgrader(self):
        root = pathlib.Path(__file__).parents[1]
        upgrade_script = (root / 'cyberpanel_upgrade.sh').read_text(
            encoding='utf-8'
        )
        self.assertIn(
            'Download_Upgrade_Source "plogical/upgrade.py" "upgrade.py"',
            upgrade_script,
        )
        self.assertIn(
            'Download_Upgrade_Source "cyberpanel_version.py" '
            '"cyberpanel_version.py"',
            upgrade_script,
        )

        with tempfile.TemporaryDirectory() as stage_dir:
            stage = pathlib.Path(stage_dir)
            shutil.copy2(root / 'plogical/upgrade.py', stage / 'upgrade.py')
            shutil.copy2(
                root / 'cyberpanel_version.py',
                stage / 'cyberpanel_version.py',
            )
            result = subprocess.run(
                [
                    'python3',
                    '-c',
                    'from cyberpanel_version import BUILD, VERSION; '
                    'print(f"{VERSION}.{BUILD}")',
                ],
                cwd=stage,
                check=True,
                capture_output=True,
                text=True,
            )
            version = (root / 'cyberpanel_version.py').read_text(
                encoding='utf-8'
            )
            namespace = {}
            exec(compile(version, 'cyberpanel_version.py', 'exec'), namespace)
            self.assertEqual(namespace['FULL_VERSION'], result.stdout.strip())

    def test_remote_mysql_password_is_not_passed_on_the_command_line(self):
        root = pathlib.Path(__file__).parents[1]
        shell_installer = (root / 'cyberpanel.sh').read_text(encoding='utf-8')
        python_installer = (root / 'install/install.py').read_text(
            encoding='utf-8'
        )

        self.assertNotIn(
            'Final_Flags+=(--mysqlpassword "$MySQL_Password")',
            shell_installer,
        )
        self.assertIn(
            'CP_INSTALL_MYSQL_PASSWORD="$MySQL_Password"', shell_installer
        )
        self.assertIn('os.environ.pop(', python_installer)
        self.assertIn("'CP_INSTALL_MYSQL_PASSWORD', None", python_installer)

    def test_remote_mysql_answers_are_validated_before_package_setup(self):
        root = pathlib.Path(__file__).parents[1]
        shell_installer = (root / 'cyberpanel.sh').read_text(encoding='utf-8')

        function_start = shell_installer.index('Validate_Remote_MySQL()')
        function_end = shell_installer.index('\n}\n', function_start) + 3
        validator = shell_installer[function_start:function_end]
        harness = (
            'log_error() { :; }\n' + validator + '\n'
            'Validate_Remote_MySQL'
        )
        base_env = {
            'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            'Remote_MySQL': 'On',
            'MySQL_Host': 'db.example.com',
            'MySQL_DB': 'mysql',
            'MySQL_User': 'cpadmin',
            'MySQL_Password': 'secret',
            'MySQL_Port': '3307',
        }

        valid = subprocess.run(['bash', '-c', harness], env=base_env)
        self.assertEqual(0, valid.returncode)
        for field, value in (
            ('MySQL_Host', ''),
            ('MySQL_DB', ''),
            ('MySQL_User', ''),
            ('MySQL_Password', ''),
            ('MySQL_Port', '70000'),
            ('MySQL_Port', 'not-a-port'),
        ):
            invalid = subprocess.run(
                ['bash', '-c', harness], env=dict(base_env, **{field: value}),
                capture_output=True, text=True,
            )
            self.assertNotEqual(0, invalid.returncode, field)
            self.assertNotIn('secret', invalid.stdout + invalid.stderr)

        validation_call = shell_installer.rindex(
            '\nValidate_Remote_MySQL || exit 1\n'
        )
        package_setup = shell_installer.rindex('\nPre_Install_Setup_Repository\n')
        self.assertLess(validation_call, package_setup)

    def test_settings_fallback_uses_python_literals_for_database_values(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'install/install.py').read_text(encoding='utf-8')

        self.assertNotIn("+ cyberpanel_db_password +", installer)
        self.assertNotIn("+ mysql_root_password +", installer)
        self.assertIn("        'PASSWORD': %r,\\n", installer)
        self.assertIn("        'HOST': %r,\\n", installer)

    def test_upgrade_failure_banner_does_not_claim_the_old_build_is_running(self):
        root = pathlib.Path(__file__).parents[1]
        upgrade_script = (root / 'cyberpanel_upgrade.sh').read_text(
            encoding='utf-8'
        )

        self.assertIn('UPGRADE_FAILED', upgrade_script)
        self.assertIn('may be partially updated', upgrade_script)
        self.assertNotIn('STILL RUNNING THE OLD BUILD', upgrade_script)

    def test_upgrade_virtualenv_uses_matching_branch_requirements(self):
        root = pathlib.Path(__file__).parents[1]
        upgrade_script = (root / 'cyberpanel_upgrade.sh').read_text(
            encoding='utf-8'
        )

        self.assertIn('Validate_Python_Requirements()', upgrade_script)
        self.assertIn(
            'Validate_Python_Requirements /usr/local/CyberPanel/bin/python '
            '/usr/local/requirments.txt',
            upgrade_script,
        )
        self.assertIn(
            'Validate_Python_Requirements /usr/local/CyberPanelTemp/bin/python '
            '/usr/local/requirments.txt',
            upgrade_script,
        )
        fallback_start = upgrade_script.index(
            'Creating temporary virtual environment for fallback upgrade'
        )
        fallback_end = upgrade_script.index(
            'Starting post-upgrade cleanup', fallback_start
        )
        fallback = upgrade_script[fallback_start:fallback_end]
        self.assertNotIn('requirments-old.txt', fallback)
        self.assertNotIn('--system-site-packages', fallback)
        self.assertNotIn('$PIP3 install', fallback)

    def test_upgrade_stops_when_source_preparation_fails(self):
        root = pathlib.Path(__file__).parents[1]
        upgrader = (root / 'plogical/upgrade.py').read_text(encoding='utf-8')

        self.assertIn(
            'download_status, download_error = Upgrade.downloadAndUpgrade(',
            upgrader,
        )
        self.assertIn('if download_status != 1:', upgrader)
        self.assertIn('if Upgrade.waitForDatabaseReady() != 1:', upgrader)

    def test_ubuntu_24_lscpd_keeps_virtualenv_packages_visible(self):
        root = pathlib.Path(__file__).parents[1]
        script = (root / 'cyberpanel_upgrade.sh').read_text(encoding='utf-8')
        function_start = script.index('Configure_LSCPD_Python_Environment()')
        function_end = script.index('\n}\n', function_start) + 3
        function = script[function_start:function_end]

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = pathlib.Path(temporary_directory)
            runtime_root = temporary_root / 'CyberCP'
            runtime_site = runtime_root / 'lib/python3.12/site-packages'
            runtime_site.mkdir(parents=True)
            runtime_python = runtime_root / 'bin/python'
            runtime_python.parent.mkdir()
            runtime_python.write_text(
                '#!/bin/sh\nprintf \'%s\\n\' "$RUNTIME_SITE"\n',
                encoding='utf-8',
            )
            runtime_python.chmod(0o755)
            environment_file = temporary_root / 'pythonenv.conf'
            environment = {
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                'Server_OS': 'Ubuntu',
                'Server_OS_Version': '24',
                'LSCPD_PYTHON_ENV_FILE': str(environment_file),
                'CYBERCP_RUNTIME_ROOT': str(runtime_root),
                'RUNTIME_SITE': str(runtime_site),
            }

            subprocess.run(
                ['bash', '-c', function + '\nConfigure_LSCPD_Python_Environment'],
                check=True,
                env=environment,
            )
            self.assertEqual(
                'PYTHONHOME=/usr\n'
                f'PYTHONPATH=.:{runtime_root}:{runtime_site}\n',
                environment_file.read_text(encoding='utf-8'),
            )

            environment['Server_OS'] = 'CentOS'
            environment['Server_OS_Version'] = '9'
            subprocess.run(
                ['bash', '-c', function + '\nConfigure_LSCPD_Python_Environment'],
                check=True,
                env=environment,
            )
            self.assertEqual(
                'PYTHONHOME=/usr\n',
                environment_file.read_text(encoding='utf-8'),
            )

    def test_repair_script_does_not_download_old_release_requirements(self):
        root = pathlib.Path(__file__).parents[1]
        repair_script = (root / 'fix_cyberpanel_install.sh').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('/v2.4.5/requirments', repair_script)
        self.assertIn('/usr/local/CyberCP/$requirements_name', repair_script)

    def test_terminal_secret_is_private_and_readable_by_panel_worker(self):
        root = pathlib.Path(__file__).parents[1]
        for script_path in (root / 'install/install.py', root / 'plogical/upgrade.py'):
            script = script_path.read_text(encoding='utf-8')
            self.assertIn(
                "shutil.chown(secret_path, user='cyberpanel', group='cyberpanel')",
                script,
            )
            self.assertIn('os.chmod(secret_path, 0o600)', script)

    def test_ubuntu_dependencies_require_installable_pcre_candidate(self):
        root = pathlib.Path(__file__).parents[1]
        for script_path in (root / 'cyberpanel.sh', root / 'install/venvsetup.sh'):
            script = script_path.read_text(encoding='utf-8')
            self.assertIn(
                "apt-cache policy libpcre3-dev 2>/dev/null | grep -q 'Candidate: [^(]'",
                script,
            )
            self.assertNotIn(
                'apt-cache show libpcre3-dev >/dev/null 2>&1',
                script,
            )
            self.assertIn('libsasl2-dev', script)

    def test_memcached_falls_back_when_pcre_one_is_unavailable(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'cyberpanel.sh').read_text(encoding='utf-8')
        legacy_installer = (root / 'install/venvsetup.sh').read_text(
            encoding='utf-8'
        )
        self.assertIn('lsmcd_supported="false"', installer)
        self.assertIn(
            '[[ $Total_RAM -ge 2048 && "$lsmcd_supported" = "true" ]]',
            installer,
        )
        self.assertIn(
            "&& apt-cache policy libpcre3-dev 2>/dev/null | grep -q 'Candidate: [^(]'",
            legacy_installer,
        )

    def test_dns_handoff_waits_for_name_resolution(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'cyberpanel.sh').read_text(encoding='utf-8')
        self.assertIn('chmod 0644 /etc/resolv.conf', installer)
        self.assertIn('DNS_Ready="No"', installer)
        self.assertIn('getent ahostsv4 cyberpanel.sh', installer)
        self.assertIn('if [[ "$DNS_Ready" = "Yes" ]]', installer)
        self.assertNotIn(
            'ping -c 1 -W 1 8.8.8.8 >/dev/null 2>&1 || nslookup',
            installer,
        )

    def test_developer_install_uses_system_python_three(self):
        script = pathlib.Path(__file__).with_name('venvsetup.sh').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('python3.6', script)
        self.assertNotIn('pip3.6', script)
        self.assertIn(
            'python3 -m venv --system-site-packages CyberPanel',
            script,
        )
        self.assertIn(
            'python3 -m venv --system-site-packages /usr/local/CyberCP',
            script,
        )
        self.assertGreaterEqual(
            script.count('python -m pip install --ignore-installed'),
            2,
        )

    def test_ubuntu_26_is_recognized_by_remaining_installer_scripts(self):
        root = pathlib.Path(__file__).parents[1]
        for relative_path in (
            'CPScripts/mailscannerinstaller.sh',
            'CPScripts/mailscanneruninstaller.sh',
        ):
            script = (root / relative_path).read_text(encoding='utf-8')
            detection_line = next(
                line for line in script.splitlines()
                if 'Server_OS="Ubuntu"' in line
            )
            detection_index = script.splitlines().index(detection_line)
            version_check = script.splitlines()[detection_index - 1]
            for release in ('18.04', '20.04', '20.10', '22.04', '24.04', '26.04'):
                self.assertIn('Ubuntu %s' % release, version_check)

        developer_installer = (root / 'install/venvsetup.sh').read_text(
            encoding='utf-8'
        )
        self.assertIn(
            'Ubuntu (18.04|20.04|22.04|24.04|26.04)',
            developer_installer,
        )

    def test_panel_credentials_keep_worker_only_permissions(self):
        root = pathlib.Path(__file__).parents[1]
        generator = (root / 'install/env_generator.py').read_text(
            encoding='utf-8'
        )
        installer = (root / 'install/install.py').read_text(encoding='utf-8')
        upgrader = (root / 'plogical/upgrade.py').read_text(encoding='utf-8')

        self.assertIn('os.chmod(env_file_path, 0o640)', generator)
        self.assertIn("group='cyberpanel'", generator)
        for script in (installer, upgrader):
            self.assertIn("'/usr/local/CyberCP/.env'", script)
            self.assertIn("'/usr/local/CyberCP/secret_key'", script)
            self.assertIn('chown root:cyberpanel %s', script)
            self.assertIn("backup_env = '/usr/local/CyberCP/.env.backup'", script)
            self.assertIn('chmod 600 %s', script)

    def test_php_symlink_fallback_uses_executable_commands(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'install/install.py').read_text(encoding='utf-8')
        upgrader = (root / 'plogical/upgrade.py').read_text(encoding='utf-8')
        self.assertEqual(
            installer.count(
                "'env DEBIAN_FRONTEND=noninteractive apt-get -y install "
                "lsphp"
            ),
            4,
        )
        self.assertIn(
            "'env DEBIAN_FRONTEND=noninteractive apt-get update'",
            upgrader,
        )
        self.assertIn(
            "'env DEBIAN_FRONTEND=noninteractive apt-get -y install "
            "lsphp83 lsphp83-*'",
            upgrader,
        )
        for script in (installer, upgrader):
            self.assertNotIn(
                "'DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp",
                script,
            )

    def test_ubuntu_26_install_does_not_restart_logind(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / 'install/install.py').read_text(encoding='utf-8')
        self.assertIn(
            "if self.distro != ubuntu or get_Ubuntu_release() < 26.04:",
            installer,
        )
        self.assertIn(
            "self.manage_service('systemd-logind', 'restart')",
            installer,
        )
        self.assertIn(
            'Ubuntu 26.04: keeping systemd-logind running during installation.',
            installer,
        )

    def test_ubuntu_package_commands_wait_for_dpkg_lock(self):
        install_command, install_shell = install_utils.get_package_install_command(
            install_utils.ubuntu,
            'gcc',
        )
        remove_command, remove_shell = install_utils.get_package_remove_command(
            install_utils.ubuntu,
            'ufw',
        )
        self.assertIn('-o DPkg::Lock::Timeout=300', install_command)
        self.assertIn('-o DPkg::Lock::Timeout=300', remove_command)
        self.assertTrue(install_shell)
        self.assertTrue(remove_shell)

    def test_non_ubuntu_package_commands_are_unchanged(self):
        centos_command, centos_shell = install_utils.get_package_install_command(
            install_utils.centos,
            'gcc',
        )
        openeuler_command, openeuler_shell = (
            install_utils.get_package_install_command(
                install_utils.openeuler,
                'gcc',
            )
        )
        self.assertEqual('yum install -y gcc ', centos_command)
        self.assertEqual('dnf install -y gcc ', openeuler_command)
        self.assertFalse(centos_shell)
        self.assertFalse(openeuler_shell)


if __name__ == '__main__':
    unittest.main()
