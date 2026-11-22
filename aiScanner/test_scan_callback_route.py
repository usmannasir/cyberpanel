"""Scan results arrive at one address only: the one the panel gives the platform."""
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from aiScanner import aiScannerManager, urls, views


class ScanCallbackRouteTests(SimpleTestCase):

    def test_the_second_callback_address_is_gone(self):
        with self.assertRaises(Resolver404):
            resolve('/callback/', urlconf=urls)
        self.assertFalse(hasattr(views, 'scanCallback'))
        self.assertFalse(hasattr(aiScannerManager.AIScannerManager, 'scanCallback'))
