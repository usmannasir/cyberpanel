import ast
import re
import shutil
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch
from lscpd_binary import host_glibc_version, select_lscpd_binary

ROOT = Path(__file__).resolve().parent


class LscpdSelectionTests(unittest.TestCase):
    def test_modern_rhel_and_debian_abis_select_nontruncating_server(self):
        for version in ((2, 25), (2, 28), (2, 34), (2, 39), (2, 10)):
            with self.subTest(version=version):
                expected = 'lscpd.0.4.0' if version >= (2, 25) else 'lscpd-0.3.1'
                self.assertEqual(select_lscpd_binary('x86_64', version), expected)

    def test_centos7_legacy_abi_remains_bootable(self):
        self.assertEqual(select_lscpd_binary('x86_64', (2, 17)), 'lscpd-0.3.1')

    def test_arm_uses_arm_binary_without_glibc_probe(self):
        with patch('lscpd_binary.host_glibc_version', side_effect=AssertionError):
            self.assertEqual(select_lscpd_binary('aarch64'), 'lscpd.aarch64')

    def test_unknown_architecture_is_rejected(self):
        with self.assertRaises(RuntimeError):
            select_lscpd_binary('ppc64le', (2, 39))

    def test_libc_probe_prefers_runtime_over_distribution(self):
        with patch('lscpd_binary.os.confstr', return_value='glibc 2.28'):
            self.assertEqual(host_glibc_version(), (2, 28))

    def test_libc_probe_falls_back_and_fails_conservatively(self):
        with patch('lscpd_binary.os.confstr', side_effect=ValueError), patch('lscpd_binary.platform.libc_ver', return_value=('glibc', '2.17')):
            self.assertEqual(host_glibc_version(), (2, 17))
        with patch('lscpd_binary.os.confstr', return_value=''), patch('lscpd_binary.platform.libc_ver', return_value=('', '')):
            self.assertIsNone(host_glibc_version())
            self.assertEqual(select_lscpd_binary('x86_64'), 'lscpd-0.3.1')

    @unittest.skipUnless(shutil.which('readelf'), 'readelf is required for bundled ELF ABI verification')
    def test_glibc_selection_floor_matches_the_bundled_binaries(self):
        for filename, floor in (('lscpd.0.4.0', (2, 25)), ('lscpd-0.3.1', (2, 17))):
            output = subprocess.check_output(['readelf', '--version-info', str(ROOT / filename)], text=True)
            requirements = [tuple(map(int, value.split('.'))) for value in re.findall(r'Name: GLIBC_(\d+\.\d+(?:\.\d+)?)', output)]
            self.assertTrue(requirements)
            self.assertLessEqual(max(requirements), floor, filename)

    def test_install_and_upgrade_share_the_selector(self):
        for relative in ('install/install.py', 'plogical/upgrade.py'):
            tree = ast.parse((ROOT / relative).read_text())
            imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == 'lscpd_binary']
            self.assertTrue(any(a.name == 'select_lscpd_binary' for n in imports for a in n.names), relative)
            selections = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'lscpdSelection' for t in n.targets)]
            self.assertEqual(len(selections), 1, relative)
            self.assertIsInstance(selections[0].value, ast.Call)
            self.assertEqual(selections[0].value.func.id, 'select_lscpd_binary')


if __name__ == '__main__':
    unittest.main()
