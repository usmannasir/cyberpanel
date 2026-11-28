import json
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from webmail.webmailManager import WebmailManager


class WebmailSettingsSecurityTests(SimpleTestCase):

    def test_saved_signature_is_sanitized_in_storage_and_response(self):
        settings = SimpleNamespace(
            display_name='',
            signature_html='',
            messages_per_page=25,
            default_reply_behavior='',
            theme_preference='',
            auto_collect_contacts=False,
            save=mock.Mock(),
        )
        request = SimpleNamespace(
            body=json.dumps({
                'signatureHtml': '<b>Safe</b><img src=x onerror="run()"><script>run()</script>',
            }).encode('utf-8'),
            POST={},
            session={'webmail_email': 'user@example.com'},
        )

        with mock.patch(
            'webmail.webmailManager.WebmailSettings.objects.get_or_create',
            return_value=(settings, False),
        ):
            response = WebmailManager(request).apiSaveSettings()

        payload = json.loads(response.content)
        self.assertEqual(1, payload['status'])
        self.assertEqual('<b>Safe</b><img src=""/>', settings.signature_html)
        self.assertEqual(settings.signature_html, payload['signatureHtml'])
        settings.save.assert_called_once_with()


class WebmailSenderSettingsTests(SimpleTestCase):
    def send(self, display_name, multipart=False):
        from django.test import RequestFactory
        from django.core.files.uploadedfile import SimpleUploadedFile
        from email import message_from_bytes, policy

        data = {'fromAccount': 'selected@example.com', 'to': 'recipient@example.net',
                'subject': 'Fixture', 'body': '<b>Message</b>', 'displayName': 'Forged client name'}
        if multipart:
            data['attachment_0'] = SimpleUploadedFile('fixture.txt', b'Attachment fixture', content_type='text/plain')
            request = RequestFactory().post('/webmail/api/sendMessage', data)
        else:
            request = RequestFactory().post('/webmail/api/sendMessage', json.dumps(data), content_type='application/json')
        request.session = {'webmail_email': 'previous@example.com'}
        manager = WebmailManager(request)
        settings = None if display_name is None else SimpleNamespace(display_name=display_name, auto_collect_contacts=False)
        smtp = mock.Mock()
        smtp.send_message.return_value = {'success': True, 'message_id': '<fixture@example.com>'}
        with mock.patch.object(manager, '_get_managed_accounts', return_value=['selected@example.com']), \
                mock.patch('webmail.webmailManager.WebmailSettings.objects.filter') as query, \
                mock.patch.object(manager, '_get_smtp', return_value=smtp), \
                mock.patch.object(manager, '_get_imap', return_value=mock.MagicMock()), \
                mock.patch.object(manager, '_auto_collect'):
            query.return_value.first.return_value = settings
            result = json.loads(manager.apiSendMessage().content)
            query.assert_called_with(email_account='selected@example.com')
        if result['status'] == 0:
            return result, smtp, None
        message = smtp.send_message.call_args.args[0]
        return result, smtp, message_from_bytes(message.as_bytes(), policy=policy.default)

    def test_saved_name_is_used_for_selected_sender_in_json_and_attachment_requests(self):
        for multipart in (False, True):
            with self.subTest(multipart=multipart):
                result, smtp, message = self.send('Hasan, Support', multipart)
                self.assertEqual(1, result['status'])
                self.assertEqual('selected@example.com', result['sentFrom'])
                self.assertEqual('Hasan, Support', message['From'].addresses[0].display_name)
                self.assertEqual('selected@example.com', message['From'].addresses[0].addr_spec)
                if multipart:
                    attachment = list(message.iter_attachments())[0]
                    self.assertEqual('fixture.txt', attachment.get_filename())
                    self.assertEqual(b'Attachment fixture', attachment.get_payload(decode=True))

    def test_sender_without_settings_uses_bare_address(self):
        result, smtp, message = self.send(None)
        self.assertEqual(1, result['status'])
        self.assertEqual('selected@example.com', str(message['From']))

    def test_saved_header_injection_is_rejected_before_smtp(self):
        result, smtp, message = self.send('Hasan\r\nBcc: attacker@example.net')
        self.assertEqual(0, result['status'])
        smtp.send_message.assert_not_called()


PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 16


class WebmailServedContentTests(SimpleTestCase):
    """Bytes from a sender are served from the panel's address."""

    def request(self, **values):
        values.setdefault('body', b'{}')
        values.setdefault('POST', {})
        values.setdefault('GET', {})
        values.setdefault('session', {'webmail_email': 'user@example.com'})
        return SimpleNamespace(**values)

    def test_proxied_image_is_served_sandboxed_with_its_own_type(self):
        import base64
        url = base64.urlsafe_b64encode(b'https://images.example/x.png').decode('ascii')
        manager = WebmailManager(self.request(GET={'url': url}))

        with mock.patch('webmail.webmailManager.image_proxy.fetch_image',
                        return_value=(PNG, 'image/png')) as fetch:
            response = manager.apiProxyImage()

        fetch.assert_called_once_with('https://images.example/x.png')
        self.assertEqual('image/png', response['Content-Type'])
        self.assertIn('sandbox', response['Content-Security-Policy'])
        self.assertIn("default-src 'none'", response['Content-Security-Policy'])
        self.assertEqual(PNG, response.content)

    def test_refused_image_returns_an_error_not_the_bytes(self):
        import base64
        from webmail.services.image_proxy import ImageProxyError
        url = base64.urlsafe_b64encode(b'https://images.example/x.svg').decode('ascii')
        manager = WebmailManager(self.request(GET={'url': url}))

        with mock.patch('webmail.webmailManager.image_proxy.fetch_image',
                        side_effect=ImageProxyError('svg')):
            response = manager.apiProxyImage()

        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual(0, json.loads(response.content)['status'])

    def test_attachment_is_a_sandboxed_download(self):
        manager = WebmailManager(self.request(
            body=json.dumps({'folder': 'INBOX', 'uid': '7', 'partId': '0'}).encode('utf-8')))
        imap = mock.MagicMock()
        imap.__enter__.return_value.get_attachment.return_value = (
            'page.html', 'text/html', b'<script>run()</script>')

        with mock.patch.object(manager, '_get_imap', return_value=imap):
            response = manager.apiGetAttachment()

        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertIn('sandbox', response['Content-Security-Policy'])


class WebmailRuleSaveTests(SimpleTestCase):

    def manager(self, body):
        return WebmailManager(SimpleNamespace(
            body=json.dumps(body).encode('utf-8'), POST={},
            session={'webmail_email': 'user@example.com'}))

    def test_rule_outside_the_filter_page_choices_is_not_saved(self):
        manager = self.manager({'name': 'x', 'conditionField': 'X-Header" "y"; discard; #',
                                'conditionType': 'contains', 'conditionValue': 'a',
                                'actionType': 'discard'})

        with mock.patch('webmail.webmailManager.SieveRule.objects.create') as create, \
                mock.patch.object(manager, '_sync_sieve_rules') as sync:
            payload = json.loads(manager.apiCreateRule().content)

        self.assertEqual(0, payload['status'])
        create.assert_not_called()
        sync.assert_not_called()

    def sync_with_scripts(self, scripts, replace_active=False):
        manager = self.manager({})
        sieve = mock.MagicMock()
        sieve.__enter__.return_value = sieve
        sieve.list_scripts.return_value = scripts
        with mock.patch('webmail.webmailManager.SieveRule.objects.filter') as query, \
                mock.patch.object(manager, '_get_sieve', return_value=sieve):
            query.return_value.order_by.return_value = []
            result = manager._sync_sieve_rules('user@example.com', replace_active=replace_active)
        return result, sieve

    def test_another_active_script_is_kept_and_reported(self):
        result, sieve = self.sync_with_scripts([('roundcube', True), ('cyberpanel', False)])

        self.assertEqual('roundcube', result)
        sieve.put_script.assert_called_once_with('cyberpanel', '')
        sieve.activate_script.assert_not_called()

    def test_explicit_activation_replaces_the_other_script(self):
        result, sieve = self.sync_with_scripts([('roundcube', True)], replace_active=True)

        self.assertIsNone(result)
        sieve.activate_script.assert_called_once_with('cyberpanel')

    def test_panel_script_is_activated_when_nothing_else_is_active(self):
        for scripts in ([], [('cyberpanel', True)], [('old', False)]):
            result, sieve = self.sync_with_scripts(scripts)
            self.assertIsNone(result)
            sieve.activate_script.assert_called_once_with('cyberpanel')
