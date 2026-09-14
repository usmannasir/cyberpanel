"""Initial quota application preserves a configured site on partial failure."""
import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import types
import unittest
from unittest.mock import Mock, patch

from plogical import filesystemQuota


ROOT = Path(__file__).resolve().parents[1]


def method(path, name):
    return next(node for node in ast.walk(ast.parse(path.read_text()))
                if isinstance(node, ast.FunctionDef) and node.name == name)


class InitialWebsiteQuotaTests(unittest.TestCase):
    def setUp(self):
        self.package = NS(pk=3, diskSpace=50, inodeLimit=70000, enforceDiskLimits=1)
        self.site = NS(pk=7, domain='owned.example', externalApp='owned', package_id=3)
        self.logger = NS(writeToFile=Mock(), statusWriter=Mock())
        self.cleanup = Mock()
        self.process = Mock()
        self.lookup = Mock(return_value=self.site)
        self.prepare = Mock(return_value={'sites': [7], 'disk_space': 50, 'inode_limit': 70000})
        self.apply = Mock(return_value={'ok': True, 'applied': ['owned.example']})
        self.resource = NS(set_user_limits=Mock(return_value=True), set_inode_limit=Mock())
        resource_module = types.ModuleType('plogical.resourceLimits')
        resource_module.resource_manager = self.resource
        for item in (patch.dict(sys.modules, {'plogical.resourceLimits': resource_module}),
                     patch.object(filesystemQuota, 'prepare_package_quota', self.prepare),
                     patch.object(filesystemQuota, 'apply_quota_plan', self.apply)):
            item.start()
            self.addCleanup(item.stop)
        # Run the actual creation tail and its unchanged outer rollback handler,
        # without unrelated website, DNS, SSL or service provisioning.
        node = copy.deepcopy(method(ROOT / 'plogical/virtualHostUtilities.py', 'createVirtualHost'))
        outer = node.body[0]
        start = next(i for i, statement in enumerate(outer.body)
                     if isinstance(statement, ast.If)
                     and isinstance(statement.test, ast.Attribute)
                     and statement.test.attr == 'enforceDiskLimits')
        outer.body = outer.body[start:]
        node.decorator_list = []
        namespace = {'selectedPackage': self.package, 'Websites': NS(objects=NS(get=self.lookup)),
                     'ProcessUtilities': self.process, 'logging': NS(CyberCPLogFileWriter=self.logger),
                     'ACLManager': NS(FindIfChild=Mock(return_value=0)),
                     'vhost': NS(deleteVirtualHostConfigurations=self.cleanup)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'virtualHostUtilities.py', 'exec'), namespace)
        self.create = namespace['createVirtualHost']

    def run_creation_tail(self, **kwargs):
        return self.create('owned.example', 'admin@example.invalid', 'PHP 8.3', 'owned',
                           0, 0, 0, 'admin', 'quota-package', 0, tempStatusPath='/tmp/owned-status', **kwargs)

    def test_success_uses_one_checked_pair_on_exact_persisted_website(self):
        calls = Mock()
        calls.attach_mock(self.prepare, 'prepare')
        calls.attach_mock(self.apply, 'apply')
        self.assertEqual((1, 'None'), self.run_creation_tail())
        self.lookup.assert_called_once_with(domain='owned.example')
        self.prepare.assert_called_once_with(self.package, [self.site])
        self.apply.assert_called_once_with(self.prepare.return_value)
        self.assertEqual(['prepare', 'apply'], [call[0] for call in calls.mock_calls])
        self.process.executioner.assert_not_called()
        self.resource.set_inode_limit.assert_not_called()
        self.cleanup.assert_not_called()
        self.assertIn('[200]', self.logger.statusWriter.call_args.args[1])

    def test_zero_limits_are_preserved_as_explicit_policy_values(self):
        self.package.diskSpace = self.package.inodeLimit = 0
        self.assertEqual(1, self.run_creation_tail()[0])
        self.prepare.assert_called_once_with(self.package, [self.site])
        self.assertEqual(0, self.prepare.call_args.args[0].diskSpace)
        self.assertEqual(0, self.prepare.call_args.args[0].inodeLimit)

    def test_disabled_package_does_not_touch_quota_or_resource_helpers(self):
        self.package.enforceDiskLimits = 0
        self.assertEqual(1, self.run_creation_tail()[0])
        self.lookup.assert_not_called()
        self.prepare.assert_not_called()
        self.apply.assert_not_called()
        self.resource.set_user_limits.assert_not_called()

    def test_preflight_and_apply_failure_preserve_site_and_report_partial_outcome(self):
        for target in (self.prepare, self.apply):
            with self.subTest(stage='prepare' if target is self.prepare else 'apply'):
                target.side_effect = filesystemQuota.QuotaError('private diagnostic')
                code, message = self.run_creation_tail()
                self.assertEqual(0, code)
                self.assertIn('Website was created', message)
                self.assertIn('quota could not be verified', message)
                self.assertNotIn('private diagnostic', message)
                self.cleanup.assert_not_called()
                self.assertIn('[404]', self.logger.statusWriter.call_args.args[1])
                self.assertNotIn('[200]', self.logger.statusWriter.call_args.args[1])
                target.side_effect = None

    def test_changed_user_or_package_is_rejected_before_quota_commands(self):
        for attribute, value in (('externalApp', 'other'), ('package_id', 4)):
            with self.subTest(attribute=attribute):
                original = getattr(self.site, attribute)
                setattr(self.site, attribute, value)
                self.assertEqual(0, self.run_creation_tail()[0])
                self.prepare.assert_not_called()
                self.apply.assert_not_called()
                self.cleanup.assert_not_called()
                setattr(self.site, attribute, original)

    def test_existing_website_path_uses_database_identity_too(self):
        self.assertEqual(1, self.run_creation_tail(LimitsCheck=0)[0])
        self.prepare.assert_called_once_with(self.package, [self.site])

    def test_resource_limit_warning_does_not_invoke_legacy_inode_setter(self):
        self.resource.set_user_limits.side_effect = RuntimeError('cgroup fixture failure')
        self.assertEqual(1, self.run_creation_tail()[0])
        self.apply.assert_called_once()
        self.resource.set_inode_limit.assert_not_called()

    def test_status_reader_reports_partial_error_and_does_not_cleanup(self):
        node = copy.deepcopy(method(ROOT / 'websiteFunctions/website.py', 'installWordpressStatus'))
        partial = 'Website was created, but its disk/inode quota could not be verified. [404]'
        commands = Mock(return_value=partial)
        cleanup = Mock()
        namespace = {'ACLManager': NS(CheckStatusFilleLoc=Mock(return_value=True)),
                     'ProcessUtilities': NS(outputExecutioner=commands),
                     'subprocess': NS(call=cleanup), 'json': json, 'HttpResponse': lambda value: value}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'website.py', 'exec'), namespace)
        result = json.loads(namespace['installWordpressStatus'](None, 1, {'statusFile': '/tmp/owned-status'}))
        self.assertEqual(1, result['abort'])
        self.assertEqual(0, result['installStatus'])
        self.assertIn(partial, result['error_message'])
        cleanup.assert_not_called()

    def test_cli_returns_failure_for_unsuccessful_creation_result(self):
        tree = ast.parse((ROOT / 'plogical/virtualHostUtilities.py').read_text())
        branch = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                      and isinstance(node.test, ast.Compare)
                      and any(isinstance(part, ast.Constant) and part.value == 'createVirtualHost'
                              for part in node.test.comparators))
        args = NS(virtualHostName='owned.example', administratorEmail='admin@example.invalid',
                  phpVersion='PHP 8.3', virtualHostUser='owned', ssl='0', dkimCheck='0',
                  openBasedir='0', websiteOwner='admin', package='quota-package', apache='0',
                  tempStatusPath='/tmp/owned-status', mailDomain='0')
        for result in ((0, 'partial quota error'), (1, 'None')):
            namespace = {'args': args, 'sys': sys,
                         'virtualHostUtilities': NS(createVirtualHost=Mock(return_value=result))}
            code = compile(ast.Module(body=branch.body, type_ignores=[]), 'virtualHostUtilities.py', 'exec')
            if result[0] == 0:
                with self.assertRaises(SystemExit) as error:
                    exec(code, namespace)
                self.assertEqual(1, error.exception.code)
            else:
                exec(code, namespace)


if __name__ == '__main__':
    unittest.main()
