"""The Version Management page reads and saves automatic update settings for administrators only."""
import json
from unittest.mock import patch

from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve

from baseTemplate import views

STATE = {'settings': {'mode': 'notify', 'hour': 4, 'email': 'admin@example.com'}, 'installed': None,
         'release': None, 'checked': None, 'error': '', 'summary': 'Version 3.0.10 is available.',
         'attempt': None, 'timer': 'active', 'server_time': '04:10', 'timezone': 'UTC'}
PROGRAM = '/usr/local/CyberCP/bin/python -I /usr/local/CyberCP/plogical/autoUpdate.py '


class AutoUpdateRouteTests(SimpleTestCase):
    def call(self, body, admin=1, session=True, method='post', output=None):
        factory = RequestFactory()
        request = factory.get('/base/autoUpdate') if method == 'get' else \
            factory.post('/base/autoUpdate', data=json.dumps(body), content_type='application/json')
        request.session = {'userID': 5} if session else {}
        result = (1, 'noise before\n' + json.dumps(STATE) + '\n') if output is None else output
        with patch.object(views.ACLManager, 'loadedACL', return_value={'admin': admin}), \
                patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=result) as helper:
            response = resolve('/base/autoUpdate').func(request)
        return response, helper

    def test_status_and_check_run_the_fixed_commands(self):
        for action in ('status', 'check'):
            response, helper = self.call({'action': action})
            self.assertEqual({'status': 1, 'autoUpdate': STATE}, json.loads(response.content))
            helper.assert_called_once_with(PROGRAM + action, shell=False, retRequired=True)

    def test_saved_settings_reach_the_root_helper_as_hexadecimal_only(self):
        response, helper = self.call({'action': 'save', 'mode': 'install', 'hour': 2, 'email': 'a.b+c@example.com'})
        self.assertEqual(1, json.loads(response.content)['status'])
        command = helper.call_args[0][0]
        self.assertRegex(command, '^' + PROGRAM.replace('.', r'\.') + 'configure [0-9a-f]+$')
        self.assertEqual({'mode': 'install', 'hour': 2, 'email': 'a.b+c@example.com'},
                         json.loads(bytes.fromhex(command.rsplit(' ', 1)[1]).decode()))

    def test_invalid_settings_never_reach_the_root_helper(self):
        for body in ({'action': 'save', 'mode': 'install', 'hour': 2, 'email': 'a@example.com; id'},
                     {'action': 'save', 'mode': 'install; id', 'hour': 2, 'email': ''},
                     {'action': 'save', 'mode': 'install', 'hour': '2; id', 'email': ''},
                     {'action': 'save', 'mode': 'install'},
                     {'action': 'install'}, {'action': 'configure 7b7d'}, {}, [], 'text'):
            with self.subTest(body):
                response, helper = self.call(body)
                self.assertEqual(0, json.loads(response.content)['status'])
                helper.assert_not_called()

    def test_only_a_signed_in_administrator_may_use_it(self):
        response, helper = self.call({'action': 'status'}, admin=0)
        helper.assert_not_called()
        self.assertNotIn(b'autoUpdate', response.content)
        response, helper = self.call({'action': 'status'}, session=False)
        helper.assert_not_called()
        self.assertEqual(0, json.loads(response.content)['status'])
        response, helper = self.call({'action': 'status'}, method='get')
        helper.assert_not_called()
        self.assertEqual(405, response.status_code)

    def test_a_refused_or_unreadable_answer_is_reported(self):
        for output, expected in (((0, json.dumps({'error': 'Choose an hour from 0 to 23.'})), 'Choose an hour from 0 to 23.'),
                                 ((1, 'not json'), 'Automatic update settings are unavailable.'),
                                 ((1, ''), 'Automatic update settings are unavailable.'),
                                 (0, 'Automatic update settings are unavailable.'),
                                 ((1, '[]'), 'Automatic update settings are unavailable.')):
            with self.subTest(output):
                response, _ = self.call({'action': 'status'}, output=output)
                self.assertEqual({'status': 0, 'error_message': expected}, json.loads(response.content))

    def test_page_has_the_settings_card_with_text_only_bindings(self):
        page = get_template('baseTemplate/versionManagment.html').template.source
        start = page.index('id="autoUpdateCard"')
        card = page[start:page.index('<div class="alert alert-warning" role="alert" ng-hide="updateError"', start)]
        for expected in ('ng-model="autoUpdate.mode"', '<option value="off">', '<option value="notify">',
                         '<option value="install">', 'ng-click="saveAutoUpdate()"', 'ng-click="checkAutoUpdate()"',
                         'ng-bind="autoUpdateState.summary"', 'ng-bind="autoUpdateError"'):
            self.assertEqual(1, card.count(expected), expected)
        self.assertNotIn('ng-bind-html', card)
        self.assertNotIn('{$', card)
