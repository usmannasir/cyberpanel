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
