# -*- coding: utf-8 -*-


from django.test import TestCase, Client, RequestFactory, SimpleTestCase
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.urls import reverse
import json
from types import SimpleNamespace
from datetime import datetime, timedelta
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.models import Administrator
from unittest import mock
import pyotp

# Create your tests here.


class TestLogin(TestCase):

    def setUp(self):
        ## Initiate Client

        self.client = Client()
        self.adminLogin = reverse('adminLogin')
        self.verifyLogin = reverse('verifyLogin')

        ## Create Login User

        response = self.client.get(self.adminLogin)
        self.assertTemplateUsed(response, 'loginSystem/login.html')

    def test_verify_login(self):

        ## Login

        data_ret = {'username': 'admin', 'password': '1234567'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.verifyLogin, json_data, content_type="application/json")
        logging.writeToFile(response.content)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['loginStatus'], 1)

        ## Verify

        response = self.client.get(self.adminLogin)
        self.assertTemplateUsed(response, 'baseTemplate/homePage.html')
        ##logging.writeToFile(result.content)
        self.assertEqual(response.status_code, 200)


class LoginSessionRegressionTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, data, session=None):
        request = self.factory.post(
            '/verifyLogin',
            data=json.dumps(data),
            content_type='application/json',
        )
        request.session = session if session is not None else SessionStore()
        return request

    @staticmethod
    def admin(two_factor=False, secret_key=''):
        return SimpleNamespace(
            pk=7,
            password='stored-password-hash',
            state='ACTIVE',
            twoFA=two_factor,
            secretKey=secret_key,
        )

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_invalid_client_ip_cannot_create_authenticated_session(
        self, administrator_get, unused_password_check
    ):
        from loginSystem.views import verifyLogin
        administrator_get.return_value = self.admin()
        request = self.request({'username': 'admin', 'password': 'valid-password'})
        request.META['HTTP_CF_CONNECTING_IP'] = 'not-an-ip'
        self.assertEqual(0, json.loads(verifyLogin(request).content)['loginStatus'])
        self.assertNotIn('userID', request.session)

    @mock.patch('plogical.CyberCPLogFileWriter.CyberCPLogFileWriter.writeToFile')
    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_mapped_ipv4_session_survives_cloudflare_request(
        self, administrator_get, unused_password_check, unused_log
    ):
        from django.http import HttpResponse
        from loginSystem.views import verifyLogin
        from CyberCP.secMiddleware import secMiddleware
        admin = self.admin()
        admin.securityLevel = secMiddleware.HIGH
        administrator_get.return_value = admin
        request = self.request({'username': 'admin', 'password': 'valid-password'})
        request.META['HTTP_CF_CONNECTING_IP'] = '::ffff:192.0.2.1'
        self.assertEqual(1, json.loads(verifyLogin(request).content)['loginStatus'])
        next_request = self.factory.get('/base/')
        next_request.session = request.session
        next_request.META['HTTP_CF_CONNECTING_IP'] = '::ffff:192.0.2.1'
        middleware = secMiddleware(lambda unused: HttpResponse('dashboard-reached'))
        self.assertEqual(b'dashboard-reached', middleware(next_request).content)
        next_request.META['HTTP_CF_CONNECTING_IP'] = '::ffff:192.0.2.2'
        expired = middleware(next_request)
        self.assertEqual(302, expired.status_code)
        self.assertEqual('/', expired['Location'])
        self.assertNotIn('userID', request.session)

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_password_with_shell_metacharacters_can_authenticate(
        self, administrator_get, unused_password_check
    ):
        from loginSystem.views import verifyLogin
        administrator_get.return_value = self.admin()
        request = self.request({
            'username': 'admin',
            'password': 'safe$word|with;chars&more',
        })

        response = verifyLogin(request)

        self.assertEqual(1, json.loads(response.content)['loginStatus'])
        self.assertEqual(7, request.session['userID'])

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_two_factor_accepts_one_adjacent_time_window(
        self, administrator_get, unused_password_check
    ):
        from loginSystem.views import verifyLogin
        secret_key = pyotp.random_base32()
        administrator_get.return_value = self.admin(True, secret_key)
        session = SessionStore()

        first = verifyLogin(self.request(
            {'username': 'admin', 'password': '1234567'},
            session,
        ))
        self.assertEqual(2, json.loads(first.content)['loginStatus'])

        previous_code = pyotp.TOTP(secret_key).at(
            datetime.now() - timedelta(seconds=30)
        )
        request = self.request({
            'username': 'admin',
            'password': '1234567',
            'twofa': previous_code,
        }, session)
        second = verifyLogin(request)

        self.assertEqual(1, json.loads(second.content)['loginStatus'])
        self.assertEqual(7, request.session['userID'])
