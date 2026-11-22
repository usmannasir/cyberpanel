"""The creation page of Docker sites refuses what it cannot use: no CPU limit, an odd site name, a visitor without the right."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager

REQUEST = {
    'sitename': 'shop', 'Owner': 'reseller', 'Domain': 'shop.example',
    'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 2048, 'App': 'WordPress',
    'WPusername': 'admin', 'WPemal': 'admin@example.test', 'WPpasswd': 'AdminPass123',
}


def submit(**changes):
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': 0}
    acl.currentContextPermission.return_value = 1
    acl.checkOwnerProtection.return_value = 1
    acl.CheckDomainBlackList.return_value = 1
    services['Websites'].objects.filter.return_value.count.return_value = 0
    env['ChildDomains'] = mock.Mock()
    env['ChildDomains'].objects.filter.return_value.count.return_value = 0
    env['PackageAssignment'] = mock.Mock()
    env['DockerPackages'] = mock.Mock()
    env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=4, Ram=8192)
    env['DockerSites'] = mock.Mock()
    env['DOCKER_APPS'] = docker_sites.DOCKER_APPS
    env['n8n_password_problem'] = docker_sites.n8n_password_problem
    env['Docker_Sites'] = mock.Mock()
    env['Docker_Sites'].site_name_problem.return_value = None
    reply = json.loads(cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST, **changes)).content)
    return reply, env


class CpuTests(unittest.TestCase):
    def test_a_site_without_a_cpu_limit_is_refused(self):
        for app in ('WordPress', 'n8n', 'Hermes'):
            for cores in (0, -1, '0', -4):
                with self.subTest(app=app, cores=cores):
                    reply, env = submit(App=app, SiteCPU=cores)
                    self.assertEqual({'status': 0, 'error_message': 'Minimum CPU cores should be 1.'}, reply)
                    env['Docker_Sites'].assert_not_called()

    def test_a_database_without_a_cpu_limit_is_refused(self):
        for app in ('WordPress', 'n8n'):
            for cores in (0, -1, '0'):
                with self.subTest(app=app, cores=cores):
                    reply, env = submit(App=app, MysqlCPU=cores)
                    self.assertEqual({'status': 0, 'error_message': 'Minimum CPU cores should be 1.'}, reply)
                    env['Docker_Sites'].assert_not_called()

    def test_an_application_without_a_database_needs_no_database_cores(self):
        reply, env = submit(App='Hermes', MysqlCPU=0)
        self.assertEqual(1, reply['status'], reply)
        self.assertEqual(0, env['Docker_Sites'].call_args[0][1]['MysqlCPU'])

    def test_one_core_each_is_enough(self):
        for app in ('WordPress', 'n8n', 'Hermes'):
            with self.subTest(app=app):
                reply, env = submit(App=app)
                self.assertEqual(1, reply['status'], reply)
                data = env['Docker_Sites'].call_args[0][1]
                self.assertEqual(1, data['SiteCPU'])

    def test_the_package_still_caps_the_request(self):
        reply, env = submit(SiteCPU=4, MysqlCPU=1)
        self.assertEqual(0, reply['status'])
        self.assertIn('CPUs', reply['error_message'])


class SiteNameTests(unittest.TestCase):
    def test_a_site_name_is_lower_case_letters_and_digits_to_its_very_end(self):
        for name in ('shop\n', 'shop\nx', 'Shop', 'my-shop', 'my shop', '', None, 7, ['shop']):
            with self.subTest(name=name):
                reply, env = submit(sitename=name)
                self.assertEqual(0, reply['status'])
                self.assertIn('invalid site name', reply['error_message'])
                env['Docker_Sites'].assert_not_called()

    def test_ordinary_site_names_are_accepted(self):
        for name in ('shop', 'n8n', '9lives', 'a'):
            reply, env = submit(sitename=name)
            self.assertEqual(1, reply['status'], reply)


def open_creation_page(permitted, assignments=0):
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.currentContextPermission.return_value = permitted
    env['PackageAssignment'] = mock.Mock()
    env['PackageAssignment'].objects.all.return_value.count.return_value = assignments
    env['DockerPackages'] = mock.Mock()
    cls().CreateDockersite(request=mock.Mock(), userID=7)
    return env, services


class CreationPageTests(unittest.TestCase):
    def test_a_user_who_may_not_open_the_page_creates_nothing_by_asking_for_it(self):
        env, services = open_creation_page(permitted=0)
        env['DockerPackages'].assert_not_called()
        env['PackageAssignment'].assert_not_called()
        services['ACLManager'].currentContextPermission.assert_called_once_with(
            services['ACLManager'].loadedACL.return_value, 'createWebsite')
        services['ACLManager'].loadedACL.assert_called_once_with(7)

    def test_the_first_package_is_still_made_for_a_user_who_may(self):
        env, services = open_creation_page(permitted=1)
        self.assertEqual('Default', env['DockerPackages'].call_args[1]['Name'])
        env['DockerPackages'].return_value.save.assert_called_once_with()
        services['Administrator'].objects.get.assert_called_once_with(pk=1)
        env['PackageAssignment'].return_value.save.assert_called_once_with()

    def test_an_existing_assignment_is_left_alone(self):
        env, services = open_creation_page(permitted=1, assignments=3)
        env['DockerPackages'].assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
