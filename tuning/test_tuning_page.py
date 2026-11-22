"""The PHP tuning page prepares nothing for a user it is refused to."""
import unittest

from tuning.test_tuning_requests import load_manager


class TuningPageTests(unittest.TestCase):
    def test_nothing_is_prepared_for_a_user_the_page_is_refused_to(self):
        manager, services = load_manager(admin=0)
        request = object()
        result = manager.phpTuning(request, 7)
        services.http.assert_called_once_with(request, 'tuning/phpTuning.html', None, 'admin')
        self.assertIs(services.http.return_value.render.return_value, result)
        services.acl.findAllSites.assert_not_called()
        services.process.decideServer.assert_not_called()

    def test_an_administrator_gets_the_list_of_websites(self):
        manager, services = load_manager(admin=1)
        services.acl.findAllSites.return_value = ['example.test']
        manager.phpTuning(object(), 7)
        self.assertEqual({'websiteList': ['example.test'], 'OLS': 1}, services.http.call_args[0][2])


if __name__ == '__main__':
    unittest.main()
