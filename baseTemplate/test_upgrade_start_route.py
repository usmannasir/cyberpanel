"""Starting and following an upgrade from the Version Management page."""
import json
import time
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase

from baseTemplate import views

JOB = 'a' * 32


class UpgradeStartTests(SimpleTestCase):
    def start(self, body, session=None, helper_answer=None, csf=False, admin=1):
        payload = body if isinstance(body, (str, bytes)) else json.dumps(body)
        request = RequestFactory().post('/base/upgrade', data=payload, content_type='application/json')
        request.session = dict({'userID': 1}, **(session or {}))
        with patch.object(views.ACLManager, 'loadedACL', return_value={'admin': admin}), \
                patch.object(views.ACLManager, 'loadErrorJson', return_value=HttpResponse('{"denied": 1}')), \
                patch('plogical.softUpgrade.installed_order', return_value=(3, 0, 9)), \
                patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=helper_answer) as helper, \
                patch('plogical.applicationInstaller.ApplicationInstaller') as installer, \
                patch.object(views.os.path, 'lexists', return_value=csf):
            response = views.upgrade(request)
        return json.loads(response.content), request.session, installer, helper

    def test_a_newer_or_the_installed_release_starts_one_run(self):
        for branch in ('v3.0.10', 'v3.0.9', 'stable'):
            answer, session, installer, helper = self.start({'branchSelect': branch})
            self.assertEqual({'upgrade': 1}, answer)
            self.assertRegex(session['softUpgradeRun'], '^[0-9a-f]{32}$')
            installer.assert_called_once_with('UpgradeCP', {'branchSelect': branch, 'upgradeRun': session['softUpgradeRun']})
            installer.return_value.start.assert_called_once_with()
            helper.assert_not_called()

    def test_an_older_release_or_an_unreadable_request_starts_nothing(self):
        for body, expected in (({'branchSelect': 'v3.0.8'}, 'older than the installed one'),
                               ({'branchSelect': 'v2.4.8'}, 'older than the installed one'),
                               ({'branchSelect': 'v3.0.10; id'}, 'Select a stable CyberPanel release branch'),
                               ({'branchSelect': 7}, 'Select a CyberPanel release.'),
                               ({}, 'Select a CyberPanel release.'),
                               ('not json', 'Select a CyberPanel release.'),
                               ('[]', 'Select a CyberPanel release.')):
            with self.subTest(body):
                answer, session, installer, _ = self.start(body)
                self.assertEqual(0, answer['upgrade'])
                self.assertIn(expected, answer['error_message'])
                self.assertNotIn('softUpgradeRun', session)
                installer.assert_not_called()

    def test_a_second_click_joins_the_running_upgrade(self):
        for state in ('starting', 'running'):
            answer, session, installer, helper = self.start(
                {'branchSelect': 'v3.0.10'}, {'softUpgradeRun': JOB, 'softUpgradeStarted': 0},
                (1, json.dumps({'state': state})))
            self.assertEqual({'upgrade': 1, 'resumed': 1}, answer)
            self.assertEqual(JOB, session['softUpgradeRun'])
            installer.assert_not_called()
            self.assertTrue(helper.call_args[0][0].endswith('softUpgrade.py --status ' + JOB))
        # The launcher has not written its record yet, or cannot be asked right now.
        for helper_answer, started in (((1, json.dumps({'state': 'missing'})), time.time()), ((0, ''), 0), (0, 0)):
            answer, session, installer, _ = self.start(
                {'branchSelect': 'v3.0.10'}, {'softUpgradeRun': JOB, 'softUpgradeStarted': started}, helper_answer)
            self.assertEqual({'upgrade': 1, 'resumed': 1}, answer)
            installer.assert_not_called()

    def test_a_finished_or_lost_run_does_not_block_a_new_one(self):
        for helper_answer, session in (((1, json.dumps({'state': 'complete'})), {'softUpgradeRun': JOB, 'softUpgradeStarted': 0}),
                                       ((1, json.dumps({'state': 'failed', 'message': 'x'})), {'softUpgradeRun': JOB, 'softUpgradeStarted': 0}),
                                       ((1, json.dumps({'state': 'missing'})), {'softUpgradeRun': JOB, 'softUpgradeStarted': 0}),
                                       ((1, 'not json'), {'softUpgradeRun': JOB, 'softUpgradeStarted': 0}),
                                       (None, {'softUpgradeRun': '../../x', 'softUpgradeStarted': 0})):
            with self.subTest(helper_answer):
                answer, new_session, installer, _ = self.start({'branchSelect': 'v3.0.10'}, session, helper_answer)
                self.assertEqual({'upgrade': 1}, answer)
                self.assertNotEqual(session['softUpgradeRun'], new_session['softUpgradeRun'])
                installer.assert_called_once()

    def test_only_an_administrator_without_csf_may_start(self):
        answer, session, installer, _ = self.start({'branchSelect': 'v3.0.10'}, admin=0)
        self.assertEqual({'denied': 1}, answer)
        installer.assert_not_called()
        answer, session, installer, _ = self.start({'branchSelect': 'v3.0.10'}, csf=True)
        self.assertEqual(0, answer['upgrade'])
        installer.assert_not_called()


class UpgradeStatusTests(SimpleTestCase):
    def poll(self, state, method='post'):
        factory = RequestFactory()
        request = factory.get('/base/UpgradeStatus') if method == 'get' else \
            factory.post('/base/UpgradeStatus', data='{}', content_type='application/json')
        request.session = {'userID': 1, 'softUpgradeRun': JOB, 'softUpgradeStarted': 0}
        with patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=(1, json.dumps(state))), \
                patch.object(views.os, 'open', side_effect=OSError('no log')):
            response = views.upgradeStatus(request)
        return response, request.session

    def test_a_finished_run_is_reported_once_and_then_forgotten(self):
        response, session = self.poll({'state': 'complete'})
        self.assertEqual((1, 1), (json.loads(response.content)['finished'], json.loads(response.content)['upgradeStatus']))
        self.assertEqual({'userID': 1}, session)
        response, session = self.poll({'state': 'failed', 'message': 'Upgrade exited with code 1.'})
        answer = json.loads(response.content)
        self.assertEqual((1, 0, 'Upgrade exited with code 1.', ''),
                         (answer['finished'], answer['upgradeStatus'], answer['error_message'], answer['upgradeLog']))
        self.assertEqual({'userID': 1}, session)

    def test_a_running_upgrade_stays_attached_to_the_session(self):
        response, session = self.poll({'state': 'running', 'pid': 1, 'start_ticks': '1'})
        self.assertEqual(0, json.loads(response.content)['finished'])
        self.assertEqual(JOB, session['softUpgradeRun'])

    def test_status_is_not_answered_to_a_plain_page_request(self):
        response, session = self.poll({'state': 'running'}, method='get')
        self.assertEqual(405, response.status_code)
        self.assertEqual(0, json.loads(response.content)['upgradeStatus'])


class VersionRowTests(SimpleTestCase):
    def call(self, session, admin=1):
        request = RequestFactory().get('/base/upgradeVersion')
        request.session = session
        with patch.object(views.ACLManager, 'loadedACL', return_value={'admin': admin}), \
                patch.object(views.ACLManager, 'loadErrorJson', return_value=HttpResponse('denied')), \
                patch.object(views, 'version') as rows, patch.object(views.requests, 'get') as get, \
                patch.object(views.logging.CyberCPLogFileWriter, 'writeToFile'):
            get.return_value.json.return_value = {'version': '3.0', 'build': 10}
            response = views.upgradeVersion(request)
        return response, rows, get

    def test_version_row_is_changed_for_an_administrator_only(self):
        response, rows, get = self.call({'userID': 1})
        self.assertEqual(b'Version upgrade OK.', response.content)
        rows.objects.get.return_value.save.assert_called_once_with()
        self.assertEqual({'timeout': (3, 5)}, get.call_args[1])
        for session, admin in (({}, 1), ({'userID': 2}, 0)):
            response, rows, get = self.call(session, admin)
            rows.objects.get.assert_not_called()
            get.assert_not_called()


class VersionPageTests(SimpleTestCase):
    def page(self, latest_build, latest_tree, current_tree='c' * 40, session=None):
        contexts = []

        def render_page(proc):
            contexts.append(proc.data)
            return HttpResponse(get_template(proc.templateName).render(proc.data))

        def response(data):
            answer = Mock()
            answer.json.return_value = data
            return answer

        commit = {'sha': 'a' * 40}
        if latest_tree:
            commit['commit'] = {'tree': {'sha': latest_tree}}
        request = RequestFactory().get('/base/versionManagment')
        request.session = dict({'userID': 1}, **(session or {}))
        with patch.object(views, 'VERSION', '3.0'), patch.object(views, 'BUILD', 9), \
                patch.object(views.requests, 'get', side_effect=[response({'version': '3.0', 'build': latest_build}), response([commit])]), \
                patch.object(views.ProcessUtilities, 'outputExecutioner',
                             side_effect=lambda command: (current_tree if 'HEAD^{tree}' in command else 'b' * 40) + '\n'), \
                patch.object(views.httpProc, 'render', autospec=True, side_effect=render_page):
            page = views.versionManagment(request)
        return page, contexts[0]

    def test_a_newer_release_is_offered_first_and_selected(self):
        page, context = self.page(10, None)
        self.assertEqual(('v3.0.10', 'v3.0.10'), (context['latestRelease'], context['defaultRelease']))
        self.assertContains(page, 'ng-init="branchSelect=\'v3.0.10\'"', count=1)
        text = page.content.decode()
        self.assertLess(text.index('<option value="v3.0.10">'), text.index('<option value="v3.0.9">'))
        self.assertLess(text.index('<option value="v3.0.9">'), text.index('<option value="stable">'))
        self.assertContains(page, 'data-installed-release="v3.0.9"', count=1)

    def test_an_older_or_equal_latest_release_keeps_the_installed_one_selected(self):
        for build in (9, 8):
            page, context = self.page(build, None)
            self.assertIsNone(context['latestRelease'])
            self.assertEqual('v3.0.9', context['defaultRelease'])
            self.assertContains(page, '<option value="v3.0.9">v3.0.9</option>', count=1)

    def test_same_files_under_another_commit_are_not_reported_as_outdated(self):
        page, context = self.page(9, 'c' * 40)
        self.assertFalse(context['Notecheck'])
        self.assertNotContains(page, 'Latest commit does not match')
        page, context = self.page(9, 'd' * 40)
        self.assertTrue(context['Notecheck'])
        page, context = self.page(9, None)
        self.assertTrue(context['Notecheck'])
