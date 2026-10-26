import json
import unittest
from types import SimpleNamespace as NS
from unittest import mock
from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager

class RestoreBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.manager,self.ns,self.services=load_wordpress_manager()
        self.acl=self.services['ACLManager'];self.acl.CheckForPremFeature.return_value=1
        self.acl.loadedACL.return_value={'admin':0};self.acl.CheckIPBackupObjectOwner.return_value=1
        self.acl.checkOwnership.return_value=1;self.acl.currentContextPermission.return_value=1
        self.services['Administrator'].objects.get.return_value=NS(pk=7)
        self.services['WPSites'].objects.get.return_value=NS(owner=NS(domain='owned.example'))
        self.services['Websites'].objects.filter.return_value.exists.return_value=False
        self.services['validators'].domain.return_value=True
        self.data={'backupid':12,'DesSite':'34','Domain':'','path':'','home':'1'}
    def restore(self):return json.loads(self.manager().RestoreWPbackupNow(7,self.data).content)
    def test_unpaid_restore_stops_before_backup_lookup(self):
        self.acl.CheckForPremFeature.return_value=0
        self.assertEqual(0,self.restore()['status']);self.services['WPSitesBackup'].objects.get.assert_not_called();self.services['ApplicationInstaller'].assert_not_called()
    def test_paid_backup_owner_and_destination_can_start_existing_worker(self):
        self.assertEqual(1,self.restore()['status']);self.acl.CheckIPBackupObjectOwner.assert_called_once();self.acl.checkOwnership.assert_called_once_with('owned.example',mock.ANY,{'admin':0});self.services['ApplicationInstaller'].return_value.start.assert_called_once()
    def test_another_accounts_backup_never_starts_worker(self):
        self.acl.CheckIPBackupObjectOwner.return_value=0
        self.assertEqual(0,self.restore()['status']);self.services['ApplicationInstaller'].assert_not_called()
    def test_another_accounts_destination_never_starts_worker(self):
        self.acl.checkOwnership.return_value=0
        self.assertEqual(0,self.restore()['status']);self.services['ApplicationInstaller'].assert_not_called()
    def test_ambiguous_or_missing_destination_never_starts_worker(self):
        for destination,domain in (('-1',''),('34','new.example'),('0','')):
            self.data.update(DesSite=destination,Domain=domain);self.assertEqual(0,self.restore()['status'])
        self.services['ApplicationInstaller'].assert_not_called()
    def test_paid_new_site_requires_create_permission(self):
        self.data.update(DesSite='-1',Domain='new.example');self.acl.currentContextPermission.return_value=0
        self.assertEqual(0,self.restore()['status']);self.services['ApplicationInstaller'].assert_not_called()
    def test_existing_domain_cannot_be_treated_as_new_site(self):
        self.data.update(DesSite='-1',Domain='existing.example');self.services['Websites'].objects.filter.return_value.exists.return_value=True
        self.assertEqual(0,self.restore()['status']);self.services['ApplicationInstaller'].assert_not_called()
    def test_paid_new_destination_preserves_worker_contract(self):
        self.data.update(DesSite='-1',Domain='new.example')
        self.assertEqual(1,self.restore()['status']);args=self.services['ApplicationInstaller'].call_args.args[1]
        self.assertEqual('new.example',args['Domain']);self.assertEqual('RestoreWPbackupNow',self.services['ApplicationInstaller'].call_args.args[0])
