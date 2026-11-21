"""The app inside the panel: registered, mounted, and absent unless switched on.

Runs only on a server marked as a disposable test server (see
multiServer/testing.py). No test here opens a database connection.
"""
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

from multiServer import crypto, keys, schema, switch, testing

SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()
    from django.apps import apps
    from django.conf import settings
    from django.contrib.sessions.backends.signed_cookies import SessionStore
    from django.http import Http404
    from django.test import RequestFactory, SimpleTestCase, override_settings
    from django.urls import Resolver404, resolve
    from multiServer import entitlement, urls, views
    Base = SimpleTestCase
else:
    Base = unittest.TestCase

TABLES = {table.name: table for table in schema.TABLES}


def request(method='GET', user_id=1):
    made = getattr(RequestFactory(), method.lower())('/multiserver/status')
    made.session = {} if user_id is None else {'userID': user_id}
    return made


class Switched(Base):
    """A server with a role, signatures and tables, unless a test says otherwise."""

    def setUp(self):
        self.role = patch.object(keys, 'role', return_value=keys.NODE).start()
        self.ready = patch.object(schema, 'ready', return_value=True).start()
        self.self_test = patch.object(crypto, 'self_test', return_value=True).start()
        patch.object(switch, '_SIGNING', False).start()
        self.administrator = MagicMock(state='ACTIVE')
        self.find = patch('loginSystem.models.Administrator.objects.get', return_value=self.administrator).start()
        self.acl = patch('plogical.acl.ACLManager.loadedACL', return_value={'admin': 1}).start()
        self.allowed = patch.object(entitlement, 'allowed', return_value=True).start()
        self.addCleanup(patch.stopall)


@unittest.skipIf(SKIP, SKIP)
class RegistrationTests(Base):
    def test_the_app_is_installed_and_mounted_at_multiserver(self):
        self.assertIn('multiServer', settings.INSTALLED_APPS)
        self.assertEqual('multiServer', apps.get_app_config('multiServer').name)
        self.assertIs(views.status, resolve('/multiserver/status').func)

    def test_django_never_creates_or_migrates_the_tables(self):
        self.assertIsNone(importlib.util.find_spec('multiServer.migrations'))
        for model in apps.get_app_config('multiServer').get_models():
            self.assertIs(False, model._meta.managed, model.__name__)

    def test_every_route_is_behind_the_switch(self):
        self.assertTrue(urls.urlpatterns)
        for pattern in urls.urlpatterns:
            # No route may differ from a missing one by a redirect to a longer address.
            self.assertFalse(str(pattern.pattern).endswith('/'), pattern)
            if pattern.name == 'multiServerRole':
                # The one page that is there with the feature off: where a full administrator switches it on.
                self.assertIs(views.role_page, pattern.callback)
                self.assertFalse(hasattr(pattern.callback, 'serves'))
                continue
            roles = getattr(pattern.callback, 'serves', None)
            self.assertTrue(roles and set(roles) <= {keys.CONTROLLER, keys.NODE}, pattern)
        self.assertEqual(1, [pattern.name for pattern in urls.urlpatterns].count('multiServerRole'))

    def test_a_view_cannot_be_declared_for_no_role_or_for_off(self):
        for roles in ((), ('off',), ('controller', 'off'), ('both',), (None,)):
            with self.assertRaises(ValueError):
                views.serves(*roles)

    def test_the_models_describe_exactly_the_tables_that_are_created(self):
        described = {model._meta.db_table: model for model in apps.get_app_config('multiServer').get_models()}
        self.assertEqual(set(TABLES), set(described))
        for name, model in described.items():
            table = TABLES[name]
            fields = {field.column: field for field in model._meta.concrete_fields}
            self.assertEqual([column for column, _ in table.columns],
                             [field.column for field in model._meta.concrete_fields], name)
            self.assertEqual(table.primary, (model._meta.pk.column,), name)
            for column, definition in table.columns:
                field = fields[column]
                self.assertEqual('NOT NULL' not in definition, field.null, (name, column))
                stored = field.target_field if field.is_relation else field
                width = re.match(r'varchar\((\d+)\)', definition)
                self.assertEqual(int(width.group(1)) if width else None, stored.max_length, (name, column))
                kind = stored.get_internal_type()
                self.assertEqual({'varchar': 'CharField', 'bigint': 'BigIntegerField', 'int': 'IntegerField',
                                  'smallint': 'SmallIntegerField', 'tinyint(1)': 'BooleanField',
                                  'mediumtext': 'TextField'}[re.match(r'[a-z]+(\(1\))?', definition).group(0)],
                                 'BigIntegerField' if kind == 'BigAutoField' else kind, (name, column))
                default = re.search(r" DEFAULT (0|''|'pending'|NULL)", definition)
                if default and not field.primary_key:
                    expected = {'0': 0, "''": '', "'pending'": 'pending', 'NULL': None}[default.group(1)]
                    self.assertEqual(expected, field.get_default(), (name, column))
            unique = {(field.column,) for field in model._meta.concrete_fields if field.unique}
            unique |= {tuple(model._meta.get_field(member).column for member in group)
                       for group in model._meta.unique_together}
            self.assertEqual(set(schema.required_unique(table)), unique, name)
            foreign = {(field.column, field.related_model._meta.db_table, field.target_field.column)
                       for field in model._meta.concrete_fields if field.is_relation}
            self.assertEqual({constraint[1:] for constraint in table.foreign}, foreign, name)


@unittest.skipIf(SKIP, SKIP)
class OffTests(Switched):
    def assert_absent(self, made=None):
        with self.assertRaises(Http404) as refused:
            views.status(made or request())
        self.assertNotIsInstance(refused.exception, Resolver404)
        self.find.assert_not_called()
        self.allowed.assert_not_called()

    def test_with_the_role_off_the_route_does_not_exist_and_nothing_else_is_looked_at(self):
        self.role.return_value = keys.OFF
        self.assert_absent()
        self.ready.assert_not_called()
        self.self_test.assert_not_called()

    def test_without_a_role_file_the_route_does_not_exist(self):
        patch.stopall()
        if keys.role() != keys.OFF:
            self.skipTest('this server has a Multi-Server Manager role of its own')
        with patch.object(schema, 'ready') as ready, patch.object(crypto, 'self_test') as self_test:
            with self.assertRaises(Http404):
                views.status(request())
            ready.assert_not_called()
            self_test.assert_not_called()

    def test_with_a_role_but_no_usable_tables_the_route_does_not_exist(self):
        self.ready.return_value = False
        self.assert_absent()

    def test_with_a_role_but_no_working_signatures_the_route_does_not_exist(self):
        self.self_test.return_value = False
        self.assert_absent()
        self.ready.assert_not_called()

    def test_a_failure_inside_the_switch_means_off(self):
        for broken in (self.role, self.ready, self.self_test):
            switch._SIGNING = False
            broken.side_effect = RuntimeError('unexpected')
            self.assertEqual(keys.OFF, switch.active_role())
            self.assert_absent()
            broken.side_effect = None

    def test_the_role_is_read_again_on_every_request(self):
        self.assertEqual(200, views.status(request()).status_code)
        self.role.return_value = keys.OFF
        with self.assertRaises(Http404):
            views.status(request())
        self.role.return_value = keys.CONTROLLER
        self.assertEqual(200, views.status(request()).status_code)
        self.assertEqual(3, self.role.call_count)
        self.assertEqual(1, self.self_test.call_count, 'a passed self-test is remembered')

    def test_a_view_for_the_other_role_does_not_exist_here(self):
        view = views.serves(keys.CONTROLLER)(lambda made, role: role)
        with self.assertRaises(Http404):
            view(request())
        self.role.return_value = keys.CONTROLLER
        self.assertEqual(keys.CONTROLLER, view(request()))


@unittest.skipIf(SKIP, SKIP)
class StatusTests(Switched):
    def answer(self, made=None):
        response = views.status(made or request())
        self.assertEqual((200, 'application/json', 'no-store'),
                         (response.status_code, response['Content-Type'], response['Cache-Control']))
        return json.loads(response.content)

    def test_a_managed_server_reports_its_role_and_asks_nobody_about_a_licence(self):
        self.assertEqual({'role': 'node', 'licensed': None}, self.answer())
        self.allowed.assert_not_called()
        self.find.assert_called_once_with(pk=1)
        self.acl.assert_called_once_with(1)

    def test_a_controller_reports_its_licence(self):
        self.role.return_value = keys.CONTROLLER
        self.assertEqual({'role': 'controller', 'licensed': True}, self.answer())
        self.allowed.return_value = False
        self.assertEqual({'role': 'controller', 'licensed': False}, self.answer())

    def test_only_a_signed_in_active_full_administrator_gets_an_answer(self):
        def refused(made=None):
            with self.assertRaises(Http404):
                views.status(made or request())
            self.allowed.assert_not_called()
        for user_id in (None, '1', 1.0, True, [1], {'pk': 1}):
            refused(request(user_id=user_id))
        self.find.assert_not_called()
        for acl in ({'admin': 0}, {}, {'admin': '1'}, {'admin': True}, {'admin': 2}):
            self.acl.return_value = acl
            refused()
        self.acl.return_value = {'admin': 1}
        for state in ('SUSPENDED', '', 'active', None):
            self.administrator.state = state
            refused()
        self.administrator.state = 'ACTIVE'
        for failing in (self.find, self.acl):
            failing.side_effect = RuntimeError('no such administrator')
            refused()
            failing.side_effect = None
        without_session = request()
        del without_session.session
        refused(without_session)
        self.assertEqual({'role': 'node', 'licensed': None}, self.answer())

    def test_only_get_is_answered(self):
        for method in ('POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'):
            with self.assertRaises(Http404):
                views.status(request(method))


@unittest.skipIf(SKIP, SKIP)
class ThroughThePanelTests(Switched):
    """Real requests through the panel's own URL table and middleware.

    Sessions are kept in a signed cookie here so that no database is needed;
    the administrator the security middleware and the view look up is a stand-in.
    """

    def setUp(self):
        super().setUp()
        self.administrator.securityLevel = 1
        settings_patch = override_settings(SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
        settings_patch.enable()
        self.addCleanup(settings_patch.disable)

    def sign_in(self):
        session = SessionStore()
        session['userID'] = 1
        session['ipAddr'] = '127.0.0.1'
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

    def test_switched_off_the_address_answers_exactly_like_one_that_was_never_there(self):
        self.role.return_value = keys.OFF
        self.sign_in()
        there = self.client.get('/multiserver/status')
        never = self.client.get('/multiserver/statu')
        elsewhere = self.client.get('/no-such-app/status')
        self.assertEqual(404, there.status_code)
        for other in (never, elsewhere):
            self.assertEqual((other.status_code, other.content, sorted(other.items())),
                             (there.status_code, there.content, sorted(there.items())))
        for address in ('/multiserver/status/', '/multiserver/', '/multiserver'):
            self.assertEqual(404, self.client.get(address).status_code, address)
        self.assertEqual(404, self.client.head('/multiserver/status').status_code)
        self.assertEqual(404, self.client.post('/multiserver/status').status_code)
        self.ready.assert_not_called()

    def test_switched_on_a_full_administrator_gets_the_status(self):
        self.sign_in()
        response = self.client.get('/multiserver/status')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'role': 'node', 'licensed': None}, json.loads(response.content))
        self.assertEqual('nosniff', response['X-Content-Type-Options'])

    def test_switched_on_anyone_else_is_told_nothing(self):
        self.sign_in()
        self.acl.return_value = {'admin': 0}
        there = self.client.get('/multiserver/status')
        never = self.client.get('/multiserver/statu')
        self.assertEqual((404, never.content), (there.status_code, there.content))

    def test_the_role_page_does_not_exist_for_anyone_but_a_full_administrator_whatever_the_role(self):
        self.sign_in()
        self.acl.return_value = {'admin': 0}
        for role in (keys.OFF, keys.CONTROLLER, keys.NODE):
            self.role.return_value = role
            never = self.client.get('/multiserver/rol')
            for there in (self.client.get('/multiserver/role'),
                          self.client.post('/multiserver/role', data={'role': 'node'})):
                self.assertEqual((404, never.content, sorted(never.items())),
                                 (there.status_code, there.content, sorted(there.items())), role)

    def test_without_a_session_the_panel_sends_the_visitor_to_sign_in_as_for_any_address(self):
        for role in (keys.OFF, keys.NODE):
            self.role.return_value = role
            there = self.client.get('/multiserver/status')
            never = self.client.get('/multiserver/statu')
            self.assertEqual(302, there.status_code)
            self.assertEqual((never.status_code, never['Location']), (there.status_code, there['Location']))


class CompatibilityTests(unittest.TestCase):
    """Not skipped anywhere: the files only a test server runs are still checked for the old grammar."""

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_sources_parse_as_python_3_6(self):
        directory = Path(__file__).resolve().parent
        for name in ('apps.py', 'models.py', 'switch.py', 'testing.py', 'urls.py', 'views.py', 'test_wiring.py',
                     'test_database.py'):
            ast.parse((directory / name).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
