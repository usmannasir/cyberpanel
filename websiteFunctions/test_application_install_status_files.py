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


class ApplicationInstallStatusFileTests(unittest.TestCase):
    def launch(self, view, data, directory):
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
            'ProcessUtilities': mock.Mock(), 'virtualHostUtilities': SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
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
        return answer, installer

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


if __name__ == '__main__':
    unittest.main()
