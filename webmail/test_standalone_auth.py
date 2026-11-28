import json
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, tag
from django.test import override_settings

from CyberCP.secMiddleware import secMiddleware
from webmail import mailbox_secret
from webmail.webmailManager import WebmailManager


def sign_in(request, password='secret'):
    """Give request the standalone session a successful login creates."""
    request.session['webmail_standalone'] = True
    request.session['webmail_email'] = 'user@example.com'
    mailbox_secret.store(request, HttpResponse(), password)
    return request


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

    def test_webmail_auth_endpoints_are_public(self):
        page = self.middleware(self.request('/webmail/login'))
        api = self.middleware(self.request(
            '/webmail/api/login',
            body={'email': 'user@example.com', 'password': 'secret'},
        ))
        logout = self.middleware(self.request(
            '/webmail/api/logout',
            body={},
        ))

        self.assertEqual(200, page.status_code)
        self.assertEqual(200, api.status_code)
        self.assertEqual(200, logout.status_code)

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
        request = sign_in(self.request('/webmail/api/listFolders', body={'folder': 'INBOX'}))

        response = self.middleware(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(b'allowed', response.content)

    def test_session_without_the_browser_key_is_rejected(self):
        request = sign_in(self.request('/webmail/api/listFolders', body={'folder': 'INBOX'}))
        del request.COOKIES[mailbox_secret.COOKIE_NAME]

        response = self.middleware(request)

        self.assertEqual('This request need session.',
                         json.loads(response.content)['error_message'])

    def test_session_whose_secret_cannot_be_opened_is_rejected(self):
        request = sign_in(self.request('/webmail/api/listFolders', body={'folder': 'INBOX'}))
        from cryptography.fernet import Fernet
        request.COOKIES[mailbox_secret.COOKIE_NAME] = Fernet.generate_key().decode('ascii')

        response = self.middleware(request)

        self.assertEqual('This request need session.',
                         json.loads(response.content)['error_message'])

    def test_ended_mailbox_session_is_sent_to_the_webmail_login(self):
        session = SessionStore()
        session.update({'webmail_standalone': True, 'webmail_email': 'user@example.com',
                        'webmail_password': 'secret'})

        response = self.middleware(self.request('/webmail/', session=session))

        self.assertEqual(302, response.status_code)
        self.assertEqual('/webmail/login', response['Location'])

    def test_plain_password_session_of_older_releases_is_rejected(self):
        session = SessionStore()
        session.update({
            'webmail_standalone': True,
            'webmail_email': 'user@example.com',
            'webmail_password': 'secret',
        })

        response = self.middleware(self.request(
            '/webmail/api/listFolders', session=session, body={'folder': 'INBOX'}))

        self.assertEqual('This request need session.',
                         json.loads(response.content)['error_message'])

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


@tag('integration')
class StandaloneWebmailRouteIntegrationTests(SimpleTestCase):

    def setUp(self):
        self.client = Client()

    def test_anonymous_auth_routes_reach_webmail_views(self):
        with mock.patch(
            'webmail.webmailManager.render',
            return_value=HttpResponse('webmail login'),
        ):
            login_page = self.client.get('/webmail/login')
        login_api = self.client.post(
            '/webmail/api/login',
            data=json.dumps({}),
            content_type='application/json',
        )
        with mock.patch(
            'webmail.webmailManager.WebmailManager.apiLogout',
            return_value=HttpResponse(
                json.dumps({'status': 1}),
                content_type='application/json',
            ),
        ):
            logout_api = self.client.post(
                '/webmail/api/logout',
                data=json.dumps({}),
                content_type='application/json',
            )

        self.assertEqual(200, login_page.status_code)
        self.assertIn('csrftoken', login_page.cookies)
        self.assertEqual(
            'Email and password are required.',
            json.loads(login_api.content)['error_message'],
        )
        self.assertEqual(1, json.loads(logout_api.content)['status'])

    def test_logout_rejects_get_requests(self):
        response = self.client.get('/webmail/api/logout')

        self.assertEqual(405, response.status_code)


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
            body={'email': ' user@example.com ', 'password': 'mailbox-pw-7781'},
            session=session,
        )

        response = WebmailManager(request).apiLogin()

        self.assertEqual(1, json.loads(response.content)['status'])
        self.assertEqual('user@example.com', session['webmail_email'])
        self.assertNotIn('webmail_password', session)
        self.assertNotIn('mailbox-pw-7781', json.dumps(dict(session.items())))
        self.assertTrue(session['webmail_standalone'])
        cookie = response.cookies[mailbox_secret.COOKIE_NAME]
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])
        self.assertEqual('/webmail', cookie['path'])
        later = self.request(session=session)
        later.COOKIES[mailbox_secret.COOKIE_NAME] = cookie.value
        self.assertEqual('mailbox-pw-7781', mailbox_secret.password(later))
        imap_client.assert_called_once_with('user@example.com', 'mailbox-pw-7781')
        imap_client.return_value.close.assert_called_once_with()

    @mock.patch('webmail.webmailManager.WebmailManager._get_master_config',
                return_value=('cyberpanel_master', 'stale-master-password'))
    @mock.patch('webmail.webmailManager.IMAPClient')
    def test_standalone_login_keeps_mailbox_credentials_for_imap(self, imap_client, master_config):
        def authenticate(address, password, **kwargs):
            if kwargs or password != 'secret':
                raise Exception('Master authentication is unavailable')
            return mock.MagicMock()

        imap_client.side_effect = authenticate
        request = self.request(body={'email': 'user@example.com', 'password': 'secret'})
        manager = WebmailManager(request)

        self.assertEqual(1, json.loads(manager.apiLogin().content)['status'])
        manager._get_imap()

        self.assertEqual(imap_client.call_args_list, [
            mock.call('user@example.com', 'secret'),
            mock.call('user@example.com', 'secret'),
        ])

    @mock.patch('webmail.webmailManager.WebmailManager._get_master_config',
                return_value=('cyberpanel_master', 'stale-master-password'))
    @mock.patch('webmail.webmailManager.SieveClient')
    def test_standalone_sieve_uses_authenticated_mailbox_credentials(self, sieve_client, master_config):
        request = sign_in(self.request())

        WebmailManager(request)._get_sieve()

        sieve_client.assert_called_once_with('user@example.com', 'secret')

    @mock.patch('webmail.webmailManager.WebmailManager._get_master_config',
                return_value=('cyberpanel_master', 'master-secret'))
    @mock.patch('webmail.webmailManager.SieveClient')
    @mock.patch('webmail.webmailManager.IMAPClient')
    def test_panel_sso_retains_master_authentication(self, imap_client, sieve_client, master_config):
        request = self.request(session={'userID': 1, 'webmail_email': 'user@example.com'})
        manager = WebmailManager(request)

        manager._get_imap()
        manager._get_sieve()

        for client in (imap_client, sieve_client):
            client.assert_called_once_with('user@example.com', '',
                                           master_user='cyberpanel_master',
                                           master_password='master-secret')

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
        response = WebmailManager(sign_in(self.request())).apiSSO()

        payload = json.loads(response.content)
        self.assertEqual(1, payload['status'])
        self.assertEqual('user@example.com', payload['email'])
        self.assertEqual(['user@example.com'], payload['accounts'])

    def test_logout_clears_standalone_mailbox_session(self):
        request = sign_in(self.request())
        session = request.session

        response = WebmailManager(request).apiLogout()

        self.assertEqual(1, json.loads(response.content)['status'])
        self.assertNotIn('webmail_standalone', session)
        self.assertNotIn('webmail_email', session)
        self.assertNotIn(mailbox_secret.SESSION_KEY, session)
        self.assertEqual(0, int(response.cookies[mailbox_secret.COOKIE_NAME]['max-age']))

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
        sign_in(request)

        response = WebmailManager(request).loadWebmail()

        self.assertEqual(200, response.status_code)
        # call_args[0] rather than .args: Python 3.6 (AlmaLinux 8) has no .args.
        self.assertEqual('webmail/index.html', render_view.call_args[0][1])
        self.assertEqual(
            'webmail/base.html',
            render_view.call_args[0][2]['webmail_base_template'],
        )
        self.assertEqual(
            'user@example.com',
            render_view.call_args[0][2]['email'],
        )


class StoredPasswordScrubTests(SimpleTestCase):
    """Sessions written by older releases held the mailbox password itself."""

    def fake_session_model(self, rows):
        class Manager:
            def only(self, *fields):
                return self

            def iterator(self):
                from types import SimpleNamespace
                return [SimpleNamespace(session_key=key, session_data=value)
                        for key, value in list(rows.items())]

            def filter(self, session_key):
                class Update:
                    def update(self, session_data):
                        rows[session_key] = session_data
                return Update()

        class Model:
            objects = Manager()

        return Model

    def test_plain_passwords_are_removed_and_other_sessions_left_alone(self):
        from django.contrib.sessions.backends.db import SessionStore as DatabaseStore
        codec = DatabaseStore()
        rows = {
            'standalone': codec.encode({'webmail_standalone': True,
                                        'webmail_email': 'user@example.com',
                                        'webmail_password': 'secret'}),
            'panel': codec.encode({'userID': 1}),
            'unreadable': 'not a session',
        }
        untouched = dict(rows)

        # The real store: Django salts session signatures with its class name.
        with mock.patch.object(DatabaseStore, 'clear_expired') as clear_expired:
            changed = mailbox_secret.scrub_stored_passwords(
                self.fake_session_model(rows), DatabaseStore)

        clear_expired.assert_called_once_with()

        self.assertEqual(1, changed)
        scrubbed = codec.decode(rows['standalone'])
        self.assertNotIn('webmail_password', scrubbed)
        self.assertEqual('user@example.com', scrubbed['webmail_email'])
        self.assertEqual(untouched['panel'], rows['panel'])
        self.assertEqual(untouched['unreadable'], rows['unreadable'])

    def test_scrub_never_raises(self):
        class Broken:
            class objects:
                @staticmethod
                def only(*fields):
                    raise RuntimeError('database unavailable')

        with mock.patch('plogical.CyberCPLogFileWriter.CyberCPLogFileWriter.writeToFile'):
            self.assertEqual(0, mailbox_secret.scrub_stored_passwords(Broken, SessionStore))

    def test_scrub_runs_after_every_migrate(self):
        from django.apps import apps
        from django.db.models.signals import post_migrate
        config = apps.get_app_config('webmail')
        with mock.patch('webmail.mailbox_secret.scrub_stored_passwords') as scrub:
            receivers = post_migrate._live_receivers(config)
            if isinstance(receivers, tuple):  # Django 5 splits sync and async
                receivers = list(receivers[0]) + list(receivers[1])
            for receiver in receivers:
                if getattr(receiver, '__module__', '') == 'webmail.apps':
                    receiver(sender=config)
        scrub.assert_called_once_with()
