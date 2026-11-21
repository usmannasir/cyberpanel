"""The PHP manager changes the server only for a POST request (which carries the CSRF token)."""
import ast
import json
from pathlib import Path
import re
import shlex
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from django.http import HttpResponse
from django.views.decorators.http import require_POST

VIEWS = Path(__file__).with_name('views.py')
CHANGING = ('submitExtensionRequest', 'getRequestStatus', 'getRequestStatusApache', 'savePHPConfigBasic',
            'savePHPConfigAdvance', 'restartPHP')


def request_factory():
    """Django's request factory; outside the panel's own test runner it needs minimal settings."""
    from django.conf import settings
    if not settings.configured:
        settings.configure(DEFAULT_CHARSET='utf-8')
    from django.test import RequestFactory
    return RequestFactory()


def load_views(names, **extra):
    """Run the named view functions from managePHP/views.py with every service replaced.

    Returns the functions and the services, so a test can set what a service
    answers and read what it was asked to do.
    """
    services = {name: mock.Mock(name=name) for name in (
        'ACLManager', 'ProcessUtilities', 'PHPManager', 'phpUtilities', 'ApacheController', 'logging',
        'httpProc', 'PHP', 'installedPackages', 'ApachePHP', 'installedPackagesApache', 'open', 'os')}
    services['ACLManager'].loadedACL.return_value = {'admin': 1}
    services['ACLManager'].loadErrorJson.side_effect = \
        lambda key='error', value=0: HttpResponse(json.dumps({key: value, 'error_message': 'ACL denied'}))
    services['os'].path.exists.return_value = False
    namespace = dict(services, json=json, re=re, shlex=shlex, HttpResponse=HttpResponse,
                     require_POST=require_POST, randint=lambda lower, upper: lower,
                     virtualHostUtilities=NS(cyberPanel='/usr/local/CyberCP'),
                     redirect=lambda target: HttpResponse(status=302), loadLoginPage='login')
    namespace.update(extra)
    tree = ast.parse(VIEWS.read_text())
    wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(VIEWS), 'exec'), namespace)
    return NS(**{name: namespace[name] for name in names}), services, namespace


def post(path, data, user=1):
    request = request_factory().post(path, data=json.dumps(data), content_type='application/json')
    request.session = {'userID': user}
    return request


class RequestMethodTests(unittest.TestCase):
    def setUp(self):
        self.views, self.services, _ = load_views(CHANGING)

    def no_effects(self):
        for name, service in self.services.items():
            self.assertEqual([], service.mock_calls, name)

    def test_safe_methods_change_nothing(self):
        for name in CHANGING:
            for method in ('get', 'head', 'options'):
                with self.subTest(view=name, method=method):
                    request = getattr(request_factory(), method)('/managephp/' + name)
                    request.session = {'userID': 1}
                    response = getattr(self.views, name)(request)
                    self.assertEqual(405, response.status_code)
                    self.no_effects()

    def test_a_link_to_restart_php_does_not_stop_php(self):
        request = request_factory().get('/managephp/restartPHP')
        request.session = {'userID': 1}
        self.assertEqual(405, self.views.restartPHP(request).status_code)
        self.services['ProcessUtilities'].executioner.assert_not_called()

    def test_the_page_can_still_restart_php(self):
        response = self.views.restartPHP(post('/managephp/restartPHP', {}))
        self.assertEqual({'status': 1}, json.loads(response.content))
        self.services['ProcessUtilities'].executioner.assert_called_once_with('killall lsphp')

    def test_restart_stays_refused_for_other_users(self):
        self.services['ACLManager'].loadedACL.return_value = {'admin': 0}
        response = self.views.restartPHP(post('/managephp/restartPHP', {}, user=7))
        self.assertEqual(0, json.loads(response.content)['status'])
        self.services['ProcessUtilities'].executioner.assert_not_called()

    def test_every_route_of_a_changing_view_is_covered(self):
        # A view added to the routes later must be classified here.
        routed = set(re.findall(r'views\.(\w+)', VIEWS.with_name('urls.py').read_text()))
        reading = {'loadPHPHome', 'installExtensions', 'getExtensionsInformation', 'editPHPConfigs',
                   'getCurrentPHPConfig', 'getCurrentAdvancedPHPConfig'}
        self.assertEqual(set(), routed - reading - set(CHANGING))
        source = VIEWS.read_text()
        for name in CHANGING:
            self.assertIn('@require_POST\ndef %s(request):' % name, source)


if __name__ == '__main__':
    unittest.main()
