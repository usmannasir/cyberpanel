"""Routing and browser binding regressions. The database cases run on marked QA only."""
import unittest

from multiServer import landings


class LandingTests(unittest.TestCase):
    def test_object_pages_open_a_target_local_picker(self):
        self.assertEqual('listWebsites', landings.destination('siteWorkspace'))
        self.assertEqual('ListWPSites', landings.destination('WPHome'))
        self.assertEqual('createDatabase', landings.destination('createDatabase'))
        self.assertEqual('index', landings.destination(None))

    def test_only_fixed_page_names_can_be_requested(self):
        for name in ('https://example.invalid', '/base/', 'siteWorkspace', 'verifyLogin',
                     'saveModifications', 'createUser?ID=2', 'multiServerNodes'):
            self.assertNotIn(name, landings.PAGES)
from multiServer import testing

SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()


@unittest.skipIf(SKIP, SKIP)
class TicketTests(unittest.TestCase):
    """Real row locks and native Django sessions in a private MariaDB database."""
    @classmethod
    def setUpClass(cls):
        from django.contrib.sessions.models import Session
        from django.db import connection
        from multiServer import schema
        cls.db = testing.ScratchDatabase()
        try:
            cls.db.give_to_django()
            with connection.cursor() as cursor:
                schema.ensure_tables(connection, cursor)
            with connection.schema_editor() as editor:
                editor.create_model(Session)
        except BaseException:
            cls.db.drop()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.db.drop()

    def setUp(self):
        import secrets
        import time
        from types import SimpleNamespace
        from unittest.mock import patch
        from multiServer import crypto, keys, models, switch, views

        self.key = crypto.generate_private_key()
        self.actor = SimpleNamespace(pk=7, userName='fixture', password='hash', twoFA=1,
                                     secretKey='enrolled', acl_id=1)
        now = int(time.time())
        self.link = models.Link.objects.create(pk=secrets.token_hex(16), pairing_key=secrets.token_hex(32),
            controller_key=crypto.public_key(self.key).hex(), status=models.ACTIVE, allowed_ips='192.0.2.1',
            admin_id=7, generation=2, created_at=now, updated_at=now, expires_at=now+3600)
        for obj, name, result in ((keys, 'generation', 2), (keys, 'revoked', False),
                                  (switch, 'active_role', keys.NODE), (views, 'active_full_administrator', self.actor)):
            patcher = patch.object(obj, name, return_value=result)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.origin = 'https://controller.example:8090'
        self.target = 'node.example:8090'

    def ticket(self):
        import json
        from multiServer import sso, nodeGateway
        request = nodeGateway.Verified(self.link.pk, 7, 'fixture', 'ticket', 'POST', self.target,
            sso.ISSUE, '', 'application/json', json.dumps(['listDBs', self.origin]).encode(), '192.0.2.1')
        status, media, raw = sso.gateway_issue(request)
        self.assertEqual((200, 'application/json'), (status, media))
        return json.loads(raw.decode())

    def test_browser_and_signed_authority_agree_on_default_https_port(self):
        from multiServer.sso import panel_origin
        self.assertEqual('https://node.example', panel_origin('https://node.example:443'))
        self.assertEqual('https://[2001:db8::2]', panel_origin('https://[2001:db8::2]:443'))
        self.assertEqual('https://node.example:8090', panel_origin('https://node.example:8090'))

    def test_unique_tickets_store_hashes_and_expire(self):
        from unittest.mock import patch
        from django.db import transaction
        from multiServer import models, sso
        token = self.ticket()
        self.assertTrue(token != self.ticket())
        flow = sso.digest(token)
        row = models.SsoTicket.objects.get(pk=flow)
        self.assertEqual(30, row.expires_at - row.created_at)
        self.assertFalse(models.SsoTicket.objects.filter(pk=token).exists())
        with transaction.atomic(), patch('time.time', return_value=row.expires_at), self.assertRaises(ValueError):
            sso.ticket_state(flow, self.origin, 'https://' + self.target)

    def test_authorization_changes_and_destination_binding(self):
        from django.db import transaction
        from multiServer import models, sso
        flow = sso.digest(self.ticket())
        with transaction.atomic(), self.assertRaises(ValueError):
            sso.ticket_state(flow, self.origin, 'https://other.example:8090')
        self.actor.acl_id = 2
        with transaction.atomic(), self.assertRaises(ValueError):
            sso.ticket_state(flow, self.origin, 'https://' + self.target)
        self.actor.acl_id = 1
        models.Link.objects.filter(pk=self.link.pk).update(status=models.PAUSED)
        with transaction.atomic(), self.assertRaises(ValueError):
            sso.ticket_state(flow, self.origin, 'https://' + self.target)

    def test_concurrent_workers_establish_one_new_native_session(self):
        import concurrent.futures
        import secrets
        import threading
        from urllib.parse import urlencode
        from django.contrib.sessions.backends.db import SessionStore
        from django.contrib.sessions.models import Session
        from django.db import connections
        from django.test import RequestFactory
        from multiServer import browser, crypto, models, sso

        flow = sso.digest(self.ticket())
        cookie = secrets.token_hex(32)
        proof = crypto.sign(self.key, sso.proof_message(flow, sso.digest(cookie))).hex()
        body = urlencode({'flow': flow, 'proof': proof, 'controller': self.origin})
        gate = threading.Barrier(4)

        def redeem(_):
            try:
                request = RequestFactory().post('/multiserver/login/redeem', body, secure=True,
                    content_type='application/x-www-form-urlencoded', HTTP_HOST=self.target, HTTP_ORIGIN='null')
                request.session = SessionStore()
                request.COOKIES[browser.BIND] = cookie
                gate.wait(10)
                return browser.dispatch(request, browser.redeem).status_code
            finally:
                connections.close_all()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual([303,403,403,403], sorted(pool.map(redeem, range(4))))
        session = models.LinkSession.objects.get(link=self.link)
        native = Session.objects.get(pk=session.pk).get_decoded()
        self.assertEqual((7, self.link.pk), (native['userID'], native['ms_managed']['link']))
        from unittest.mock import patch
        request = RequestFactory().get('/dataBases/listDBs', secure=True, HTTP_HOST=self.target)
        request.session = SessionStore(session_key=session.pk)
        with patch('time.time', return_value=native['ms_managed']['until']), self.assertRaises(ValueError):
            sso.managed_context(request)

    def test_all_picker_contexts_reverse_to_unparameterized_or_fixed_hub_pages(self):
        from django.urls import resolve
        for source in landings.CREATE_PAGES:
            self.assertIn(source, landings.PAGES.union(landings.PICKERS))
        for page in sorted(landings.PAGES):
            path = landings.path(page)
            self.assertNotIn('?', path)
            self.assertEqual(page, landings.destination(resolve(path).url_name, resolve(path).kwargs))
