"""The server login addresses in the panel's own chain.

What the panel's last middleware does with these addresses is tested through the
whole chain, on the database of multiServer/test_gateway.py: which path counts
as one, and that a session is bound to its address there as everywhere else.
"""
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from multiServer import keys
from multiServer import test_gateway as panel

SKIP = panel.SKIP
if SKIP is None:
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from django.http import HttpResponse
    from django.test import Client
    from loginSystem.models import Administrator
    from multiServer import browser

HOST = panel.HOST
ELSEWHERE = '203.0.113.9'
FAILED = b'Server login unavailable'
# (address, method, the role that serves it)
LEGS = (('select', 'post', keys.CONTROLLER), ('return', 'post', keys.CONTROLLER), ('finish', 'get', keys.CONTROLLER),
        ('arrive', 'post', keys.NODE), ('redeem', 'post', keys.NODE))
# Paths that Django routes to another view, or to none, and that only resolve to a Multi-Server address.
DOTTED_LOGIN = ('/docker/view/x/../../../multiserver/login/arrive', '/docker/view/x/../../../multiserver/login/select',
                '/multiserver/login/x/../finish', '/x/../multiserver/login/redeem')


@unittest.skipIf(SKIP, SKIP)
class PathTests(panel.Panel):
    def test_the_login_addresses_are_the_five_that_are_routed(self):
        from django.urls import resolve
        self.assertEqual(set('/multiserver/login/' + leg for leg, _, _ in LEGS), set(browser.PATHS))
        for path in browser.PATHS:
            self.assertEqual('multiServer.views', resolve(path).func.__module__)

    def test_a_path_that_only_resolves_to_a_login_address_needs_a_session_like_any_other(self):
        for path in DOTTED_LOGIN:
            with self.subTest(path):
                response = Client().post(path, data=b'{"a": 1}', content_type='text/plain', HTTP_HOST=HOST)
                self.assertIn(b'This request need session.', response.content)
                self.assertFalse(response.has_header('Set-Cookie'))

    def test_such_a_path_does_not_let_a_managed_session_past_its_guard(self):
        for path in DOTTED_LOGIN:
            with self.subTest(path):
                session = SessionStore()
                session.update({'userID': self.administrator.pk, 'ipAddr': '127.0.0.1',
                                'ms_managed': {'link': panel.LINK}})
                session.save()
                client = Client()
                client.cookies[panel.settings.SESSION_COOKIE_NAME] = session.session_key
                response = client.get(path, HTTP_HOST=HOST)
                self.assertEqual(403, response.status_code)
                self.assertIn(FAILED, response.content)
                self.assertFalse(Session.objects.filter(pk=session.session_key).exists())

    def test_the_password_of_the_nodes_form_is_exempt_from_the_scanner_at_that_address_only(self):
        self.role.return_value = keys.CONTROLLER
        client = Client()
        self.sign_in(client)
        body = urlencode({'action': 'revoke', 'password': 'a;b|c$d'})
        form = 'application/x-www-form-urlencoded'
        for path in ('/x/../multiserver/nodes/control', '/multiserver/nodes/x/../control',
                     '/docker/view/x/../../../multiserver/nodes/control'):
            with self.subTest(path):
                response = client.post(path, data=body, content_type=form, HTTP_HOST=HOST)
                self.assertIn(b'Data supplied is not accepted', response.content)
        response = client.post('/multiserver/nodes/control', data=body, content_type=form, HTTP_HOST=HOST)
        self.assertNotIn(b'Data supplied is not accepted', response.content)


@unittest.skipIf(SKIP, SKIP)
class AddressBindingTests(panel.Panel):
    """A session is the session of the address it signed in from, at a server login address too."""

    def setUp(self):
        panel.Panel.setUp(self)
        self.users = []

        def reached(request):
            self.users.append(request.session.get('userID'))
            return HttpResponse('reached')

        for name in ('select', 'returned', 'finish', 'arrive', 'redeem'):
            self.start(patch.object(browser, name, side_effect=reached))

    def ask(self, leg, method, role, address, **session):
        self.role.return_value = role
        client = Client()
        key = self.sign_in(client)
        if session:
            stored = SessionStore(session_key=key)
            stored.update(session)
            stored.save()
        options = dict(HTTP_HOST=HOST, REMOTE_ADDR=address)
        if method == 'post':
            options.update(data='a=1', content_type='application/x-www-form-urlencoded')
        response = getattr(client, method)('/multiserver/login/' + leg, **options)
        return response, Session.objects.filter(pk=key).exists()

    def elsewhere(self):
        """Whether the panel keeps the same session, from the same other address, on an ordinary path."""
        client = Client()
        key = self.sign_in(client)
        client.get('/multiserver/no-such-address', HTTP_HOST=HOST, REMOTE_ADDR=ELSEWHERE)
        return Session.objects.filter(pk=key).exists()

    def test_from_its_own_address_the_session_reaches_the_view(self):
        for leg, method, role in LEGS:
            with self.subTest(leg):
                response, kept = self.ask(leg, method, role, '127.0.0.1')
                self.assertEqual((200, b'reached', True), (response.status_code, response.content, kept))
        self.assertEqual([self.administrator.pk] * len(LEGS), self.users)

    def test_from_another_address_the_session_is_ended_as_on_every_other_path(self):
        self.assertFalse(self.elsewhere())
        for leg, method, role in LEGS:
            with self.subTest(leg):
                response, kept = self.ask(leg, method, role, ELSEWHERE)
                self.assertFalse(kept, 'the session presented from another address was not ended')
                self.assertEqual(200, response.status_code)
        # The view answers for itself, and to nobody: there is no administrator in what it is given.
        self.assertEqual([None] * len(LEGS), self.users)

    def test_a_pending_server_login_goes_with_the_session(self):
        seen = []

        def finish(request):
            seen.append(request.session.get('ms_open'))
            return HttpResponse('reached')

        pending = ['f1' * 32, panel.LINK, int(time.time()) + 30]
        with patch.object(browser, 'finish', side_effect=finish):
            self.ask('finish', 'get', keys.CONTROLLER, '127.0.0.1', ms_open=pending)
            self.ask('finish', 'get', keys.CONTROLLER, ELSEWHERE, ms_open=pending)
        self.assertEqual([pending, None], seen)

    def test_an_administrator_without_address_binding_is_treated_as_on_every_other_path(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(securityLevel=1)
        self.assertTrue(self.elsewhere())
        for leg, method, role in LEGS:
            with self.subTest(leg):
                response, kept = self.ask(leg, method, role, ELSEWHERE)
                self.assertEqual((b'reached', True), (response.content, kept))
        self.assertEqual([self.administrator.pk] * len(LEGS), self.users)


@unittest.skipIf(SKIP, SKIP)
class RealViewTests(panel.Panel):
    def test_the_views_themselves_refuse_a_session_presented_from_another_address(self):
        self.role.return_value = keys.CONTROLLER
        for leg, method in (('select', 'post'), ('finish', 'get')):
            with self.subTest(leg):
                client = Client()
                key = self.sign_in(client)
                options = dict(HTTP_HOST=HOST, REMOTE_ADDR=ELSEWHERE, HTTP_SEC_FETCH_SITE='same-origin')
                if method == 'post':
                    options.update(data='server=local&page=index', content_type='application/x-www-form-urlencoded')
                response = getattr(client, method)('/multiserver/login/' + leg, **options)
                self.assertEqual(403, response.status_code)
                self.assertIn(FAILED, response.content)
                self.assertFalse(Session.objects.filter(pk=key).exists())


if __name__ == '__main__':
    unittest.main()
