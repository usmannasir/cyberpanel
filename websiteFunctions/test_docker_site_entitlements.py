"""Docker App is free, while package administration still follows panel ACLs."""
import json
import unittest
from unittest import mock

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager


class DockerSiteAccessTests(unittest.TestCase):
    def test_create_page_is_available_without_a_paid_entitlement(self):
        cls, env, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 0
        services['ACLManager'].loadAllUsers.return_value = ['admin']
        env['PackageAssignment'] = mock.Mock()
        env['PackageAssignment'].objects.all.return_value.count.return_value = 1
        expected = object()
        services['httpProc'].return_value.render.return_value = expected

        self.assertIs(expected, cls().CreateDockersite(request=object(), userID=7))
        self.assertEqual('websiteFunctions/CreateDockerSite.html',
                         services['httpProc'].call_args.args[1])
        services['ACLManager'].CheckForPremFeature.assert_not_called()

    def test_free_access_does_not_override_package_admin_acl(self):
        cls, env, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 0
        services['ACLManager'].loadedACL.return_value = {'admin': 0}
        denied = object()
        services['ACLManager'].loadError.return_value = denied
        self.assertIs(denied, cls().AddDockerpackage(userID=7, data={}))
        services['Administrator'].objects.get.assert_not_called()
        services['ACLManager'].CheckForPremFeature.assert_not_called()

    def test_free_package_creation_preserves_values_and_response(self):
        cls, env, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 0
        services['ACLManager'].loadedACL.return_value = {'admin': 1}
        package = mock.Mock()
        env['DockerPackages'] = mock.Mock(return_value=package)
        result = cls().AddDockerpackage(userID=7, data={
            'name': 'fixture-package', 'cpu': 2, 'Memory': 1024, 'Bandwidth': 100, 'disk': 10})
        self.assertEqual(1, json.loads(result.content)['status'])
        env['DockerPackages'].assert_called_once_with(Name='fixture-package', CPUs=2,
            Ram=1024, Bandwidth=100, DiskSpace=10, config='')
        package.save.assert_called_once_with()
        services['ACLManager'].CheckForPremFeature.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
