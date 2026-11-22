import ast
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


INSTALLER = Path(__file__).with_name('install.py')
BOOTSTRAP = INSTALLER.parents[1] / 'cyberpanel.sh'


def method_source(text, cls, method):
    """The lines of a method of a class, up to the next statement of the class.

    ast.get_source_segment gives them from Python 3.8 on; the interpreter of
    the panel on AlmaLinux 8, which also runs these tests, is 3.6.
    """
    lines = text.splitlines(True)
    later = [node.lineno for node in cls.body if node.lineno > method.lineno]
    return ''.join(lines[method.lineno - 1:min(later) - 1 if later else len(lines)])


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
        source = method_source(INSTALLER.read_text(), installer_class, method)

        self.assertIn('if is_el10_release()', source)
        self.assertIn('dnf install -y postfix postfix-mysql cyrus-sasl-plain', source)
        self.assertIn('gf-release-latest.gf.el9.noarch.rpm', source)

    def test_el10_skips_removed_mariadb_module_commands(self):
        tree = ast.parse(
            (INSTALLER.with_name('installCyberPanel.py')).read_text()
        )
        installer_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'InstallCyberPanel'
        )
        method = next(
            node for node in installer_class.body
            if isinstance(node, ast.FunctionDef) and node.name == 'installMySQL'
        )
        source = method_source(
            INSTALLER.with_name('installCyberPanel.py').read_text(), installer_class, method
        )

        self.assertIn("if self.detectPlatform() != 'rhel10':", source)
        self.assertIn('dnf -qy module disable mariadb', source)
        self.assertIn('dnf module reset mariadb -y', source)

    def test_el10_keeps_the_verified_modsecurity_module(self):
        tree = ast.parse(INSTALLER.read_text())
        installer_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'preFlightsChecks'
        )
        method = next(
            node for node in installer_class.body
            if isinstance(node, ast.FunctionDef) and node.name == 'modSecPreReqs'
        )
        namespace = {'is_el10_release': lambda: True, 'os': os}
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        exec(compile(module, str(INSTALLER), 'exec'), namespace)
        self.assertEqual(namespace['modSecPreReqs'](None), 1)

    def test_el10_opendkim_maps_are_readable_by_the_service(self):
        tree = ast.parse(INSTALLER.read_text())
        installer_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'preFlightsChecks'
        )
        method = next(
            node for node in installer_class.body
            if isinstance(node, ast.FunctionDef) and node.name == 'installOpenDKIM'
        )
        source = method_source(INSTALLER.read_text(), installer_class, method)

        self.assertIn('if is_el10_release():', source)
        self.assertIn("shutil.chown(table_path, user='root', group='opendkim')", source)
        self.assertIn('os.chmod(table_path, 0o640)', source)
        self.assertIn(
            "shutil.chown(keys_path, user='root', group='opendkim')", source
        )

    def test_progress_logging_reuses_detected_server_ip(self):
        source = BOOTSTRAP.read_text()
        function_start = source.index('Debug_Log2()')
        function_end = source.index('\n}\n', function_start) + 3
        function = source[function_start:function_end].replace(
            '/var/log/installLogs.txt', '"$INSTALL_LOG"'
        )

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            call_log = directory / 'requests'
            # Debug_Log2 asks for the address with curl when it does not know
            # it, and posts the progress line with curl. Both are recorded
            # here instead of being sent; nothing leaves this machine.
            harness = (
                'curl() {\n'
                '  printf "%s\\n" "$*" >> "$CALL_LOG"\n'
                '  case "$*" in *cyberpanel.sh/?ip*) printf "%s" "$LOOKUP_ANSWER" ;; esac\n'
                '}\n'
                f'{function}\n'
                'Debug_Log2 "Installing components,10"\n'
                'Debug_Log2 "Installing more components,20"\n'
            )
            environment = {
                'PATH': os.environ['PATH'],
                'CALL_LOG': str(call_log),
                'INSTALL_LOG': str(directory / 'install.log'),
                'LOOKUP_ANSWER': '192.0.2.20',
            }

            def requests(**variables):
                if call_log.exists():
                    call_log.unlink()
                subprocess.run(
                    ['bash', '-c', harness], check=True, env=dict(environment, **variables)
                )
                lines = call_log.read_text().splitlines()
                lookups = [line for line in lines if 'cyberpanel.sh/?ip' in line]
                posts = [line for line in lines if 'servers/RecvData' in line]
                self.assertEqual(len(lines), len(lookups) + len(posts))
                return lookups, posts

            # The address is known: it is used, and not asked for again.
            lookups, posts = requests(Server_IP='192.0.2.10')
            self.assertEqual([], lookups)
            self.assertEqual(2, len(posts))
            self.assertTrue(all('"ipAddress": "192.0.2.10"' in post for post in posts))

            # The address is not known: asked for once, then reused.
            lookups, posts = requests()
            self.assertEqual(1, len(lookups))
            self.assertEqual(2, len(posts))
            self.assertTrue(all('"ipAddress": "192.0.2.20"' in post for post in posts))

            # No usable answer: nothing is taken for an address, and the next
            # progress line asks again.
            lookups, posts = requests(LOOKUP_ANSWER='<html>busy</html>')
            self.assertEqual(2, len(lookups))
            self.assertTrue(all('"ipAddress": ""' in post for post in posts))


if __name__ == '__main__':
    unittest.main()
