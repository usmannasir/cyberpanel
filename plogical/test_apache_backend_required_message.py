"""An installer that needs Apache names its own application and refuses before it creates anything."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from plogical.wordpressInstallerUtilities import apache_backend_missing, apache_backend_required_message

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'plogical' / 'applicationInstaller.py'
OLS = 1
ENT = 3


def installer_method(name):
    source = ast.parse(INSTALLER.read_text(encoding='utf-8'))
    installer = next(node for node in source.body
                     if isinstance(node, ast.ClassDef) and node.name == 'ApplicationInstaller')
    return next(node for node in installer.body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def message_calls():
    """(installer method, first argument) of every apache_backend_required_message call."""
    source = ast.parse(INSTALLER.read_text(encoding='utf-8'))
    installer = next(node for node in source.body
                     if isinstance(node, ast.ClassDef) and node.name == 'ApplicationInstaller')
    calls = []
    for method in installer.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        for node in ast.walk(method):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'apache_backend_required_message'):
                calls.append((method.name, ast.literal_eval(node.args[0])))
    return calls


class ApacheBackendRequiredMessageTests(unittest.TestCase):
    def test_message_names_the_application_and_where_to_switch(self):
        message = apache_backend_required_message('Mautic', 'shop.example.com')

        self.assertIn('Mautic needs this website to be served through Apache', message)
        self.assertIn('then start the Mautic installation again', message)
        self.assertIn('Apache Manager (/websites/ApacheManager/shop.example.com)', message)
        self.assertNotIn('PrestaShop', message)
        self.assertNotIn('Prestashop', message)

    def test_message_promises_nothing_about_licences(self):
        message = apache_backend_required_message('PrestaShop', 'shop.example.com').lower()

        for word in ('licen', 'free', 'paid', 'purchase', 'enterprise'):
            self.assertNotIn(word, message)

    def test_old_prestashop_sentence_is_gone(self):
        text = INSTALLER.read_text(encoding='utf-8')

        self.assertNotIn('otherwise Prestashop installation will not work', text)
        self.assertNotIn('please switch your website to use Apache', text)

    def test_every_installer_names_its_own_application(self):
        calls = message_calls()

        self.assertIn(('installPrestaShop', 'PrestaShop'), calls)
        for method, application in calls:
            with self.subTest(method=method):
                self.assertEqual(method.lower(), 'install' + application.lower())


class PrestaShopRefusalTests(unittest.TestCase):
    """Run installPrestaShop on its own with everything it reaches replaced."""

    def run_installer(self, apache_conf_exists, server=OLS):
        method = installer_method('installPrestaShop')
        module = ast.Module(body=[method], type_ignores=[])
        with tempfile.TemporaryDirectory() as directory:
            conf_base = os.path.join(directory, 'conf') + os.sep
            os.mkdir(conf_base)
            if apache_conf_exists:
                Path(conf_base, 'shop.example.com.conf').write_text('<VirtualHost *:8083>\n')
            status_path = os.path.join(directory, 'status')
            process = mock.Mock()
            process.OLS = OLS
            process.decideServer.return_value = server
            child_domains, websites = mock.Mock(), mock.Mock()
            # Stop the run at its first check on the website: the database allowance.
            child_domains.objects.get.side_effect = LookupError('not a child domain')
            website = mock.Mock(externalApp='shopuser')
            website.package.dataBases = 1
            website.databases_set.all.return_value.count.return_value = 1
            websites.objects.get.return_value = website
            env = {
                'os': os, 'ApacheVhost': SimpleNamespace(configBasePath=conf_base),
                'ProcessUtilities': process, 'ChildDomains': child_domains, 'Websites': websites,
                'apache_backend_missing': apache_backend_missing,
                'apache_backend_required_message': apache_backend_required_message,
                'BaseException': BaseException, 'open': open, 'str': str,
                'mysqlUtilities': mock.Mock(), 'Databases': mock.Mock(), 'logging': mock.Mock(),
                'LookupError': LookupError,
            }
            exec(compile(module, str(INSTALLER), 'exec'), env)
            installer = SimpleNamespace(extraArgs={
                'admin': mock.Mock(), 'domainName': 'shop.example.com', 'home': '1',
                'shopName': 'Shop', 'firstName': 'A', 'lastName': 'B', 'databasePrefix': 'ps_',
                'email': 'a@example.com', 'password': 'secret', 'tempStatusPath': status_path,
            }, dbCreation=mock.Mock(), dataLossCheck=mock.Mock())
            result = env['installPrestaShop'](installer)
            status = Path(status_path).read_text()
        return result, status, installer, child_domains, websites

    def test_openlitespeed_website_is_refused_before_anything_is_created(self):
        result, status, installer, child_domains, websites = self.run_installer(False)

        self.assertEqual(result, 0)
        self.assertEqual(status, apache_backend_required_message('PrestaShop', 'shop.example.com') + ' [404]')
        child_domains.objects.get.assert_not_called()
        websites.objects.get.assert_not_called()
        installer.dbCreation.assert_not_called()
        installer.dataLossCheck.assert_not_called()

    def test_apache_backed_website_goes_on_to_the_install(self):
        result, status, installer, child_domains, websites = self.run_installer(True)

        self.assertEqual(result, 0)
        websites.objects.get.assert_called_once_with(domain='shop.example.com')
        self.assertEqual(status, 'Maximum database limit reached for this website. [404]')

    def test_server_other_than_openlitespeed_is_not_refused(self):
        result, status, installer, child_domains, websites = self.run_installer(False, server=ENT)

        websites.objects.get.assert_called_once_with(domain='shop.example.com')
        self.assertEqual(status, 'Maximum database limit reached for this website. [404]')


class ApacheBackendMissingTests(unittest.TestCase):
    def test_only_an_openlitespeed_website_without_its_apache_conf_is_missing_apache(self):
        with tempfile.TemporaryDirectory() as directory:
            base = directory + os.sep
            Path(base, 'apache.example.com.conf').write_text('<VirtualHost *:8083>\n')

            self.assertTrue(apache_backend_missing('ols.example.com', base, True))
            self.assertFalse(apache_backend_missing('apache.example.com', base, True))
            self.assertFalse(apache_backend_missing('ols.example.com', base, False))


if __name__ == '__main__':
    unittest.main()
