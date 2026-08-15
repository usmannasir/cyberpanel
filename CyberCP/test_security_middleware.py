import unittest

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
