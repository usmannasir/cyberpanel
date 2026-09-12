"""Paid Docker Site provisioning must be denied before manager work begins."""
import json
import unittest
from unittest import mock

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager


class DockerSiteEntitlementTests(unittest.TestCase):
    def test_unpaid_pages_and_actions_do_not_load_data_or_start_work(self):
        cls, env, services = load_wordpress_manager()
        manager = cls()
        services['ACLManager'].CheckForPremFeature.return_value = 0
        pages = ('CreateDockerPackage', 'AssignPackage', 'CreateDockersite', 'Dockersitehome')
        actions = ('AddDockerpackage', 'Getpackage', 'Updatepackage', 'AddAssignment', 'submitDockerSiteCreation')
        for name in pages:
            with self.subTest(page=name):
                result = getattr(manager, name)(userID=7)
                self.assertEqual(302, result.status_code)
                self.assertEqual('pricing', result.url)
        for name in actions:
            with self.subTest(action=name):
                result = json.loads(getattr(manager, name)(userID=7).content)
                self.assertEqual(0, result['status'])
                self.assertEqual(0, result['installStatus'])
                self.assertEqual(0, result['createWebSiteStatus'])
        services['ACLManager'].loadedACL.assert_not_called()
        services['Administrator'].objects.get.assert_not_called()

    def test_license_does_not_override_package_admin_access(self):
        cls, env, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 1
        services['ACLManager'].loadedACL.return_value = {'admin': 0}
        denied = object()
        services['ACLManager'].loadError.return_value = denied
        self.assertIs(denied, cls().AddDockerpackage(userID=7, data={}))
        services['Administrator'].objects.get.assert_not_called()

    def test_paid_package_creation_preserves_values_and_response(self):
        cls, env, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 1
        services['ACLManager'].loadedACL.return_value = {'admin': 1}
        package = mock.Mock()
        env['DockerPackages'] = mock.Mock(return_value=package)
        result = cls().AddDockerpackage(userID=7, data={
            'name': 'fixture-package', 'cpu': 2, 'Memory': 1024, 'Bandwidth': 100, 'disk': 10})
        self.assertEqual(1, json.loads(result.content)['status'])
        env['DockerPackages'].assert_called_once_with(Name='fixture-package', CPUs=2,
            Ram=1024, Bandwidth=100, DiskSpace=10, config='')
        package.save.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2)
