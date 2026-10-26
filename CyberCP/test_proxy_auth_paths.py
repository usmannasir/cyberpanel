import json
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase
from CyberCP.sessionSecurity import session_ip_key
from plogical.securityUtils import generate_api_token
from loginSystem.views import verifyLogin
from api.views import loginAPI
from cloudAPI.views import access
from databases.phpmyadmin_session import panel_ip_allowed


class ProxyAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.admin=SimpleNamespace(pk=7,userName='proxy-test',password='stored-hash',state='ACTIVE',api=1,twoFA=False,secretKey='',token=generate_api_token())
        self.factory=RequestFactory()

    def invoke(self, kind, peer, header):
        if kind == 'panel':
            request=self.factory.post('/verifyLogin',json.dumps({'username':'proxy-test','password':'test'}),content_type='application/json',REMOTE_ADDR=peer,HTTP_CF_CONNECTING_IP=header)
            view=verifyLogin
        elif kind == 'api':
            request=self.factory.post('/api/loginAPI',{'username':'proxy-test','password':'test'},REMOTE_ADDR=peer,HTTP_CF_CONNECTING_IP=header)
            view=loginAPI
        else:
            request=self.factory.get('/cloudAPI/access',{'serverUserName':'proxy-test','token':self.admin.token,'redirect':'/websites/'},REMOTE_ADDR=peer,HTTP_CF_CONNECTING_IP=header)
            view=access
        request.session=SessionStore()
        with patch('loginSystem.models.Administrator.objects.get',return_value=self.admin),patch('plogical.hashPassword.check_password',return_value=True):
            response=view(request)
        return request,response

    def test_all_session_creators_ignore_direct_forged_cloudflare_header(self):
        for kind in ('panel','api','cloud'):
            request,response=self.invoke(kind,'203.0.113.8','192.0.2.9')
            self.assertEqual(7,request.session.get('userID'),(kind,response.content))
            self.assertEqual('203.0.113.8',request.session.get('ipAddr'))

    def test_all_session_creators_share_canonical_trusted_ipv6(self):
        for kind in ('panel','api','cloud'):
            request,response=self.invoke(kind,'173.245.48.10','2001:db8:0:1234::1')
            self.assertEqual(7,request.session.get('userID'),(kind,response.content))
            self.assertEqual('2001:db8::/48',request.session.get('ipAddr'))
            self.assertTrue(panel_ip_allowed(request.session,'2001:db8::9',0))
            self.assertFalse(panel_ip_allowed(request.session,'2001:db8:1::9',0))

    def test_invalid_trusted_client_cannot_create_any_session(self):
        for kind in ('panel','api','cloud'):
            request,response=self.invoke(kind,'173.245.48.10','bad-ip')
            self.assertNotIn('userID',request.session)

    def test_pma_mapped_ipv4_and_safe_legacy_prefix(self):
        self.assertTrue(panel_ip_allowed({'ipAddr':'192.0.2.8'},'::ffff:192.0.2.8',0))
        self.assertFalse(panel_ip_allowed({'ipAddr':'::ffff'},'::ffff:192.0.2.8',0))
        self.assertTrue(panel_ip_allowed({'ipAddr':'2001:db8:0'},'2001:db8::8',0))
        self.assertFalse(panel_ip_allowed({'ipAddr':'2001::'},'2001:db8::8',0))
