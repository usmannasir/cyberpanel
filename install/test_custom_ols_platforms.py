import ast
import builtins
import os
import re
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_method(path, class_name, method_name):
    tree = ast.parse(path.read_text())
    class_node = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method_node = next(
        node for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    )
    minimal_class = ast.ClassDef(
        name=class_name,
        bases=[],
        keywords=[],
        body=[
            ast.FunctionDef(
                name='stdOut',
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg='message'), ast.arg(arg='level')],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[ast.Pass()],
                decorator_list=[ast.Name(id='staticmethod', ctx=ast.Load())],
            ),
            method_node,
        ],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[minimal_class], type_ignores=[]))
    namespace = {
        'logging': mock.Mock(),
        'os': os,
        're': re,
        'staticmethod': staticmethod,
    }
    exec(compile(module, str(path), 'exec'), namespace)
    return getattr(namespace[class_name], method_name)


def binary_configs(path, class_name):
    tree = ast.parse(path.read_text())
    class_node = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method_node = next(
        node for node in class_node.body
        if isinstance(node, ast.FunctionDef)
        and node.name == 'installCustomOLSBinaries'
    )
    assignment = next(
        node for node in ast.walk(method_node)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'BINARY_CONFIGS'
                for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def method_source(path, class_name, method_name):
    tree = ast.parse(path.read_text())
    class_node = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method_node = next(
        node for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )
    return ast.get_source_segment(path.read_text(), method_node)


class CustomOLSPlatformTests(unittest.TestCase):
    install_path = ROOT / 'install' / 'installCyberPanel.py'
    upgrade_path = ROOT / 'plogical' / 'upgrade.py'

    def test_almalinux_10_uses_dedicated_artifacts(self):
        os_release = 'NAME="AlmaLinux"\nVERSION="10.1"\nVERSION_ID="10.1"\n'
        cases = (
            (self.install_path, 'InstallCyberPanel', False),
            (self.upgrade_path, 'Upgrade', True),
        )

        for path, class_name, is_static in cases:
            with self.subTest(path=path.name):
                detect = load_method(path, class_name, 'detectPlatform')
                exists = lambda candidate: candidate == '/etc/os-release'
                with mock.patch.object(os.path, 'exists', side_effect=exists), \
                     mock.patch.object(builtins, 'open', mock.mock_open(read_data=os_release)):
                    target = None if is_static else type('Target', (), {})()
                    self.assertEqual(detect() if is_static else detect(target), 'rhel10')

    def test_almalinux_10_release_set_is_abi_matched(self):
        for path, class_name in (
            (self.install_path, 'InstallCyberPanel'),
            (self.upgrade_path, 'Upgrade'),
        ):
            with self.subTest(path=path.name):
                config = binary_configs(path, class_name)['rhel10']
                self.assertTrue(config['url'].endswith('openlitespeed-2.5.2-x86_64-rhel10'))
                self.assertTrue(config['module_url'].endswith('cyberpanel_ols-2.7.6-x86_64-rhel10.so'))
                self.assertTrue(config['modsec_url'].endswith('mod_security-2.5.2-x86_64-rhel10.so'))
                self.assertEqual(set(config['sha256']), {'binary', 'module', 'modsec'})
                for checksum in config['sha256'].values():
                    self.assertRegex(checksum, r'^[0-9a-f]{64}$')

    def test_existing_platform_artifact_urls_do_not_change(self):
        expected = {
            self.install_path: {
                'rhel8': ('2.5.0', '2.7.3'),
                'rhel9': ('2.5.0', '2.7.3'),
                'ubuntu': ('2.5.0', '2.7.3'),
            },
            self.upgrade_path: {
                'rhel8': ('2.5.1', '2.7.5'),
                'rhel9': ('2.5.1', '2.7.5'),
                'ubuntu': ('2.5.1', '2.7.5'),
            },
        }

        for path, class_name in (
            (self.install_path, 'InstallCyberPanel'),
            (self.upgrade_path, 'Upgrade'),
        ):
            configs = binary_configs(path, class_name)
            for platform, (core_version, module_version) in expected[path].items():
                with self.subTest(path=path.name, platform=platform):
                    self.assertIn(
                        f'openlitespeed-{core_version}-x86_64-{platform}',
                        configs[platform]['url'],
                    )
                    self.assertIn(
                        f'cyberpanel_ols-{module_version}-x86_64-{platform}.so',
                        configs[platform]['module_url'],
                    )

    def test_almalinux_10_installs_udns_before_abi_preflight(self):
        cases = (
            (
                self.install_path,
                'InstallCyberPanel',
                "self.install_package('udns')",
            ),
            (
                self.upgrade_path,
                'Upgrade',
                "subprocess.call(['dnf', 'install', '-y', 'udns'])",
            ),
        )

        for path, class_name, dependency_install in cases:
            with self.subTest(path=path.name):
                source = method_source(
                    path, class_name, 'installCustomOLSBinaries'
                )
                self.assertIn("if platform == 'rhel10':", source)
                self.assertIn(dependency_install, source)
                self.assertLess(
                    source.index(dependency_install),
                    source.index('checkGlibcCompat'),
                )


if __name__ == '__main__':
    unittest.main()
