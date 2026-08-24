import ast
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


INSTALLER = Path(__file__).with_name('install.py')
BOOTSTRAP = INSTALLER.parents[1] / 'cyberpanel.sh'


def load_key_helpers():
    tree = ast.parse(INSTALLER.read_text())
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name)
                and target.id == 'LITESPEED_EL10_KEY_SHA256'
                for target in node.targets):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in (
                'is_el10_release', 'verify_litespeed_el10_key'):
            selected.append(node)
    namespace = {'hashlib': hashlib}
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(INSTALLER), 'exec'), namespace)
    return namespace


class LiteSpeedEL10KeyTests(unittest.TestCase):
    def test_el10_detection_is_exact(self):
        helpers = load_key_helpers()
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / 'os-release'
            release.write_text('ID="almalinux"\nVERSION_ID="10.2"\n')
            self.assertTrue(helpers['is_el10_release'](release))
            release.write_text('ID="almalinux"\nVERSION_ID="9.7"\n')
            self.assertFalse(helpers['is_el10_release'](release))

    def test_key_verification_is_pinned(self):
        helpers = load_key_helpers()
        with tempfile.NamedTemporaryFile() as key_file:
            key_file.write(b'wrong key')
            key_file.flush()
            self.assertFalse(helpers['verify_litespeed_el10_key'](key_file.name))

    def test_bootstrap_uses_pinned_el10_repositories(self):
        source = BOOTSTRAP.read_text()

        self.assertIn('RPM-GPG-KEY-litespeed2025', source)
        self.assertIn(
            'cd0578a8febe98cb7d7d437a73419b8407ddd98cd848f2c9c7fdd288d768af01',
            source,
        )
        self.assertIn('epel-release-latest-10.noarch.rpm', source)
        self.assertIn('remi-release-10.rpm', source)
        self.assertIn('10.11/rhel10-amd64/', source)

    def test_existing_el9_repository_targets_are_retained(self):
        source = BOOTSTRAP.read_text()

        self.assertIn('epel-release-latest-9.noarch.rpm', source)
        self.assertIn('remi-release-9.rpm', source)
        self.assertIn('10.11/rhel9-amd64/', source)

    def test_el10_mail_uses_native_packages(self):
        tree = ast.parse(INSTALLER.read_text())
        installer_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'preFlightsChecks'
        )
        method = next(
            node for node in installer_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == 'install_postfix_dovecot'
        )
        source = ast.get_source_segment(INSTALLER.read_text(), method)

        self.assertIn('if is_el10_release()', source)
        self.assertIn('dnf install -y postfix postfix-mysql cyrus-sasl-plain', source)
        self.assertIn('gf-release-latest.gf.el9.noarch.rpm', source)

    def test_progress_logging_reuses_detected_server_ip(self):
        source = BOOTSTRAP.read_text()
        function_start = source.index('Debug_Log2()')
        function_end = source.index('\n}\n', function_start) + 3
        function = source[function_start:function_end].replace(
            '/var/log/installLogs.txt', '"$INSTALL_LOG"'
        )

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            call_log = directory / 'ip-checks'
            harness = (
                'Check_Server_IP() { printf called >> "$CALL_LOG"; }\n'
                'curl() { :; }\n'
                f'{function}\n'
                'Debug_Log2 "Installing components,10"\n'
            )
            environment = os.environ.copy()
            environment.update({
                'CALL_LOG': str(call_log),
                'INSTALL_LOG': str(directory / 'install.log'),
                'Server_IP': '192.0.2.10',
            })
            subprocess.run(
                ['bash', '-c', harness], check=True, env=environment
            )

            self.assertFalse(call_log.exists())


if __name__ == '__main__':
    unittest.main()
