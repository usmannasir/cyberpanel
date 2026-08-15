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
