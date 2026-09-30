"""Failure handling for child deletion and conversion, without server services."""
import ast
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load_method(relative_path, class_name, method_name, namespace):
    path = Path(__file__).resolve().parents[1] / relative_path
    cls = next(node for node in ast.parse(path.read_text()).body
               if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == method_name)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[method_name]


def response(**data):
    return SimpleNamespace(content=json.dumps(data).encode())


class ChildDeletionTests(unittest.TestCase):
    def run_deletion(self, success=1, output='1,None\n', remains=False):
        process = Mock()
        process.outputExecutioner.return_value = (success, output)
        children = Mock()
        children.objects.filter.return_value.exists.return_value = remains
        acl = Mock()
        acl.checkOwnership.return_value = 1
        delete = load_method('websiteFunctions/website.py', 'WebsiteManager',
                             'submitDomainDeletion', dict(
            json=json, shlex=shlex, ACLManager=acl, Administrator=Mock(),
            ChildDomains=children, ProcessUtilities=process,
            virtualHostUtilities=SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))
        result = delete(None, 1, {'websiteName': 'child.example.test', 'DeleteDocRoot': 1})
        return json.loads(result.content), process

    def test_helper_application_failure_is_not_reported_as_deleted(self):
        result, process = self.run_deletion(output='0,Permission denied\n')
        self.assertEqual(0, result['websiteDeleteStatus'])
        self.assertIn('Permission denied', result['error_message'])

    def test_helper_process_failure_is_not_reported_as_deleted(self):
        result, process = self.run_deletion(success=0, output='ModuleNotFoundError: dependency\n')
        self.assertEqual(0, result['websiteDeleteStatus'])
        self.assertIn('ModuleNotFoundError', result['error_message'])

    def test_remaining_child_record_prevents_false_success(self):
        result, process = self.run_deletion(remains=True)
        self.assertEqual(0, result['websiteDeleteStatus'])

    def test_completed_deletion_preserves_document_root_option(self):
        result, process = self.run_deletion(output='helper diagnostic\n1,None\n')
        self.assertEqual(1, result['websiteDeleteStatus'])
        self.assertIn('--DeleteDocRoot 1', process.outputExecutioner.call_args.args[0])
        self.assertTrue(process.outputExecutioner.call_args.kwargs['retRequired'])

    def test_configuration_failure_keeps_child_model(self):
        children, hosts = Mock(), Mock()
        children.objects.count.return_value = 1
        hosts.objects.count.return_value = 1
        vhost = Mock()
        vhost.deleteCoreConf.return_value = 0
        delete = load_method('plogical/virtualHostUtilities.py', 'virtualHostUtilities',
                             'deleteDomain', dict(
            ChildDomains=children, Websites=hosts, vhost=vhost,
            logging=Mock(), ProcessUtilities=Mock(), installUtilities=Mock(), sslUtilities=Mock()))
        result = delete('child.example.test', 1)
        self.assertEqual(0, result[0])
        children.objects.get.assert_not_called()

    def test_document_root_removal_failure_keeps_child_model(self):
        children, hosts, process, vhost = Mock(), Mock(), Mock(), Mock()
        children.objects.count.return_value = 1
        hosts.objects.count.return_value = 1
        children.objects.get.return_value.path = '/home/parent/child files'
        vhost.deleteCoreConf.return_value = 1
        process.outputExecutioner.return_value = (0, 'Permission denied')
        delete = load_method('plogical/virtualHostUtilities.py', 'virtualHostUtilities',
                             'deleteDomain', dict(
            ChildDomains=children, Websites=hosts, vhost=vhost, shlex=shlex,
            logging=Mock(), ProcessUtilities=process, installUtilities=Mock(), sslUtilities=Mock()))
        result = delete('child.example.test', 1)
        self.assertEqual(0, result[0])
        self.assertIn('Permission denied', result[1])
        children.objects.get.return_value.delete.assert_not_called()
        process.outputExecutioner.assert_called_once_with(
            "rm -rf -- '/home/parent/child files'", retRequired=True)


class ChildConversionTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source = self.root / 'child content'
        self.source.mkdir()
        (self.source / 'customer.txt').write_text('original website data')
        self.target_home = self.root / 'target'
        self.target_home.mkdir()
        self.target = self.target_home / 'public_html'
        self.target.mkdir()
        (self.target / 'index.html').write_text('generated index')
        self.status = self.root / 'status'
        self.child = SimpleNamespace(path=str(self.source), pk=5,
                                     master=SimpleNamespace(domain='parent.example.test'))
        self.children = Mock()
        self.children.objects.get.return_value = self.child
        self.children.objects.filter.return_value.exists.return_value = False
        self.children.objects.filter.return_value.exclude.return_value.exists.return_value = False
        self.manager = Mock()
        self.manager.submitDomainDeletion.return_value = response(websiteDeleteStatus=1)
        self.preflight_response = response(createWebSiteStatus=1)
        self.creation_response = response(
            createWebSiteStatus=1, tempStatusPath='/tmp/creation-status')
        self.manager.submitWebsiteCreation.side_effect = lambda *args, **kwargs: (
            self.preflight_response if kwargs.get('conversionPreflight') else self.creation_response)
        self.creation_status = 'Successfully created [200]'
        self.process = Mock()
        self.process.outputExecutioner.side_effect = self.command
        self.acl = Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnerProtection.return_value = 1
        self.clock = Mock()
        self.clock.monotonic.return_value = 0
        self.files = Mock()
        self.files.fixPermissions.return_value = None
        self.namespace = dict(json=json, os=os, shlex=shlex, time=self.clock,
                              ChildDomains=self.children, ACLManager=self.acl,
                              Administrator=Mock(), ProcessUtilities=self.process)
        self.convert = load_method('plogical/applicationInstaller.py', 'ApplicationInstaller',
                                   'convertDomainToSite', self.namespace)
        self.runner = SimpleNamespace(tempStatusPath=str(self.status), extraArgs={
            'request': SimpleNamespace(session={'userID': 1}, body=json.dumps({
                'domainName':'child.example.test', 'package':'Default',
                'adminEmail':'admin@example.test', 'phpSelection':'PHP 8.3',
                'websiteOwner':'admin', 'openBasedir':0}).encode())})

    def command(self, command, **kwargs):
        if command.startswith('test -d'):
            return 1, ''
        if command.startswith('cat --'):
            return self.creation_status
        if command.startswith('backup='):
            # Run the actual relocation shell command against isolated directories.
            command = command.replace('/home/child.example.test', str(self.target_home))
            process = subprocess.run(command, shell=True, capture_output=True, text=True)
            return int(process.returncode == 0), process.stdout + process.stderr
        self.fail('Unexpected command: ' + command)

    def run_conversion(self):
        with patch.dict(sys.modules, {
            'websiteFunctions.website': SimpleNamespace(WebsiteManager=lambda: self.manager),
            'filemanager.filemanager': SimpleNamespace(FileManager=lambda *args: self.files),
        }):
            self.convert(self.runner)
        return self.status.read_text()

    def assert_original_preserved(self):
        self.assertEqual('original website data', (self.source / 'customer.txt').read_text())
        self.files.fixPermissions.assert_not_called()

    def test_creation_failure_preserves_real_error_and_original_files(self):
        self.creation_status = 'PHP configuration failed [404]'
        status = self.run_conversion()
        self.assertIn('PHP configuration failed', status)
        self.assertIn('Original files remain at %s' % self.source, status)
        self.assertIn('child configuration was removed', status)
        self.assert_original_preserved()

    def test_deletion_failure_prevents_creation(self):
        self.manager.submitDomainDeletion.return_value = response(
            websiteDeleteStatus=0, error_message='Could not delete vhost')
        self.assertIn('Could not delete vhost', self.run_conversion())
        self.assertEqual(1, self.manager.submitWebsiteCreation.call_count)
        self.assertIn('conversionPreflight', self.manager.submitWebsiteCreation.call_args.kwargs)
        self.assert_original_preserved()

    def test_rejected_creation_response_preserves_error(self):
        self.creation_response = response(
            createWebSiteStatus=0, error_message='Invalid package')
        self.assertIn('Invalid package', self.run_conversion())
        self.assert_original_preserved()

    def test_creation_timeout_keeps_original_files(self):
        self.clock.monotonic.side_effect = [0, 601]
        self.assertIn('timed out', self.run_conversion())
        self.assert_original_preserved()

    def test_shared_root_rejected_before_deletion(self):
        self.child.path = '/home/parent.example.test/public_html'
        self.assertIn('shared or overlaps', self.run_conversion())
        self.manager.submitDomainDeletion.assert_not_called()
        self.assert_original_preserved()

    def test_missing_creation_permission_rejected_before_deletion(self):
        self.preflight_response = response(createWebSiteStatus=0, error_message='No permission')
        self.assertIn('permission', self.run_conversion())
        self.manager.submitDomainDeletion.assert_not_called()
        self.assert_original_preserved()

    def test_preflight_error_preserves_child_and_files(self):
        self.preflight_response = response(createWebSiteStatus=0, error_message='Website limit reached')
        self.assertIn('Website limit reached', self.run_conversion())
        self.manager.submitDomainDeletion.assert_not_called()
        self.assert_original_preserved()

    def test_permission_repair_error_is_not_success(self):
        self.files.fixPermissions.return_value = response(status=0, error_message='Symlink attack.')
        status = self.run_conversion()
        self.assertIn('Symlink attack.', status)
        self.assertIn('Files were moved', status)
        self.assertNotIn('[200]', status)
        self.assertEqual('original website data', (self.target / 'customer.txt').read_text())

    def test_success_moves_files_and_then_repairs_permissions(self):
        self.assertIn('Successfully converted. [200]', self.run_conversion())
        self.assertEqual('original website data', (self.target / 'customer.txt').read_text())
        self.assertFalse(self.source.exists())
        self.assertFalse((self.target / 'index.html').exists())
        self.files.fixPermissions.assert_called_once_with('child.example.test')
        self.manager.submitDomainDeletion.assert_called_once_with(1, {
            'websiteName':'child.example.test', 'DeleteDocRoot':0})

    def test_move_failure_restores_generated_root_and_reports_error(self):
        # The command's source disappears after the preflight check.
        self.child.path = str(self.root / 'missing source')
        self.assertIn('Could not move', self.run_conversion())
        self.assertEqual('generated index', (self.target / 'index.html').read_text())
        self.assert_original_preserved()


class ConversionPreflightTests(unittest.TestCase):
    def setUp(self):
        self.acl = Mock()
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnerProtection.return_value = 1
        self.acl.checkOwnership.return_value = 1
        self.acl.websitesLimitCheck.return_value = 1
        self.packages = Mock()
        self.websites = Mock()
        self.websites.objects.filter.return_value.exists.return_value = False
        self.children = Mock()
        self.children.objects.filter.return_value.exclude.return_value.exists.return_value = False
        self.validators = Mock()
        self.validators.domain.return_value = True
        self.validators.email.return_value = True
        self.paths = Mock()
        self.paths.path.isfile.return_value = True
        self.process = Mock()
        self.vhost = Mock()
        self.vhost.checkIfAliasExists.return_value = 0
        self.child = SimpleNamespace(domain='child.example.test', pk=5)
        self.data = dict(domainName=self.child.domain, adminEmail='admin@example.test',
                         package='Default', websiteOwner='admin', phpSelection='PHP 8.3',
                         openBasedir=0)
        self.create = load_method('websiteFunctions/website.py', 'WebsiteManager',
                                 'submitWebsiteCreation', dict(
            json=json, os=self.paths, validators=self.validators,
            ACLManager=self.acl, Administrator=Mock(), Package=self.packages,
            Websites=self.websites, ChildDomains=self.children, ProcessUtilities=self.process,
            PHPManager=SimpleNamespace(getPHPString=lambda version: '83'),
            apache_backend_entitlement_error=lambda data: None,
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))

    def run_preflight(self):
        with patch.dict(sys.modules, {'plogical.vhost': SimpleNamespace(vhost=self.vhost)}):
            result = self.create(None, 1, self.data, conversionPreflight=self.child)
        self.process.popenExecutioner.assert_not_called()
        return json.loads(result.content)

    def test_valid_conversion_does_not_launch_worker(self):
        self.assertEqual(1, self.run_preflight()['createWebSiteStatus'])
        self.packages.objects.get.assert_called_once_with(packageName='Default')
        self.acl.websitesLimitCheck.assert_called_once()
        self.children.objects.filter.return_value.exclude.assert_called_once_with(pk=5)

    def test_invalid_email_fails_before_conversion(self):
        self.validators.email.return_value = False
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertEqual('Invalid email.', result['error_message'])

    def test_missing_package_fails_before_conversion(self):
        self.packages.objects.get.side_effect = ValueError('Package does not exist')
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertIn('Package does not exist', result['error_message'])

    def test_website_limit_fails_before_conversion(self):
        self.acl.websitesLimitCheck.return_value = 0
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertIn('maximum websites limit', result['error_message'])

    def test_missing_php_fails_before_conversion(self):
        self.paths.path.isfile.return_value = False
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertIn('PHP version is not installed', result['error_message'])

    def test_other_child_conflict_fails_before_conversion(self):
        self.children.objects.filter.return_value.exclude.return_value.exists.return_value = True
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertIn('another child domain', result['error_message'])

    def test_invalid_open_basedir_fails_before_conversion(self):
        del self.data['openBasedir']
        result = self.run_preflight()
        self.assertEqual(0, result['createWebSiteStatus'])
        self.assertIn('open_basedir', result['error_message'])

    def test_managed_domain_preflight_skips_remote_reservation(self):
        self.child.domain = 'child.cyberpanel.website'
        self.data['domainName'] = self.child.domain
        with patch.dict(sys.modules, {'requests': Mock()}) as modules:
            self.assertEqual(1, self.run_preflight()['createWebSiteStatus'])
            modules['requests'].post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
