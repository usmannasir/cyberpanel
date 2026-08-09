import pathlib
import subprocess
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

    def test_upgrade_updates_database_version_record(self):
        root = pathlib.Path(__file__).parents[1]
        upgrader = (root / 'plogical/upgrade.py').read_text(encoding='utf-8')
        self.assertIn('\n        Upgrade.upgradeVersion()\n', upgrader)
        self.assertNotIn('# Upgrade.upgradeVersion()', upgrader)

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
