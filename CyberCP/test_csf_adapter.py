"""No firewall commands: real Django CSRF and middleware boundary tests."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from CyberCP import csfAdapter as adapter


@csrf_exempt
def plugin_view(request):
    if request.method == 'POST':
        plugin_view.calls.append(request.POST.copy())
    return HttpResponse('<form action="/configservercsf/iframe/" method="post">'
                        '<input name="action" value="saveconf">'
                        '<input name="TCP_IN" value="22,80,443">'
                        '<button>Save</button></form>')


plugin_view.__module__ = 'configservercsf.views'
plugin_view.__name__ = 'configservercsfiframe'
plugin_view.calls = []
urlpatterns = [path('configservercsf/iframe/', plugin_view)]


@override_settings(ALLOWED_HOSTS=['testserver'], ROOT_URLCONF=__name__)
class AdapterTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = patch.object(adapter, '_is_admin', return_value=True)
        self.admin.start()
        self.addCleanup(self.admin.stop)

    def request(self, method='get', data=None, path=adapter.PATH, **extra):
        request = getattr(self.factory, method)(path, data=data or {}, **extra)
        request.session = {'userID': 1}
        return request

    def test_exact_registered_route_only(self):
        for url in ('/other/configservercsf/iframe/', '/configservercsf/iframe', '/configservercsf/other/'):
            self.assertEqual(adapter.validate_request(self.request(path=url)), (False, None))
        with patch.object(adapter, '_registered_view', return_value=False):
            active, response = adapter.validate_request(self.request())
        self.assertFalse(active)
        self.assertEqual(response.status_code, 403)

    def test_non_admin_denied_before_confirmation_or_plugin(self):
        with patch.object(adapter, '_is_admin', return_value=False):
            for method in ('get', 'post'):
                active, response = adapter.validate_request(self.request(method, {'action': 'stop'}))
                self.assertFalse(active)
                self.assertEqual(response.status_code, 403)

    def test_mutation_get_gets_escaped_confirmation_only(self):
        request = self.request(data={'action': 'stop', 'comment': '\"><script>alert(1)</script>'})
        active, response = adapter.validate_request(request)
        self.assertFalse(active)
        self.assertIn(b'Confirm and continue', response.content)
        self.assertIn(b'csrfmiddlewaretoken', response.content)
        self.assertNotIn(b'<script>alert', response.content)
        self.assertIn('no-store', response['Cache-Control'])

    def test_readonly_get_rejects_extra_and_duplicate_parameters(self):
        for action in adapter.READ_ONLY_ACTIONS:
            self.assertEqual(adapter.validate_request(self.request(data={'action': action})), (True, None))
            active, response = adapter.validate_request(self.request(data={'action': [action, 'stop']}))
            self.assertFalse(active)
            self.assertIn(b'Confirm and continue', response.content)
        active, response = adapter.validate_request(self.request(data={'action': 'status', 'do': 'stop'}))
        self.assertFalse(active)

    def test_missing_and_wrong_csrf_tokens_rejected(self):
        for token in ('', 'a' * 64):
            request = self.request('post', {'action': 'saveconf', 'csrfmiddlewaretoken': token})
            request.COOKIES['csrftoken'] = 'b' * 32
            request.csrf_processing_done = True
            request._dont_enforce_csrf_checks = True
            active, response = adapter.validate_request(request)
            self.assertFalse(active)
            self.assertEqual(response.status_code, 403)

    def test_valid_csrf_and_origin_required(self):
        seed = self.request()
        token = get_token(seed)
        for origin, allowed in (('https://testserver', True), ('https://other.example', False)):
            request = self.request('post', {'action': 'saveconf', 'csrfmiddlewaretoken': token,
                                           'content': "# allow\nTCP_IN = '22,80:90';"},
                                   secure=True, HTTP_ORIGIN=origin)
            request.COOKIES['csrftoken'] = seed.META['CSRF_COOKIE']
            active, response = adapter.validate_request(request)
            self.assertEqual(active, allowed)
            if not allowed:
                self.assertEqual(response.status_code, 403)

    def test_only_form_post_and_get_supported(self):
        for request in (self.request('put'), self.factory.post(adapter.PATH, '{}', content_type='application/json')):
            active, response = adapter.validate_request(request)
            self.assertFalse(active)
            self.assertIn(response.status_code, (403, 405))

    def test_forms_only_same_origin_route_receive_token(self):
        request = self.request()
        source = ("<!doctype html>\n<script>let t='<form method=get>';</script>"
                  "<form method='get' action='?action=conf' data-note='a>b'>x&amp;y</form>"
                  "<form action='https://elsewhere.example/configservercsf/iframe/'>external</form>"
                  "<form action='/other'>other</form>")
        response = HttpResponse(source)
        response['Content-Length'] = '1'
        response['ETag'] = 'old'
        result = adapter.adapt_response(request, response)
        text = result.content.decode()
        self.assertEqual(text.count('name="csrfmiddlewaretoken"'), 1)
        self.assertIn('data-note="a&gt;b" method="post" action="/configservercsf/iframe/"', text)
        self.assertIn("<script>let t='<form method=get>';</script>", text)
        self.assertIn("<form action='/other'>other</form>", text)
        self.assertIn('x&amp;y', text)
        self.assertEqual(result['Content-Length'], str(len(result.content)))
        self.assertFalse(result.has_header('ETag'))


@override_settings(
    ROOT_URLCONF=__name__, ALLOWED_HOSTS=['testserver'],
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
    MIDDLEWARE=['django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'CyberCP.secMiddleware.secMiddleware'],
)
class MiddlewareIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        session = self.client.session
        session['userID'] = 1
        session.save()
        from django.conf import settings
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        plugin_view.calls.clear()
        self.admin = patch.object(adapter, '_is_admin', return_value=True)
        self.admin.start()
        self.addCleanup(self.admin.stop)
        self.model = patch('CyberCP.secMiddleware.Administrator.objects.get',
                           return_value=SimpleNamespace(securityLevel=1))
        self.model.start()
        self.addCleanup(self.model.stop)

    def test_real_csrf_exempt_view_get_confirmation_then_post_execution(self):
        denied = self.client.post(adapter.PATH, {'action': 'stop'})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(plugin_view.calls, [])
        confirmation = self.client.get(adapter.PATH, {'action': 'stop'})
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(plugin_view.calls, [])
        self.assertEqual(confirmation['X-Frame-Options'], 'sameorigin')
        self.assertIn("frame-ancestors 'self'", confirmation['Content-Security-Policy'])
        token = self.client.cookies['csrftoken'].value
        response = self.client.post(adapter.PATH, {'action': 'stop', 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(plugin_view.calls), 1)
        self.assertEqual(plugin_view.calls[0]['action'], 'stop')
        self.assertIn(b'csrfmiddlewaretoken', response.content)

    def test_configuration_special_characters_pass_only_with_csrf(self):
        self.client.get(adapter.PATH)
        token = self.client.cookies['csrftoken'].value
        response = self.client.post(adapter.PATH, {'action': 'saveconf',
             'TCP_IN': '22,80:90', 'comment': '# literal; $value\nentry', 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(plugin_view.calls[-1]['comment'], '# literal; $value\nentry')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
