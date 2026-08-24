import ast
import hashlib
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


if __name__ == '__main__':
    unittest.main()
