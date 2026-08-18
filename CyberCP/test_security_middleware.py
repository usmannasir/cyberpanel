import unittest
import json

from django.http import HttpResponse
from django.test import RequestFactory

from CyberCP.secMiddleware import secMiddleware


class SecurityMiddlewareTests(unittest.TestCase):

    def test_content_security_policy_is_emitted_as_one_complete_header(self):
        request = RequestFactory().get('/')
        request.session = {}
        response = secMiddleware(lambda unused_request: HttpResponse('ok'))(request)
        policy = response['Content-Security-Policy']

        self.assertIn("default-src 'self'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertIn('connect-src *', policy)
        self.assertIn("object-src 'none'", policy)
        self.assertIn("base-uri 'self'", policy)
        self.assertIn("frame-ancestors 'self'", policy)

    def test_login_password_allows_common_special_characters(self):
        request = RequestFactory().post(
            '/verifyLogin',
            data=json.dumps({
                'username': 'admin',
                'password': "valid$pass|with;special&chars",
            }),
            content_type='application/json',
        )
        request.session = {}

        response = secMiddleware(
            lambda unused_request: HttpResponse('login-view-reached')
        )(request)

        self.assertEqual(b'login-view-reached', response.content)

    def test_login_username_keeps_command_character_validation(self):
        request = RequestFactory().post(
            '/verifyLogin',
            data=json.dumps({
                'username': 'admin;touch /tmp/example',
                'password': 'valid-password',
            }),
            content_type='application/json',
        )
        request.session = {}

        response = secMiddleware(
            lambda unused_request: HttpResponse('login-view-reached')
        )(request)

        self.assertNotEqual(b'login-view-reached', response.content)
        self.assertIn(b'potentially dangerous characters', response.content)
