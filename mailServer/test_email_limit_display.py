"""Read-only endpoint regressions for unavailable and explicitly saved email rates."""

import json
from pathlib import Path
import re
import unittest
from types import SimpleNamespace
from unittest import mock

from django.http import HttpResponse
from django.template import Context, Engine
from django.test import RequestFactory

from mailServer import mailserverManager as manager


class EmailLimitDisplayTests(unittest.TestCase):
    def read_limits(self, outputs, permission=1, ownership=1):
        request = RequestFactory().post(
            '/email/getEmailsForDomain', json.dumps({'domain': 'rate.example'}),
            content_type='application/json')
        request.session = {'userID': 7}
        emails = [SimpleNamespace(email='user%d@rate.example' % i, DiskUsage=0)
                  for i in range(len(outputs))]
        queryset = mock.MagicMock()
        queryset.count.return_value = len(emails)
        queryset.__iter__.side_effect = lambda: iter(emails)
        domain = SimpleNamespace(eusers_set=SimpleNamespace(all=lambda: queryset))
        denied = HttpResponse(json.dumps({'fetchStatus': 0}))
        with mock.patch.object(manager.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                mock.patch.object(manager.ACLManager, 'currentContextPermission', return_value=permission), \
                mock.patch.object(manager.ACLManager, 'checkOwnership', return_value=ownership), \
                mock.patch.object(manager.ACLManager, 'loadErrorJson', return_value=denied), \
                mock.patch.object(manager.Administrator.objects, 'get', return_value=SimpleNamespace(pk=7)), \
                mock.patch.object(manager.Domains.objects, 'get', return_value=domain), \
                mock.patch.object(manager.ProcessUtilities, 'outputExecutioner', side_effect=outputs) as execution:
            result = json.loads(manager.MailServerManager(request).getEmailsForDomain().content)
        return result, execution

    def assert_unavailable(self, output):
        response, execution = self.read_limits([output])
        self.assertEqual(response['fetchStatus'], 1)
        entry = json.loads(response['data'])[0]
        self.assertIsNone(entry['numberofEmails'])
        self.assertIsNone(entry['duration'])
        execution.assert_called_once()

    def test_missing_mailbox_override_is_unavailable(self):
        self.assert_unavailable('')

    def test_missing_map_is_unavailable(self):
        self.assert_unavailable('awk: cannot open /etc/rspamd/badusers.map\n0,0\n')

    def test_unreadable_map_is_unavailable(self):
        self.assert_unavailable('awk: permission denied\n0,0\n')

    def test_malformed_rate_is_unavailable(self):
        self.assert_unavailable('not-a-rate\n')

    def test_lookup_exception_is_unavailable(self):
        self.assert_unavailable(OSError('Lookup failed'))

    def test_saved_positive_rate_is_preserved(self):
        response, _ = self.read_limits(['10/5m\n'])
        entry = json.loads(response['data'])[0]
        self.assertEqual((entry['numberofEmails'], entry['duration']), (10, '5m'))

    def test_saved_zero_is_not_relabelled_unavailable(self):
        for saved, duration in [('0/0m\n', '0m'), ('0/5m\n', '5m')]:
            with self.subTest(saved=saved):
                response, _ = self.read_limits([saved])
                entry = json.loads(response['data'])[0]
                self.assertEqual((entry['numberofEmails'], entry['duration']), (0, duration))

    def test_missing_rate_does_not_inherit_previous_mailbox(self):
        response, _ = self.read_limits(['25/1h\n', ''])
        first, second = json.loads(response['data'])
        self.assertEqual((first['numberofEmails'], first['duration']), (25, '1h'))
        self.assertIsNone(second['numberofEmails'])
        self.assertIsNone(second['duration'])

    def test_permission_denial_does_not_read_limits(self):
        response, execution = self.read_limits(['10/5m\n'], permission=0)
        self.assertEqual(response['fetchStatus'], 0)
        execution.assert_not_called()

    def test_ownership_denial_does_not_read_limits(self):
        response, execution = self.read_limits(['10/5m\n'], ownership=0)
        self.assertEqual(response['fetchStatus'], 0)
        execution.assert_not_called()


class EmailLimitScriptVersionTests(unittest.TestCase):
    def rendered_script_url(self, context):
        root = Path(__file__).resolve().parents[1]
        engine = Engine(
            dirs=[str(root / 'baseTemplate' / 'templates')],
            libraries={'i18n': 'django.templatetags.i18n',
                       'static': 'django.templatetags.static'})
        # Navigation URL resolution is unrelated to rendering the real script
        # element and would import every application's URL configuration.
        with mock.patch('django.urls.reverse', return_value='/navigation/'):
            html = engine.get_template('baseTemplate/index.html').render(Context(context))
        urls = re.findall(r'<script\b[^>]*src="([^"]*mailServer/mailServer\.js[^\"]*)"', html)
        self.assertEqual(len(urls), 1)
        return urls[0]

    def test_mail_controller_script_uses_scoped_cache_version(self):
        self.assertEqual(
            self.rendered_script_url({'CYBERPANEL_FULL_VERSION': '3.0.6'}),
            '/static/mailServer/mailServer.js?v=3.0.6-2')

    def test_mail_controller_script_uses_fallback_cache_version(self):
        self.assertEqual(self.rendered_script_url({}),
                         '/static/mailServer/mailServer.js?v=3.0.3-2')


if __name__ == '__main__':
    unittest.main()
