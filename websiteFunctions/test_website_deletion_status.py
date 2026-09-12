import json
import unittest
from unittest import mock
from websiteFunctions import website as module
from websiteFunctions.models import GDriveSites


class WebsiteDeletionStatusTests(unittest.TestCase):
    def delete(self, state='completed', remains=False, permitted=True, child=False):
        with mock.patch.object(module.ACLManager, 'FindIfChild', return_value=int(child)), mock.patch.object(module.ACLManager, 'loadedACL', return_value={}), mock.patch.object(module.ACLManager, 'currentContextPermission', return_value=int(permitted)), mock.patch.object(module.ACLManager, 'checkOwnership', return_value=1), mock.patch.object(module.Administrator.objects, 'get', return_value=mock.Mock()), mock.patch.object(module.Websites.objects, 'filter') as sites, mock.patch.object(GDriveSites.objects, 'filter') as drives, mock.patch('plogical.websiteDeletion.wait_for_deletion', return_value=state) as worker:
            sites.return_value.exists.return_value = remains
            response = json.loads(module.WebsiteManager().submitWebsiteDeletion(7, {'websiteName': 'fixture.example'}).content)
        return response, drives, worker

    def test_success_requires_absent_row_and_completed_worker(self):
        response, drives, worker = self.delete()
        self.assertEqual(1, response['websiteDeleteStatus'])
        self.assertEqual('completed', response['state'])
        drives.return_value.delete.assert_called_once()

    def test_remaining_row_is_not_reported_as_deleted(self):
        response, drives, worker = self.delete(remains=True)
        self.assertEqual(0, response['websiteDeleteStatus'])
        drives.assert_not_called()

    def test_pending_keeps_metadata_and_does_not_claim_completion(self):
        response, drives, worker = self.delete(state='pending')
        self.assertEqual(2, response['websiteDeleteStatus'])
        self.assertEqual('pending', response['state'])
        drives.assert_not_called()

    def test_worker_failure_preserves_dependent_metadata(self):
        response, drives, worker = self.delete(state='failed')
        self.assertEqual(0, response['websiteDeleteStatus'])
        drives.assert_not_called()

    def test_failover_retains_shared_row_and_requires_primary_action(self):
        response, drives, worker = self.delete(remains=True, child=True)
        self.assertEqual(2, response['websiteDeleteStatus'])
        self.assertEqual('awaiting_primary', response['state'])
        drives.assert_not_called()
