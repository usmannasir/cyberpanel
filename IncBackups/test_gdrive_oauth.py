"""No external Google account or customer repository is used by these tests."""
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.template import Context, Engine
from IncBackups import gdrive_oauth as flow


class Session(dict):
    session_key = 'synthetic-panel-session'
    modified = False
    def save(self):
        pass


@override_settings(
    GDRIVE_HANDOFF_ENABLED=True,
    GDRIVE_PLATFORM_BASE_URL='https://platform.example.test',
    GDRIVE_HANDOFF_REGISTRATION_KEY='synthetic-gdrive-installation-key-20261015',
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class HandoffTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.session = Session(userID=7)
        self.expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self.access = mock.patch.object(flow, '_check_access', return_value=None)
        self.access.start()
        self.addCleanup(self.access.stop)
        self.capability = mock.patch.object(flow, 'capability', return_value=(True, ''))
        self.capability_mock = self.capability.start()
        self.addCleanup(self.capability.stop)

    def request(self, method, data=None):
        if method == 'POST':
            req = self.factory.post('/IncrementalBackups/ConfigureV2BackupSetup',
                                    json.dumps(data or {}), content_type='application/json',
                                    HTTP_HOST='panel.example.test:8090', HTTP_ORIGIN='https://panel.example.test:8090', secure=True)
        else:
            req = self.factory.get('/IncrementalBackups/ConfigureV2BackupSetup', data or {},
                                   HTTP_HOST='panel.example.test:8090', secure=True)
        req.session = self.session
        req._dont_enforce_csrf_checks = True
        return req

    def start(self):
        body = {'Selectedwebsite': 'owned.example', 'accountName': 'qa-drive',
                'client_id': 'synthetic.apps.googleusercontent.com',
                'client_secret': 'SYNTHETIC-CLIENT-SECRET'}
        response = mock.Mock(status_code=200)
        response.json.return_value = {'status': 1, 'authorization_url':
                                     'https://platform.example.test/gDrive/v2/start?handoff='+'a'*43}
        with mock.patch.object(flow.requests, 'post', return_value=response) as post:
            result = flow.begin(self.request('POST', body))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(json.loads(result.content)['status'], 1)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['client_secret'], body['client_secret'])
        self.assertNotIn(body['client_secret'], post.call_args.args[0])
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertEqual(post.call_args.kwargs['headers']['X-GDrive-Installation-Key'],
                         'synthetic-gdrive-installation-key-20261015')
        self.assertNotIn('verifier', payload)
        self.assertNotIn('SYNTHETIC', result.content.decode())
        return next(iter(self.session[flow.SESSION_KEY])), payload

    def credentials(self):
        return {'token': 'SYNTHETIC-ACCESS', 'refresh_token': 'SYNTHETIC-REFRESH',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'scopes': ['https://www.googleapis.com/auth/drive.file'],
                'client_id': 'synthetic.apps.googleusercontent.com',
                'client_secret': 'SYNTHETIC-CLIENT-SECRET', 'expiry': self.expiry}

    def test_begin_sends_secrets_only_in_https_post_body(self):
        _, payload = self.start()
        self.assertEqual(len(payload['challenge']), 43)

    def test_return_get_does_not_redeem_or_configure(self):
        state, _ = self.start()
        with mock.patch.object(flow.requests, 'post') as network, \
                mock.patch.object(flow, '_install_backend') as install:
            result = flow.complete(self.request('GET', {'state': state, 'code': 'c'*43}))
        self.assertEqual(result.status_code, 200)
        self.assertIn('csrfmiddlewaretoken', result.content.decode())
        self.assertEqual(result['Referrer-Policy'], 'strict-origin')
        self.assertIn("form-action 'self'", result['Content-Security-Policy'])
        network.assert_not_called()
        install.assert_not_called()

    def test_complete_verifies_metadata_and_consumes_once(self):
        state, payload = self.start()
        response = mock.Mock(status_code=200)
        response.json.return_value = {'status': 1, 'credentials': self.credentials(),
                                     'account': 'qa-drive', 'domain': 'owned.example', 'state': state, 'flow_type': 'v2'}
        with mock.patch.object(flow.requests, 'post', return_value=response) as post, \
                mock.patch.object(flow, '_install_backend') as install:
            result = flow.complete(self.request('POST', {'state': state, 'code': 'c'*43}))
            again = flow.complete(self.request('POST', {'state': state, 'code': 'c'*43}))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(again.status_code, 400)
        install.assert_called_once_with('owned.example', 'qa-drive', self.credentials())
        self.assertEqual(post.call_args.kwargs['json']['callback'], payload['callback'])
        self.assertNotIn('SYNTHETIC', result.content.decode())

    def test_legacy_query_secrets_fail_without_reflection_or_network(self):
        with mock.patch.object(flow.requests, 'post') as network:
            result = flow.complete(self.request('GET', {'t': 'DO-NOT-REFLECT',
                                                       'client_secret': 'DO-NOT-REFLECT'}))
        self.assertEqual(result.status_code, 400)
        self.assertNotIn('DO-NOT-REFLECT', result.content.decode())
        network.assert_not_called()

    def test_switched_user_session_and_expiry_fail_before_redeem(self):
        for kind in ('user', 'session', 'expired'):
            with self.subTest(kind=kind):
                self.session = Session(userID=7)
                state, _ = self.start()
                if kind == 'user': self.session['userID'] = 8
                if kind == 'session': self.session.session_key = 'different-session'
                if kind == 'expired': self.session[flow.SESSION_KEY][state]['created'] -= 301
                with mock.patch.object(flow.requests, 'post') as network:
                    result = flow.complete(self.request('POST', {'state': state, 'code': 'c'*43}))
                self.assertEqual(result.status_code, 400)
                network.assert_not_called()

    def test_tampered_metadata_and_invalid_credentials_do_not_write(self):
        for field, value in [('domain', 'someone-else.example'), ('account', 'other'),
                             ('state', 'other'), ('credentials', {'token': 'bad'})]:
            with self.subTest(field=field):
                self.session = Session(userID=7)
                state, _ = self.start()
                data = {'status': 1, 'credentials': self.credentials(),
                        'account': 'qa-drive', 'domain': 'owned.example', 'state': state, 'flow_type': 'v2'}
                data[field] = value
                response = mock.Mock(status_code=200)
                response.json.return_value = data
                with mock.patch.object(flow.requests, 'post', return_value=response), \
                        mock.patch.object(flow, '_install_backend') as install:
                    result = flow.complete(self.request('POST', {'state': state, 'code': 'c'*43}))
                self.assertEqual(result.status_code, 400)
                install.assert_not_called()

    def test_registration_network_failure_never_reflects_exception(self):
        with mock.patch.object(flow.requests, 'post', side_effect=RuntimeError('SECRET-QUERY')), \
                mock.patch.object(flow, '_install_backend') as install:
            result = flow.begin(self.request('POST', {'Selectedwebsite':'owned.example',
                                'accountName':'qa-drive', 'client_id':'x.apps.googleusercontent.com',
                                'client_secret':'SYNTHETIC'}))
        self.assertEqual(result.status_code, 502)
        self.assertNotIn('SECRET-QUERY', result.content.decode())
        install.assert_not_called()

    def test_callback_owner_permission_and_entitlement_rechecked(self):
        state, _ = self.start()
        with mock.patch.object(flow, '_check_access', side_effect=flow.AccessDenied), \
                mock.patch.object(flow.requests, 'post') as network:
            result = flow.complete(self.request('POST', {'state':state,'code':'c'*43}))
        self.assertEqual(result.status_code, 403)
        network.assert_not_called()

    def test_begin_denies_before_any_registration_or_write(self):
        with mock.patch.object(flow, '_check_access', side_effect=flow.AccessDenied), \
                mock.patch.object(flow.requests, 'post') as network, \
                mock.patch.object(flow, '_install_backend') as install:
            result = flow.begin(self.request('POST', {'Selectedwebsite':'owned.example',
                                'accountName':'qa-drive', 'client_id':'x.apps.googleusercontent.com',
                                'client_secret':'SYNTHETIC'}))
        self.assertEqual(result.status_code, 403)
        network.assert_not_called()
        install.assert_not_called()
        self.capability_mock.assert_not_called()

    def test_platform_capability_disabled_never_registers(self):
        self.capability_mock.return_value=(False,'Secure enrollment unavailable')
        with mock.patch.object(flow.requests,'post') as network:
            result=flow.begin(self.request('POST',{'Selectedwebsite':'owned.example','accountName':'qa',
                'client_id':'a.apps.googleusercontent.com','client_secret':'SYNTHETIC'}))
        self.assertEqual(result.status_code,503)
        network.assert_not_called()

    @override_settings(GDRIVE_HANDOFF_ENABLED=False)
    def test_disabled_feature_fails_closed(self):
        with mock.patch.object(flow.requests, 'post') as network:
            self.assertEqual(flow.begin(self.request('POST')).status_code, 503)
            self.assertEqual(flow.complete(self.request('GET')).status_code, 503)
        network.assert_not_called()

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
    def test_cookie_session_must_not_hold_pkce_secret(self):
        self.assertEqual(flow.begin(self.request('POST')).status_code, 503)

    def test_get_begin_not_allowed(self):
        self.assertEqual(flow.begin(self.request('GET')).status_code, 405)
        self.capability_mock.assert_not_called()

    def test_pending_limit_rejects_before_registration(self):
        import time
        self.session[flow.SESSION_KEY]={str(i):{'created':time.time()} for i in range(4)}
        with mock.patch.object(flow.requests,'post') as network:
            result=flow.begin(self.request('POST',{'Selectedwebsite':'owned.example','accountName':'qa',
                'client_id':'a.apps.googleusercontent.com','client_secret':'SYNTHETIC'}))
        self.assertEqual(result.status_code,429)
        network.assert_not_called()

    def test_real_configuration_template_loads_versioned_controller(self):
        root = Path(__file__).resolve().parents[1]
        engine = Engine(dirs=[str(root/'baseTemplate/templates'), str(root/'IncBackups/templates')],
                        libraries={'i18n':'django.templatetags.i18n', 'static':'django.templatetags.static'})
        with mock.patch('django.urls.reverse', return_value='/navigation/'):
            html = engine.get_template('IncBackups/ConfigureV2Backup.html').render(Context(
                {'BackupStat':1,'websiteList':['owned.example'],'CP_VERSION':'qa-test'}))
        self.assertIn('IncBackups/IncBackups.js', html)
        self.assertIn('gdrive-public-1', html)
        self.assertIn('type="password" autocomplete="off"', html)

    def test_duplicate_return_fields_rejected(self):
        state, _ = self.start()
        request = self.factory.get('/IncrementalBackups/ConfigureV2BackupSetup?state='+state+'&state='+state+'&code='+'c'*43,
                                   HTTP_HOST='panel.example.test:8090', secure=True)
        request.session = self.session
        with mock.patch.object(flow.requests, 'post') as network:
            self.assertEqual(flow.complete(request).status_code, 400)
        network.assert_not_called()

    def test_csrf_required_for_both_post_endpoints(self):
        for function in (flow.begin, flow.complete):
            request = self.request('POST', {})
            request._dont_enforce_csrf_checks = False
            with self.subTest(function=function.__name__):
                result = function(request)
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result['Cache-Control'], 'no-store')

    def test_null_origin_is_not_trusted(self):
        request = self.request('POST', {})
        request._dont_enforce_csrf_checks = False
        request.META['HTTP_ORIGIN'] = 'null'
        self.assertEqual(flow.begin(request).status_code, 403)


class AccessTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(pk=7)
        self.admin = mock.Mock()
        self.admin.objects.get.return_value = self.user
        self.acl = mock.Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnership.return_value = 1
        self.acl.CheckForPremFeature.return_value = 1
        self.modules = mock.patch.dict(sys.modules, {
            'loginSystem.models': SimpleNamespace(Administrator=self.admin),
            'plogical.acl': SimpleNamespace(ACLManager=self.acl)})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.request = SimpleNamespace(session={'userID':7})

    def test_permission_ownership_and_entitlement_required(self):
        flow._check_access(self.request, 'owned.example')
        self.acl.checkOwnership.assert_called_once_with('owned.example', self.user, self.acl.loadedACL.return_value)
        for attribute in ('currentContextPermission', 'checkOwnership', 'CheckForPremFeature'):
            with self.subTest(attribute=attribute):
                getattr(self.acl, attribute).return_value = 0
                with self.assertRaises(flow.AccessDenied):
                    flow._check_access(self.request, 'owned.example')
                getattr(self.acl, attribute).return_value = 1

    def test_unauthenticated_and_boolean_identity_rejected(self):
        for value in (None, True, '7'):
            self.request.session['userID'] = value
            with self.assertRaises(flow.AccessDenied):
                flow._check_access(self.request, 'owned.example')
        self.admin.objects.get.assert_not_called()

    def test_truthy_noninteger_entitlement_rejected(self):
        self.acl.CheckForPremFeature.return_value = True
        with self.assertRaises(flow.AccessDenied):
            flow._check_access(self.request, 'owned.example')

    def test_status_v2_checks_entitlement_without_website_ownership(self):
        flow._check_access(self.request,None,'v2',status_only=True)
        self.acl.checkOwnership.assert_not_called()
        self.acl.CheckForPremFeature.return_value=0
        with self.assertRaises(flow.AccessDenied):
            flow._check_access(self.request,None,'v2',status_only=True)


@override_settings(GDRIVE_HANDOFF_ENABLED=True, GDRIVE_HANDOFF_PUBLIC=True,
                   GDRIVE_PLATFORM_BASE_URL='https://platform.cyberpersons.com',
                   GDRIVE_HANDOFF_REGISTRATION_KEY='',
                   SESSION_ENGINE='django.contrib.sessions.backends.db')
class PublicAdmissionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.session = Session(userID=7)
        self.good = {'status':1, 'protocol':'gdrive-handoff', 'version':2, 'enabled':True,
            'admission':'public', 'flows':['normal','v2'], 'register_path':'/gDrive/register',
            'redeem_path':'/gDrive/redeem', 'start_path':'/gDrive/v2/start',
            'callback_path':'/gDrive/v2/callback'}

    request = HandoffTests.request

    def test_requires_explicit_public_admission_and_exact_protocol(self):
        for mode in ('normal','v2'):
            response = mock.Mock(status_code=200)
            for update, expected in (({}, True), ({'admission':'registered'}, False),
                                     ({'admission':None}, False), ({'admission':True}, False),
                                     ({'version':1}, False), ({'enabled':False}, False),
                                     ({'register_path':'https://attacker.example'}, False)):
                response.json.return_value = dict(self.good, **update)
                with self.subTest(mode=mode, update=update), mock.patch.object(flow.requests,'get',return_value=response):
                    self.assertEqual(flow.capability(mode)[0], expected)
            response.json.return_value = {k:v for k,v in self.good.items() if k != 'admission'}
            with mock.patch.object(flow.requests,'get',return_value=response):
                self.assertFalse(flow.capability(mode)[0])

    def test_empty_key_requires_explicit_public_mode_and_fixed_platform(self):
        self.assertEqual(flow._registration_headers(flow.PUBLIC_PLATFORM), {})
        for overrides in ({'GDRIVE_HANDOFF_PUBLIC':False}, {'GDRIVE_HANDOFF_PUBLIC':'true'},
                          {'GDRIVE_HANDOFF_REGISTRATION_KEY':'invalid'}):
            with override_settings(**overrides), self.assertRaises(ValueError):
                flow._registration_headers(flow.PUBLIC_PLATFORM)
        with self.assertRaises(ValueError):
            flow._registration_headers('https://attacker.example')
        with override_settings(GDRIVE_HANDOFF_REGISTRATION_KEY='x'*43):
            self.assertEqual(flow._registration_headers(flow.PUBLIC_PLATFORM),
                             {'X-GDrive-Installation-Key':'x'*43})

    def test_both_public_flows_remain_session_bound_and_save_once(self):
        expiry = (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        creds = {'token':'SYNTHETIC','refresh_token':'SYNTHETIC-REFRESH',
                 'token_uri':'https://oauth2.googleapis.com/token', 'scopes':[flow.SCOPE],
                 'client_id':'synthetic.apps.googleusercontent.com','client_secret':'SYNTHETIC',
                 'expiry':expiry}
        available = mock.Mock(status_code=200)
        available.json.return_value = self.good
        registered = mock.Mock(status_code=200)
        registered.json.return_value = {'status':1,'authorization_url':flow.PUBLIC_PLATFORM+
                                        '/gDrive/v2/start?handoff='+'a'*43}
        for mode in ('normal','v2'):
            self.session = Session(userID=7)
            with self.subTest(mode=mode), mock.patch.object(flow, '_check_access') as access, \
                    mock.patch.object(flow.requests,'get',return_value=available), \
                    mock.patch.object(flow.requests,'post',return_value=registered) as post:
                response = flow.begin(self.request('POST', {'Selectedwebsite':'owned.example',
                    'accountName':'public-qa','client_id':'synthetic.apps.googleusercontent.com',
                    'client_secret':'SYNTHETIC'}),mode=mode)
            self.assertEqual(response.status_code,200)
            self.assertEqual(post.call_args.kwargs['headers'],{})
            self.assertFalse(post.call_args.kwargs['allow_redirects'])
            access.assert_called_once_with(mock.ANY, 'owned.example' if mode=='v2' else flow.NORMAL_DOMAIN, mode)
            state = next(iter(self.session[flow.SESSION_KEY]))
            saved = self.session[flow.SESSION_KEY][state]
            with mock.patch.object(flow, '_check_access'), mock.patch.object(flow.requests,'post') as post:
                req = self.request('GET',{'state':state,'code':'c'*43});req.path=flow.CALLBACKS[mode]
                self.assertEqual(flow.complete(req,mode=mode).status_code,200)
                post.assert_not_called()
            redeemed = mock.Mock(status_code=200)
            redeemed.json.return_value = {'status':1, 'credentials':creds, 'account':'public-qa',
                'domain':saved['website'], 'state':state,'flow_type':mode}
            installer = '_install_backend' if mode=='v2' else '_install_normal'
            with mock.patch.object(flow, '_check_access'), \
                    mock.patch.object(flow.requests,'post',return_value=redeemed), \
                    mock.patch.object(flow,installer) as install:
                req=self.request('POST',{'state':state,'code':'c'*43});req.path=flow.CALLBACKS[mode]
                self.assertEqual(flow.complete(req,mode=mode).status_code,200)
                self.assertEqual(flow.complete(req,mode=mode).status_code,400)
                install.assert_called_once()

    def test_public_does_not_bypass_csrf_or_access_checks(self):
        body={'Selectedwebsite':'owned.example','accountName':'public-qa',
              'client_id':'synthetic.apps.googleusercontent.com','client_secret':'SYNTHETIC'}
        for mode in ('normal','v2'):
            with self.subTest(mode=mode), mock.patch.object(flow.requests,'post') as post, \
                    mock.patch.object(flow,'_check_access',side_effect=flow.AccessDenied):
                self.assertEqual(flow.begin(self.request('POST',body),mode=mode).status_code,403)
                post.assert_not_called()
            req=self.request('POST',body);req._dont_enforce_csrf_checks=False
            with mock.patch.object(flow.requests,'post') as post:
                self.assertEqual(flow.begin(req,mode=mode).status_code,403)
                post.assert_not_called()
