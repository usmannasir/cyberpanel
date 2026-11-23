"""Each application install run gets a status file of its own.

The install pages poll the file named in the launch answer. A name another
installer can also draw shows that installer's progress or error on this page.
"""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

from plogical import statusUtilities
from plogical.wordpressInstallerUtilities import apache_backend_missing, apache_backend_required_message

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / 'websiteFunctions' / 'website.py'

# Launch view -> application handed to ApplicationInstaller, and the request it receives.
LAUNCHERS = {
    'installWordpress': ('wordpress', {
        'domain': 'site.example.com', 'home': '1', 'blogTitle': 'Blog', 'adminUser': 'admin',
        'passwordByPass': 'secret', 'adminEmail': 'a@example.com'}),
    'mauticInstall': ('mautic', {
        'domain': 'site.example.com', 'home': '1', 'username': 'admin', 'email': 'a@example.com',
        'passwordByPass': 'secret'}),
    'prestaShopInstall': ('prestashop', {
        'domain': 'site.example.com', 'home': '1', 'shopName': 'Shop', 'firstName': 'A',
        'lastName': 'B', 'databasePrefix': 'ps_', 'email': 'a@example.com',
        'passwordByPass': 'secret'}),
}


def manager_method(name):
    source = ast.parse(WEBSITE.read_text(encoding='utf-8'))
    manager = next(node for node in source.body
                   if isinstance(node, ast.ClassDef) and node.name == 'WebsiteManager')
    method = next(node for node in manager.body
                  if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    return method


class LaunchMixin:
    def launch(self, view, data, directory, process=None, apache_config_base='/nonexistent/apache/'):
        method = manager_method(view)
        module = ast.Module(body=[method], type_ignores=[])
        installer = mock.Mock()
        acl = mock.Mock()
        acl.checkOwnership.return_value = 1
        version_answer = mock.Mock()
        version_answer.json.return_value = {'offers': [{'current': '6.8.3'}]}
        requests = SimpleNamespace(get=mock.Mock(return_value=version_answer),
                                   RequestException=OSError)
        env = {
            'ACLManager': acl, 'Administrator': mock.Mock(), 'ApplicationInstaller': installer,
            'ProcessUtilities': process or mock.Mock(),
            'ApacheVhost': SimpleNamespace(configBasePath=apache_config_base),
            'apache_backend_missing': apache_backend_missing,
            'apache_backend_required_message': apache_backend_required_message,
            'virtualHostUtilities': SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
            'mailUtilities': mock.Mock(), 'time': mock.Mock(), 'json': json,
            'HttpResponse': lambda body: body, 'requests': requests,
            'select_wordpress_version': lambda offers: offers[0]['current'],
            # Every caller of randint draws the same number, as two workers
            # sharing one random state do.
            'randint': lambda low, high: 1234,
        }
        exec(compile(module, str(WEBSITE), 'exec'), env)
        reserved = ModuleType('plogical.statusUtilities')
        reserved.create_status_file = lambda: statusUtilities.create_status_file(directory)
        with mock.patch.dict(sys.modules, {'plogical.statusUtilities': reserved}), \
                mock.patch('plogical.statusUtilities', reserved, create=True):
            answer = json.loads(env[view](SimpleNamespace(domain=None), userID=1, data=dict(data)))
        self.process = env['ProcessUtilities']
        return answer, installer


class ApplicationInstallStatusFileTests(LaunchMixin, unittest.TestCase):

    def test_each_launch_reserves_its_own_status_file(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = []
            for view, (application, data) in sorted(LAUNCHERS.items()):
                for attempt in range(2):
                    with self.subTest(view=view, attempt=attempt):
                        answer, installer = self.launch(view, data, directory)
                        self.assertEqual(answer['installStatus'], 1)
                        path = answer['tempStatusPath']
                        self.assertEqual(installer.call_args[0][0], application)
                        self.assertEqual(installer.call_args[0][1]['tempStatusPath'], path)
                        self.assertEqual(os.path.dirname(path), directory)
                        self.assertTrue(os.path.isfile(path))
                        self.assertTrue(statusUtilities.valid_status_path(
                            '/home/cyberpanel/' + os.path.basename(path)))
                        seen.append(path)
            self.assertEqual(len(seen), len(set(seen)))

    def test_refused_request_reserves_no_status_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data = dict(LAUNCHERS['mauticInstall'][1])
            data['home'] = '0'  # a sub-folder install without its path
            answer, installer = self.launch('mauticInstall', data, directory)

            self.assertEqual(answer['installStatus'], 0)
            installer.assert_not_called()
            self.assertEqual(os.listdir(directory), [])


class PrestaShopViewRefusalTests(LaunchMixin, unittest.TestCase):
    """The PrestaShop launch refuses an OpenLiteSpeed-only website before it changes it."""

    def openlitespeed(self):
        process = mock.Mock()
        process.OLS = 1
        process.decideServer.return_value = 1
        return process

    def test_openlitespeed_only_website_is_refused_before_its_php_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            answer, installer = self.launch('prestaShopInstall', LAUNCHERS['prestaShopInstall'][1],
                                            directory, process=self.openlitespeed(),
                                            apache_config_base=directory + '/apache/')

            self.assertEqual(answer['installStatus'], 0)
            self.assertEqual(answer['error_message'],
                             apache_backend_required_message('PrestaShop', 'site.example.com'))
            self.process.executioner.assert_not_called()
            installer.assert_not_called()
            self.assertEqual(os.listdir(directory), [])

    def test_apache_backed_website_has_its_php_changed_and_is_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            apache = os.path.join(directory, 'apache')
            os.mkdir(apache)
            Path(apache, 'site.example.com.conf').write_text('<VirtualHost *:8083>\n')
            answer, installer = self.launch('prestaShopInstall', LAUNCHERS['prestaShopInstall'][1],
                                            directory, process=self.openlitespeed(),
                                            apache_config_base=apache + '/')

            self.assertEqual(answer['installStatus'], 1)
            command = self.process.executioner.call_args[0][0]
            self.assertIn("changePHP --phpVersion 'PHP 8.3'", command)
            self.assertEqual(installer.call_args[0][0], 'prestashop')


if __name__ == '__main__':
    unittest.main()
