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

    def test_database_password_allows_special_characters_on_account_endpoints(self):
        for path in (
            '/dataBases/submitDBCreation',
            '/dataBases/changePassword',
        ):
            request = RequestFactory().post(
                path,
                data=json.dumps({
                    'dbUserName': 'site_user',
                    'dbPassword': "valid $pass|with;'special&chars",
                }),
                content_type='application/json',
            )
            request.session = {'userID': 1}

            response = secMiddleware(
                lambda unused_request: HttpResponse('database-view-reached')
            )(request)

            self.assertEqual(b'database-view-reached', response.content)

    def test_database_password_exemption_does_not_cover_other_fields(self):
        request = RequestFactory().post(
            '/dataBases/submitDBCreation',
            data=json.dumps({
                'dbName': 'site;DROP_DATABASE',
                'dbPassword': 'valid$password',
            }),
            content_type='application/json',
        )
        request.session = {'userID': 1}

        response = secMiddleware(
            lambda unused_request: HttpResponse('database-view-reached')
        )(request)

        self.assertNotEqual(b'database-view-reached', response.content)

    def firewall_request(self, path, fields):
        request = RequestFactory().post(path, data=json.dumps(fields),
                                        content_type='application/json')
        request.session = {'userID': 1}
        return secMiddleware(lambda unused: HttpResponse('firewall-view-reached'))(request)

    def test_firewall_source_fields_allow_valid_ipv4_and_ipv6(self):
        for path in ('/firewall/addRule', '/firewall/deleteRule'):
            for address in ('192.0.2.44/32', '2001:db8::/64',
                            '2001:db8:1234:5678:90ab:cdef:1234:5678/128'):
                with self.subTest(path=path, address=address):
                    response = self.firewall_request(path, {'ruleIP':address})
                    self.assertEqual(response.content,b'firewall-view-reached')
                    self.assertEqual(response['X-Content-Type-Options'],'nosniff')

    def test_firewall_source_validation_rejects_metacharacters_and_invalid_types(self):
        for address in ('2001:db8::1;id','2001:db8::1|id','$(id)',
                        '2001:db8::1\\n','fe80::1%eth0','[2001:db8::1]',
                        '2001:db8::1/129','foo:bar', None, 0, ['2001:db8::1']):
            with self.subTest(address=address):
                response = self.firewall_request('/firewall/addRule',{'ruleIP':address})
                self.assertNotEqual(response.content,b'firewall-view-reached')
                self.assertIn(b'valid IPv4 or IPv6',response.content)

    def test_firewall_source_allowance_does_not_cover_other_fields_or_routes(self):
        cases = [
            ('/firewall/addRule',{'ruleName':'qa:bad','ruleIP':'2001:db8::1'}),
            ('/firewall/addRule',{'rulePort':'15433;id','ruleIP':'2001:db8::1'}),
            ('/firewall/addRule',{'ruleProtocol':'tcp;id','ruleIP':'2001:db8::1'}),
            ('/firewall/other',{'ruleIP':'2001:db8::1'}),
            ('/firewall/addRuleExtra',{'ruleIP':'2001:db8::1'}),
        ]
        for path, fields in cases:
            with self.subTest(path=path, fields=fields):
                self.assertNotEqual(self.firewall_request(path,fields).content,
                                    b'firewall-view-reached')
