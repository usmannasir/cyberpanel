"""The PHP pages prepare nothing for a user they are refused to."""
import unittest

from managePHP.test_request_methods import load_views, request_factory

PAGES = (('installExtensions', 'managePHP/installExtensions.html'), ('editPHPConfigs', 'managePHP/editPHPConfig.html'))


class PHPPageAccessTests(unittest.TestCase):
    def setUp(self):
        self.views, self.services, _ = load_views([name for name, _ in PAGES])

    def page(self, name, admin, path='/managephp/x'):
        for service in self.services.values():
            service.reset_mock()
        self.services['ACLManager'].loadedACL.return_value = {'admin': admin}
        request = request_factory().get(path)
        request.session = {'userID': 7}
        return request, getattr(self.views, name)(request)

    def test_another_user_gets_the_refusal_and_nothing_else_happens(self):
        for name, template in PAGES:
            with self.subTest(page=name):
                request, response = self.page(name, 0)
                self.services['httpProc'].assert_called_once_with(request, template, None, 'admin')
                self.assertIs(self.services['httpProc'].return_value.render.return_value, response)
                for service in ('PHP', 'installedPackages', 'ApachePHP', 'installedPackagesApache',
                                'ApacheController', 'PHPManager', 'ProcessUtilities', 'open'):
                    self.assertEqual([], self.services[service].mock_calls, service)

    def test_an_administrator_gets_the_installed_versions(self):
        request, _ = self.page('editPHPConfigs', 1)
        self.services['ApacheController'].checkIfApacheInstalled.assert_called_once_with()
        arguments = self.services['httpProc'].call_args[0]
        self.assertEqual((request, 'managePHP/editPHPConfig.html'), arguments[:2])
        self.assertIn('phps', arguments[2])
        self.assertEqual('admin', arguments[3])

    def test_a_visitor_who_is_not_signed_in_is_sent_to_the_login_page(self):
        for name, _ in PAGES:
            request = request_factory().get('/managephp/x')
            request.session = {}
            self.assertEqual(302, getattr(self.views, name)(request).status_code)
        self.assertEqual([], self.services['PHP'].mock_calls)


if __name__ == '__main__':
    unittest.main()
