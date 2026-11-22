"""Only the routes something calls are served under /aiscanner/."""
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from aiScanner import urls, views


class ScannerRouteTests(SimpleTestCase):

    def test_the_old_file_routes_are_gone(self):
        for path in ('/api/authenticate/', '/api/list-files/', '/api/get-file/'):
            with self.assertRaises(Resolver404):
                resolve(path, urlconf=urls)
        for name in ('aiScannerAuthenticate', 'aiScannerListFiles', 'aiScannerGetFile'):
            self.assertFalse(hasattr(views, name))

    def test_the_pages_own_routes_remain(self):
        names = set(pattern.name for pattern in urls.urlpatterns)
        for name in ('aiScannerHome', 'aiScannerSetupPayment', 'aiScannerSetupComplete', 'aiScannerStartScan',
                     'aiScannerHistory', 'aiScannerDetails', 'aiScannerScheduledScans'):
            self.assertIn(name, names)
