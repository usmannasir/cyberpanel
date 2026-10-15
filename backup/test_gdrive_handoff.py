"""Synthetic-only normal backup handoff and preservation regression tests."""
import json
import sys
from types import SimpleNamespace
from unittest import mock
from django.db import connection, models
from django.test import TransactionTestCase
from IncBackups import test_gdrive_oauth as base_tests
from IncBackups import gdrive_oauth as flow


class NormalHandoffTests(base_tests.HandoffTests):
    def start_normal(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {'status':1, 'authorization_url':
            'https://platform.example.test/gDrive/v2/start?handoff='+'a'*43}
        with mock.patch.object(flow.requests, 'post', return_value=response) as post:
            result = flow.begin(self.request('POST', {'accountName':'new-account',
                'client_id':'synthetic.apps.googleusercontent.com','client_secret':'SYNTHETIC'}), mode='normal')
        self.assertEqual(result.status_code, 200)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['callback'],'https://panel.example.test:8090/backup/gDriveSetup')
        self.assertEqual(payload['domain'],flow.NORMAL_DOMAIN)
        self.assertEqual(payload['flow_type'],'normal')
        return payload['state']

    def test_normal_save_and_replay(self):
        state = self.start_normal()
        response = mock.Mock(status_code=200)
        response.json.return_value = {'status':1,'state':state,'flow_type':'normal',
            'domain':flow.NORMAL_DOMAIN,'account':'new-account','credentials':self.credentials()}
        request = self.request('POST',{'state':state,'code':'c'*43})
        request.path = '/backup/gDriveSetup'
        with mock.patch.object(flow.requests,'post',return_value=response), \
                mock.patch.object(flow,'_install_normal') as install:
            self.assertEqual(flow.complete(request, mode='normal').status_code,200)
            self.assertEqual(flow.complete(request, mode='normal').status_code,400)
        install.assert_called_once_with(7,'new-account',self.credentials())

    def test_normal_state_cannot_be_used_as_v2(self):
        state = self.start_normal()
        with mock.patch.object(flow.requests,'post') as network:
            self.assertEqual(flow.complete(self.request('POST',{'state':state,'code':'c'*43})).status_code,400)
        network.assert_not_called()

    def test_legacy_raw_callback_never_saves(self):
        with mock.patch.object(flow,'_install_normal') as install:
            self.assertEqual(flow.complete(self.request('GET',{'t':'SYNTHETIC','r':'SYNTHETIC'}),mode='normal').status_code,400)
        install.assert_not_called()

    def test_old_django_origin_guard(self):
        for origin in (None,'null','https://attacker.example'):
            req=self.request('POST',{'accountName':'new-account','client_id':'a.apps.googleusercontent.com','client_secret':'SYNTHETIC'})
            if origin is None: req.META.pop('HTTP_ORIGIN',None)
            else: req.META['HTTP_ORIGIN']=origin
            with mock.patch.object(flow.requests,'post') as network:
                self.assertEqual(flow.begin(req,mode='normal').status_code,400)
            network.assert_not_called()

    def test_normal_name_limit(self):
        with mock.patch.object(flow.requests,'post') as network:
            result=flow.begin(self.request('POST',{'accountName':'a'*51,
                'client_id':'a.apps.googleusercontent.com','client_secret':'SYNTHETIC'}),mode='normal')
        self.assertEqual(result.status_code,400)
        network.assert_not_called()

    def test_redeem_flow_type_confusion_never_saves(self):
        state=self.start_normal()
        response=mock.Mock(status_code=200)
        response.json.return_value={'status':1,'state':state,'flow_type':'v2',
            'domain':flow.NORMAL_DOMAIN,'account':'new-account','credentials':self.credentials()}
        with mock.patch.object(flow.requests,'post',return_value=response),mock.patch.object(flow,'_install_normal') as install:
            self.assertEqual(flow.complete(self.request('POST',{'state':state,'code':'c'*43}),mode='normal').status_code,400)
        install.assert_not_called()


class CapabilityTests(base_tests.HandoffTests):
    def test_capability_checks_fixed_version_paths_and_modes(self):
        self.capability.stop()
        good={'status':1,'protocol':'gdrive-handoff','version':2,'enabled':True,
              'flows':['normal','v2'],'register_path':'/gDrive/register','redeem_path':'/gDrive/redeem',
              'start_path':'/gDrive/v2/start','callback_path':'/gDrive/v2/callback'}
        response=mock.Mock(status_code=200)
        response.json.return_value=good
        with mock.patch.object(flow.requests,'get',return_value=response) as network:
            self.assertEqual(flow.capability('normal'),(True,''))
        self.assertEqual(network.call_args.args[0],'https://platform.example.test/gDrive/capabilities')
        self.assertFalse(network.call_args.kwargs['allow_redirects'])
        for field,value in [('version',1),('enabled',False),('flows',['v2']),('start_path','/gDrive'),('protocol','other')]:
            response.json.return_value=dict(good,**{field:value})
            with mock.patch.object(flow.requests,'get',return_value=response):
                self.assertFalse(flow.capability('normal')[0])

    def test_capability_unknown_or_unavailable_fails_closed(self):
        self.capability.stop()
        with mock.patch.object(flow.requests,'get',side_effect=RuntimeError('SYNTHETIC-SECRET')):
            enabled,reason=flow.capability('normal')
        self.assertFalse(enabled)
        self.assertNotIn('SYNTHETIC',reason)


class NormalAccessTests(base_tests.AccessTests):
    def test_normal_not_paid_and_no_website_required(self):
        self.acl.CheckForPremFeature.return_value=0
        flow._check_access(self.request,None,'normal')
        self.acl.CheckForPremFeature.assert_not_called()
        self.acl.checkOwnership.assert_not_called()
        self.acl.currentContextPermission.return_value=0
        with self.assertRaises(flow.AccessDenied): flow._check_access(self.request,None,'normal')


class FixtureDrive(models.Model):
    owner_id=models.IntegerField()
    name=models.CharField(max_length=50,unique=True)
    auth=models.TextField()
    runTime=models.CharField(max_length=20,default='NEVER')
    class Meta:
        app_label='qa_handoff'
        db_table='qa_normal_drive_fixture'


class NormalPersistenceTests(TransactionTestCase):
    def setUp(self):
        with connection.schema_editor() as editor: editor.create_model(FixtureDrive)
        self.modules=mock.patch.dict(sys.modules,{'websiteFunctions.models':SimpleNamespace(GDrive=FixtureDrive)})
        self.modules.start()

    def tearDown(self):
        self.modules.stop()
        with connection.schema_editor() as editor: editor.delete_model(FixtureDrive)

    def test_insert_only_preserves_existing_and_runtime(self):
        old=FixtureDrive.objects.create(owner_id=8,name='existing',auth='EXACT-OLD-BYTES',runTime='Daily')
        credentials={'token':'SYNTHETIC','client_id':'synthetic.apps.googleusercontent.com','client_secret':'SYNTHETIC'}
        flow._install_normal(7,'new-account',credentials)
        added=FixtureDrive.objects.get(name='new-account')
        self.assertEqual(added.owner_id,7)
        self.assertEqual(added.runTime,'NEVER')
        self.assertEqual(json.loads(added.auth),dict(credentials,handoff_version=2))
        with self.assertRaises(Exception): flow._install_normal(7,'existing',credentials)
        old.refresh_from_db()
        self.assertEqual((old.owner_id,old.auth,old.runTime),(8,'EXACT-OLD-BYTES','Daily'))
        self.assertEqual(FixtureDrive.objects.count(),2)
