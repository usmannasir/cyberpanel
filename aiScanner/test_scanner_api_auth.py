"""A scanner key or token reaches only the website its own scan was started for."""
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from django.utils import timezone

from aiScanner import api
from plogical.scannerFileAccess import Refused


class Missing(Exception):
    pass


def model(**objects):
    return SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(**objects))


class ScannerApiAuthTests(SimpleTestCase):

    def setUp(self):
        now = timezone.now()
        self.owner = SimpleNamespace(pk=7, userName='owner')
        self.other = SimpleNamespace(pk=8, userName='other')
        self.settings = {
            7: SimpleNamespace(admin=self.owner, api_key='cp_key_of_the_owner'),
            8: SimpleNamespace(admin=self.other, api_key='cp_key_of_the_other'),
        }
        self.scan = SimpleNamespace(scan_id='cp_0123456789ab', admin=self.owner, domain='e.com',
                                    status='completed', started_at=now - timedelta(hours=3),
                                    completed_at=now - timedelta(hours=2))
        self.websites = {'e.com': SimpleNamespace(domain='e.com', externalApp='ecom1234', admin=self.owner)}
        self.file_token = None
        self.owns = 1
        # Another customer's WordPress site whose address contains the scan's domain.
        self.wordpress_sites = mock.Mock()
        self.wordpress_sites.filter.return_value.first.return_value = SimpleNamespace(
            path='/home/shop.example.com/public_html', owner=SimpleNamespace(externalApp='shope5678'))

        def file_tokens(**query):
            found = self.file_token if self.file_token and query.get('token') == self.file_token.token else None
            return SimpleNamespace(first=lambda: found)

        def file_token_get(**query):
            found = file_tokens(**query).first()
            if found is None:
                raise Missing()
            return found

        def settings_filter(**query):
            found = [row for row in self.settings.values() if row.api_key == query.get('api_key')]
            return SimpleNamespace(first=lambda: found[0] if found else None)

        def settings_get(**query):
            return self.settings[query['admin'].pk]

        def scan_get(**query):
            if query.get('scan_id') != self.scan.scan_id or query.get('admin', self.scan.admin) is not self.scan.admin:
                raise Missing()
            return self.scan

        def website_get(**query):
            if query.get('domain') not in self.websites:
                raise Missing()
            return self.websites[query['domain']]

        tokens = model(filter=file_tokens, get=file_token_get)
        settings = model(filter=settings_filter, get=settings_get)
        scans = model(get=scan_get)
        websites = model(get=website_get)
        for target, value in (
                ('aiScanner.api.FileAccessToken', tokens), ('aiScanner.models.FileAccessToken', tokens),
                ('aiScanner.api.AIScannerSettings', settings), ('aiScanner.models.AIScannerSettings', settings),
                ('aiScanner.api.ScanHistory', scans), ('aiScanner.models.ScanHistory', scans),
                ('aiScanner.api.Websites', websites), ('websiteFunctions.models.Websites', websites),
                ('websiteFunctions.models.WPSites', SimpleNamespace(objects=self.wordpress_sites)),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (
                ('plogical.acl.ACLManager.loadedACL', lambda pk: {'admin': 0}),
                ('plogical.acl.ACLManager.checkOwnership', lambda domain, admin, acl: self.owns),
        ):
            patcher = mock.patch(target, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def key_access(self, token='cp_key_of_the_owner'):
        return api.validate_access_token(token, self.scan.scan_id)

    def test_the_key_reaches_the_website_whose_domain_is_exactly_the_scans_domain(self):
        auth, error = self.key_access()
        self.assertIsNone(error)
        self.assertEqual(('e.com', '/home/e.com/public_html', 'ecom1234', 'api_key'),
                         (auth.domain, auth.wp_path, auth.external_app, auth.auth_type))
        self.wordpress_sites.filter.assert_not_called()

    def test_a_scan_of_a_website_that_no_longer_exists_reaches_nothing(self):
        self.websites.clear()
        self.assertEqual((None, 'Website not found'), self.key_access())

    def test_a_scan_of_a_website_its_owner_no_longer_has_reaches_nothing(self):
        self.owns = 0
        self.assertEqual((None, 'Website not found'), self.key_access())

    def test_the_key_works_for_a_limited_time_after_the_scan(self):
        self.scan.completed_at = timezone.now() - timedelta(days=6, hours=23)
        self.assertIsNone(self.key_access()[1])
        self.scan.completed_at = timezone.now() - timedelta(days=7, minutes=1)
        self.assertEqual((None, 'Scan is too old for file operations. Run a new scan.'), self.key_access())
        # A scan whose result never arrived counts from its start.
        self.scan.completed_at = None
        self.scan.started_at = timezone.now() - timedelta(days=1)
        self.assertIsNone(self.key_access()[1])
        self.scan.started_at = timezone.now() - timedelta(days=8)
        self.assertIsNotNone(self.key_access()[1])

    def test_only_the_key_of_the_scans_owner_is_accepted(self):
        self.assertEqual((None, 'Invalid token'), self.key_access('cp_key_of_the_other'))
        self.assertEqual((None, 'Invalid token'), self.key_access('cp_unknown'))
        self.assertEqual((None, 'Invalid token format'), self.key_access('key_of_the_owner'))
        self.assertEqual((None, 'Invalid token format'), self.key_access(None))
        self.settings[7].api_key = None
        self.assertEqual((None, 'Invalid token'), self.key_access('cp_None'))

    def test_a_key_that_several_administrators_share_still_reaches_the_owners_scan(self):
        self.settings[8].api_key = 'cp_shared_server_key'
        self.settings[7].api_key = 'cp_shared_server_key'
        self.settings = {8: self.settings[8], 7: self.settings[7]}
        auth, error = self.key_access('cp_shared_server_key')
        self.assertIsNone(error)
        self.assertEqual('ecom1234', auth.external_app)

    def test_a_website_without_a_system_user_is_not_given_another_account(self):
        self.websites['e.com'].externalApp = ''
        auth, error = self.key_access()
        self.assertNotEqual('owner', getattr(auth, 'external_app', None))
        with self.assertRaises(Refused) as caught:
            api.site_files(auth)
        self.assertEqual('no_site_user', caught.exception.code)

    def test_the_file_token_of_a_running_scan_reaches_the_scans_website(self):
        self.file_token = SimpleNamespace(token='cp_file_token', domain='e.com', wp_path='/home/e.com/public_html',
                                          is_expired=lambda: False)
        auth, error = api.validate_access_token('cp_file_token', self.scan.scan_id)
        self.assertIsNone(error)
        self.assertEqual(('e.com', '/home/e.com/public_html', 'ecom1234', 'file_token'),
                         (auth.domain, auth.wp_path, auth.external_app, auth.auth_type))
        self.file_token.is_expired = lambda: True
        self.assertEqual((None, 'Invalid token'), api.validate_access_token('cp_file_token', self.scan.scan_id))
