"""Unpaid navigation goes to pricing instead of offering a free installer."""
import unittest
try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager


class PaidWordPressNavigationTests(unittest.TestCase):
    def test_create_and_existing_site_pages_redirect_unpaid_users(self):
        manager, _, services = load_wordpress_manager()
        services['ACLManager'].CheckForPremFeature.return_value = 0
        for name in ('WPCreate', 'wordpressInstall', 'WPHome'):
            with self.subTest(page=name):
                result = getattr(manager(domain='owned.example'), name)(userID=7)
                self.assertEqual(result.status_code, 302)
                self.assertEqual(result.url, 'pricing')
        services['httpProc'].assert_not_called()
        services['Administrator'].objects.get.assert_not_called()
        services['ApplicationInstaller'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
