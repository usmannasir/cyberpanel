"""Real request handlers with model reads isolated from product settings/SQL."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from django.conf import settings
if not settings.configured:
    settings.configure(DEFAULT_CHARSET='utf-8', ALLOWED_HOSTS=['testserver'])
from django.http import JsonResponse
from django.test import RequestFactory
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from databases.phpmyadmin_handoff import consume_handoff, create_handoff
from databases.phpmyadmin_session import issue_grant, panel_ip_allowed, validate_grant
from databases.test_phpmyadmin_session import Session


class PhpMyAdminSessionViewTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).with_name('views.py')
        names = {'_phpmyadmin_principal', 'consumePHPMYAdminHandoff', 'validatePHPMYAdminSession'}
        nodes = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
        self.admin = SimpleNamespace(pk=7, userName='panel-user', state='ACTIVE', securityLevel=0,
                                     acl=SimpleNamespace(config='{"adminStatus":0,"listDatabases":1}'))
        self.database_user = SimpleNamespace(token='authorization-token')
        self.admin_model = SimpleNamespace(objects=Mock())
        self.database_model = SimpleNamespace(objects=Mock())
        self.admin_model.objects.get.return_value = self.admin
        self.database_model.objects.get.return_value = self.database_user
        self.scope = dict(JsonResponse=JsonResponse, csrf_exempt=csrf_exempt, require_POST=require_POST,
                          json=json, Administrator=self.admin_model, GlobalUserDB=self.database_model,
                          issue_grant=issue_grant, panel_ip_allowed=panel_ip_allowed,
                          validate_grant=validate_grant, consume_handoff=consume_handoff)
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source), 'exec'), self.scope)
        self.session = Session(userID=7, ipAddr='203.0.113.10')
        self.grant = issue_grant(self.session, 7, 'panel-user', 'authorization-token', False)
        self.session.modified = False

    def request(self, endpoint='validatePHPMYAdminSession', method='post', **kwargs):
        body = dict(username='panel-user', grant=self.grant)
        body.update(kwargs)
        request = getattr(RequestFactory(), method)('/', body, REMOTE_ADDR='203.0.113.10')
        request.session = self.session
        return self.scope[endpoint](request)

    def test_valid_read_does_not_mutate_session(self):
        self.assertEqual(200, self.request().status_code)
        self.assertFalse(self.session.modified)

    def test_get_cannot_validate_or_consume(self):
        for endpoint in ('validatePHPMYAdminSession', 'consumePHPMYAdminHandoff'):
            self.assertEqual(405, self.request(endpoint=endpoint, method='get').status_code)

    def test_suspended_or_missing_current_principal_rejects(self):
        self.admin.state = 'SUSPENDED'
        self.assertEqual(403, self.request().status_code)
        self.admin_model.objects.get.side_effect = ValueError('not found')
        self.assertEqual(403, self.request().status_code)

    def test_missing_current_database_authorization_rejects(self):
        self.database_model.objects.get.side_effect = ValueError('not found')
        self.assertEqual(403, self.request().status_code)

    def test_revoked_list_permission_rejects(self):
        self.admin.acl.config = '{"adminStatus":0,"listDatabases":0}'
        self.assertEqual(403, self.request().status_code)

    def test_admin_demotion_rejects_root_grant(self):
        self.grant = issue_grant(self.session, 7, 'root', 'authorization-token', True)
        self.assertEqual(403, self.request(username='root').status_code)

    def test_admin_custom_database_user_preserved(self):
        self.admin.acl.config = '{"adminStatus":1}'
        self.grant = issue_grant(self.session, 7, 'remote-admin', 'authorization-token', True)
        self.assertEqual(200, self.request(username='remote-admin').status_code)

    def test_database_token_rotation_rejects(self):
        self.database_user.token = 'rotated-token'
        self.assertEqual(403, self.request().status_code)

    def test_non_admin_cannot_validate_another_database_user(self):
        self.assertEqual(403, self.request(username='other-user').status_code)

    def test_high_ip_change_rejects_even_without_middleware(self):
        self.session['ipAddr'] = '203.0.113.11'
        self.assertEqual(403, self.request().status_code)
        self.admin.securityLevel = 1
        self.assertEqual(200, self.request().status_code)

    def test_handoff_returns_new_bound_grant_only_once(self):
        create_handoff(self.session, 'panel-user', 'authorization-token')
        response = self.request(endpoint='consumePHPMYAdminHandoff', token='authorization-token')
        self.assertEqual(200, response.status_code)
        result = json.loads(response.content)
        self.assertEqual(64, len(result['grant']))
        self.assertNotEqual(self.grant, result['grant'])
        self.assertEqual(403, self.request(endpoint='consumePHPMYAdminHandoff', token='authorization-token').status_code)

    def test_refused_authorization_still_consumes_one_time_token(self):
        create_handoff(self.session, 'panel-user', 'authorization-token')
        self.admin.state = 'SUSPENDED'
        self.assertEqual(403, self.request(endpoint='consumePHPMYAdminHandoff', token='authorization-token').status_code)
        self.assertNotIn('phpmyadmin_handoff', self.session)

    def test_grant_is_not_created_for_rotated_handoff_authorization(self):
        create_handoff(self.session, 'panel-user', 'old-token')
        self.assertEqual(403, self.request(endpoint='consumePHPMYAdminHandoff', token='old-token').status_code)


if __name__ == '__main__':
    unittest.main()
