"""A Docker site always gets a CPU limit: none of its containers is started without one."""
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
