import json
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.test import override_settings

from CyberCP.secMiddleware import secMiddleware
from webmail.webmailManager import WebmailManager


class StandaloneWebmailMiddlewareTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = secMiddleware(lambda request: HttpResponse('allowed'))

    def request(self, path, session=None, body=None):
        if body is None:
            request = self.factory.get(path)
        else:
            request = self.factory.post(
                path,
                data=json.dumps(body),
                content_type='application/json',
            )
        request.session = session if session is not None else SessionStore()
        return request

    def test_login_page_and_login_api_are_public(self):
        page = self.middleware(self.request('/webmail/login'))
        api = self.middleware(self.request(
            '/webmail/api/login',
            body={'email': 'user@example.com', 'password': 'secret'},
        ))

        self.assertEqual(200, page.status_code)
        self.assertEqual(200, api.status_code)

    def test_mailbox_api_requires_authenticated_session(self):
        response = self.middleware(self.request(
            '/webmail/api/listFolders',
            body={'folder': 'INBOX'},
        ))

        self.assertEqual(
            'This request need session.',
            json.loads(response.content)['error_message'],
        )

    def test_valid_standalone_session_can_access_mailbox_api(self):
        session = SessionStore()
        session.update({
            'webmail_standalone': True,
            'webmail_email': 'user@example.com',
            'webmail_password': 'secret',
        })

        response = self.middleware(self.request(
            '/webmail/api/listFolders',
            session=session,
            body={'folder': 'INBOX'},
        ))

        self.assertEqual(200, response.status_code)
        self.assertEqual(b'allowed', response.content)

    def test_incomplete_standalone_session_is_rejected(self):
        session = SessionStore()
        session.update({
            'webmail_standalone': True,
            'webmail_email': 'user@example.com',
        })

        response = self.middleware(self.request(
            '/webmail/api/listFolders',
            session=session,
            body={'folder': 'INBOX'},
        ))

        self.assertEqual(
            'This request need session.',
            json.loads(response.content)['error_message'],
        )


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'standalone-webmail-auth-tests',
        }
    }
)
class StandaloneWebmailManagerTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        from django.core.cache import cache
        cache.clear()

    def request(self, path='/webmail/api/login', body=None, session=None):
        request = self.factory.post(
            path,
            data=json.dumps(body or {}),
            content_type='application/json',
        )
        request.session = session if session is not None else SessionStore()
        return request

    @mock.patch('webmail.webmailManager.IMAPClient')
    def test_successful_login_creates_standalone_session(self, imap_client):
        session = SessionStore()
        request = self.request(
            body={'email': ' user@example.com ', 'password': 'secret'},
            session=session,
        )

        response = WebmailManager(request).apiLogin()

        self.assertEqual(1, json.loads(response.content)['status'])
        self.assertEqual('user@example.com', session['webmail_email'])
        self.assertEqual('secret', session['webmail_password'])
        self.assertTrue(session['webmail_standalone'])
        imap_client.assert_called_once_with('user@example.com', 'secret')
        imap_client.return_value.close.assert_called_once_with()

    @mock.patch('webmail.webmailManager.IMAPClient', side_effect=Exception('private detail'))
    @mock.patch('webmail.webmailManager.logging.CyberCPLogFileWriter.writeToFile')
    def test_failed_login_does_not_expose_backend_error(self, unused_log, unused_imap):
        response = WebmailManager(self.request(body={
            'email': 'user@example.com',
            'password': 'wrong',
        })).apiLogin()

        payload = json.loads(response.content)
        self.assertEqual(0, payload['status'])
        self.assertNotIn('private detail', payload['error_message'])
        self.assertNotIn('user@example.com', unused_log.call_args.args[0])
        self.assertNotIn('private detail', unused_log.call_args.args[0])

    def test_login_throttle_does_not_trust_forwarded_client_ip(self):
        first_request = self.request(body={
            'email': 'user@example.com',
            'password': 'wrong',
        })
        first_request.META['REMOTE_ADDR'] = '192.0.2.10'
        first_request.META['HTTP_CF_CONNECTING_IP'] = '198.51.100.1'
        second_request = self.request(body={
            'email': 'user@example.com',
            'password': 'wrong',
        })
        second_request.META['REMOTE_ADDR'] = '192.0.2.10'
        second_request.META['HTTP_CF_CONNECTING_IP'] = '203.0.113.20'

        self.assertEqual(
            WebmailManager(first_request)._login_failure_cache_key('user@example.com'),
            WebmailManager(second_request)._login_failure_cache_key('user@example.com'),
        )

    def test_standalone_sso_returns_the_authenticated_mailbox(self):
        session = SessionStore()
        session.update({
            'webmail_standalone': True,
            'webmail_email': 'user@example.com',
            'webmail_password': 'secret',
        })

        response = WebmailManager(self.request(session=session)).apiSSO()

        payload = json.loads(response.content)
        self.assertEqual(1, payload['status'])
        self.assertEqual('user@example.com', payload['email'])
        self.assertEqual(['user@example.com'], payload['accounts'])

    @mock.patch('webmail.webmailManager.IMAPClient', side_effect=Exception('denied'))
    @mock.patch('webmail.webmailManager.logging.CyberCPLogFileWriter.writeToFile')
    def test_repeated_failed_logins_are_rate_limited(self, unused_log, imap_client):
        request = self.request(body={
            'email': 'user@example.com',
            'password': 'wrong',
        })
        manager = WebmailManager(request)

        for unused in range(10):
            manager.apiLogin()
        response = manager.apiLogin()

        self.assertIn('Too many login attempts', json.loads(response.content)['error_message'])
        self.assertEqual(10, imap_client.call_count)

    @mock.patch('webmail.webmailManager.render', return_value=HttpResponse('mailbox'))
    def test_standalone_mailbox_page_renders_without_panel_user(self, render_view):
        request = self.factory.get('/webmail/')
        request.session = SessionStore()
        request.session.update({
            'webmail_standalone': True,
            'webmail_email': 'user@example.com',
            'webmail_password': 'secret',
        })

        response = WebmailManager(request).loadWebmail()

        self.assertEqual(200, response.status_code)
        self.assertEqual('webmail/index.html', render_view.call_args.args[1])
        self.assertEqual(
            'user@example.com',
            render_view.call_args.args[2]['email'],
        )
