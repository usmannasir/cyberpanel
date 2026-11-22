"""Live scan progress is shown to the signed-in user who may see the scan, and to nobody else."""
import json
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner import status_api


class Missing(Exception):
    pass


class LiveProgressTests(SimpleTestCase):

    def setUp(self):
        self.owner = SimpleNamespace(pk=7)
        self.scan = SimpleNamespace(scan_id='cp_0123456789ab', admin=self.owner, status='running')
        self.status = SimpleNamespace(
            phase='scanning_files', progress=40, current_file='wp-content/plugins/demo.php', files_discovered=10,
            files_scanned=4, files_remaining=6, threats_found=1, critical_threats=0, high_threats=1,
            activity_description='Scanning', last_updated=datetime(2026, 11, 22, 10, 0, 0), is_active=True)
        self.acl = {'admin': 0}
        self.visible = [self.owner]

        def scan_get(scan_id):
            if scan_id != self.scan.scan_id:
                raise Missing()
            return self.scan

        def status_get(scan_id):
            if self.status is None or scan_id != self.scan.scan_id:
                raise Missing()
            return self.status

        for target, value in (
                ('aiScanner.status_api.ScanHistory',
                 SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(get=scan_get))),
                ('aiScanner.models.ScanHistory',
                 SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(get=scan_get))),
                ('aiScanner.status_api.ScanStatusUpdate',
                 SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(get=status_get))),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (
                ('plogical.acl.ACLManager.loadedACL', lambda userID: self.acl),
                ('plogical.acl.ACLManager.loadUserObjects', lambda userID: self.visible),
        ):
            patcher = mock.patch(target, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def ask(self, session, scan_id='cp_0123456789ab'):
        request = RequestFactory().get('/api/ai-scanner/scan/%s/live-progress' % scan_id)
        request.session = session
        response = status_api.get_live_scan_progress(request, scan_id)
        return response.status_code, json.loads(response.content.decode('utf-8'))

    def test_nobody_without_a_session_sees_progress(self):
        status, reply = self.ask({})
        self.assertEqual(401, status)
        self.assertEqual({'success': False, 'error': 'Not authenticated'}, reply)

    def test_the_owner_sees_progress(self):
        status, reply = self.ask({'userID': 7})
        self.assertEqual(200, status)
        self.assertEqual((True, 'scanning_files', 40, 'wp-content/plugins/demo.php'),
                         (reply['success'], reply['phase'], reply['progress'], reply['current_file']))

    def test_another_users_scan_looks_like_no_scan(self):
        self.visible = [SimpleNamespace(pk=9)]
        self.assertEqual((404, {'success': False, 'error': 'Scan not found'}), self.ask({'userID': 9}))
        self.assertEqual((404, {'success': False, 'error': 'Scan not found'}), self.ask({'userID': 9}, 'cp_unknown'))

    def test_an_administrator_sees_every_scan(self):
        self.acl = {'admin': 1}
        self.visible = []
        self.assertEqual(200, self.ask({'userID': 1})[0])

    def test_a_user_whose_acl_switches_the_scanner_off_sees_nothing(self):
        self.acl = {'admin': 0, 'aiScannerAccess': 0}
        self.assertEqual((403, {'success': False, 'error': 'Access denied'}), self.ask({'userID': 7}))

    def test_a_scan_without_status_yet_says_so_to_its_owner(self):
        self.status = None
        status, reply = self.ask({'userID': 7})
        self.assertEqual((404, True, 'running'), (status, reply['scan_exists'], reply['scan_status']))
