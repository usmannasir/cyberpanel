import json
import pathlib
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from baseTemplate import views


class BaseTemplateSecurityTests(SimpleTestCase):

    def post(self, path, payload):
        request = RequestFactory().post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.session = {'userID': 1}
        return request

    def test_ssh_activity_requires_csrf_protection(self):
        self.assertFalse(getattr(views.getSSHUserActivity, 'csrf_exempt', False))

        javascript = (
            pathlib.Path(views.__file__).with_name('static')
            / 'baseTemplate'
            / 'custom-js'
            / 'system-status.js'
        ).read_text(encoding='utf-8')
        activity_request = javascript[javascript.index("$http.post('/base/getSSHUserActivity'"):]
        self.assertIn("'X-CSRFToken': getCookie('csrftoken')", activity_request[:400])

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_ssh_activity_rejects_command_characters(self, unused_acl):
        request = self.post(
            '/base/getSSHUserActivity',
            {'user': 'root;id', 'tty': '', 'ip': ''},
        )

        with mock.patch('baseTemplate.views.subprocess.run') as run:
            response = views.getSSHUserActivity(request)

        self.assertEqual(400, response.status_code)
        run.assert_not_called()

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    @mock.patch('baseTemplate.views.Websites.objects.get', side_effect=Exception('not a website user'))
    @mock.patch(
        'baseTemplate.views.pwd.getpwnam',
        return_value=SimpleNamespace(pw_dir='/home/example'),
    )
    def test_ssh_activity_uses_argument_list_commands(
            self,
            unused_account,
            unused_website,
            unused_acl):
        request = self.post(
            '/base/getSSHUserActivity',
            {'user': 'example', 'tty': '', 'ip': ''},
        )
        command_results = [
            SimpleNamespace(returncode=0, stdout='', stderr=''),
            SimpleNamespace(returncode=0, stdout='1M\t/home/example\n', stderr=''),
            SimpleNamespace(returncode=0, stdout='', stderr=''),
        ]

        with mock.patch('baseTemplate.views.os.path.exists', return_value=True), \
                mock.patch('baseTemplate.views.subprocess.run', side_effect=command_results) as run:
            response = views.getSSHUserActivity(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(['ps', '-u', 'example', '-o', 'pid,ppid,tty,time,cmd', '--no-headers'], run.call_args_list[0].args[0])
        self.assertEqual(['du', '-sh', '--', '/home/example'], run.call_args_list[1].args[0])
        self.assertEqual(['w', '-h', 'example'], run.call_args_list[2].args[0])
        for call in run.call_args_list:
            self.assertNotIn('shell', call.kwargs)

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    def test_onboarding_rejects_command_injection_hostname(self, unused_acl):
        request = self.post(
            '/base/runonboarding',
            {'hostname': 'panel.example.com;id', 'rDNSCheck': 0},
        )

        with mock.patch('baseTemplate.views.ProcessUtilities.popenExecutioner') as execute:
            response = views.runonboarding(request)

        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(0, result['status'])
        execute.assert_not_called()
