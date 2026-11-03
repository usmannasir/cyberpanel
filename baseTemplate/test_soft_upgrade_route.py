from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve

from baseTemplate import views


class UpgradePageRouteTests(SimpleTestCase):
    @staticmethod
    def response(data=None, error=None):
        response = Mock()
        response.json.return_value = data
        response.raise_for_status.side_effect = error
        return response

    def check_page(self, responses, unavailable=False, version_available=True):
        path = '/base/versionManagment'
        page = resolve(path)
        self.assertIs(page.func, views.versionManagment)
        self.assertIs(resolve('/base/UpgradeStatus').func, views.upgradeStatus)
        contexts = []

        def render_page(proc):
            contexts.append(proc.data)
            return HttpResponse(get_template(proc.templateName).render(proc.data))

        with patch.object(views.requests, 'get') as get, \
                patch.object(views.ProcessUtilities, 'outputExecutioner',
                             return_value='b' * 40 + '\n'), \
                patch.object(views.httpProc, 'render', autospec=True, side_effect=render_page):
            for session, expected in (({'softUpgradeRun': 'a' * 32}, '1'), ({}, '0')):
                with self.subTest(session=session):
                    get.reset_mock()
                    get.side_effect = responses
                    request = RequestFactory().get(path)
                    request.session = {'userID': 1, **session}
                    response = page.func(request)
                    self.assertContains(response, 'data-resume-upgrade="%s"' % expected, count=1)
                    self.assertContains(response, 'id="branchSelect"', count=1)
                    self.assertContains(response, 'ng-click="upgrade()"', count=1)
                    self.assertContains(response, '<option value="stable">stable</option>', count=1)
                    release = 'v%s.%s' % (views.VERSION, views.BUILD)
                    self.assertContains(response, '<option value="%s">%s</option>' % (release, release), count=1)
                    self.assertEqual(contexts[-1]['currentRelease'], release)
                    self.assertEqual(contexts[-1]['currentVersion'], views.VERSION)
                    self.assertEqual(contexts[-1]['build'], str(views.BUILD))
                    self.assertEqual(contexts[-1]['Currentcomt'], 'b' * 40)
                    self.assertEqual(contexts[-1]['releaseMetadataUnavailable'], unavailable)
                    for call in get.call_args_list:
                        self.assertEqual(call.kwargs, {'timeout': (3, 5)})
                    if unavailable:
                        self.assertContains(response, 'Latest release information is temporarily unavailable.')
                        self.assertContains(response, 'Unavailable')
                        self.assertFalse(contexts[-1]['Notecheck'])
                        self.assertIsNone(contexts[-1]['latestcomit'])
                    else:
                        self.assertNotContains(response, 'Latest release information is temporarily unavailable.')
                        self.assertEqual(contexts[-1]['latestcomit'], 'a' * 40)
                        self.assertTrue(contexts[-1]['Notecheck'])
                    if version_available:
                        self.assertEqual(contexts[-1]['latestVersion'], '3.0')
                        self.assertEqual(contexts[-1]['latestBuild'], '8')
                    if not version_available:
                        self.assertIsNone(contexts[-1]['latestVersion'])
                        self.assertIsNone(contexts[-1]['latestBuild'])
                        self.assertEqual(get.call_count, 1)

    def version_response(self):
        return self.response({'version': '3.0', 'build': '8'})

    def test_version_page_renders_resume_only_for_its_session(self):
        self.check_page([self.version_response(), self.response([{'sha': 'a' * 40}])])

    def test_github_rate_limit_403_preserves_routed_resume_and_controls(self):
        self.check_page([self.version_response(), self.response(
            {'message': 'API rate limit exceeded'}, views.requests.HTTPError('403'))],
            unavailable=True)

    def test_github_nonlist_empty_or_invalid_commit_preserves_page(self):
        for payload in ({'message': 'rate limit'}, [], [None], [{'sha': 'invalid'}]):
            with self.subTest(payload=payload):
                self.check_page([self.version_response(), self.response(payload)], unavailable=True)

    def test_github_timeout_preserves_page(self):
        self.check_page([self.version_response(), views.requests.Timeout()], unavailable=True)

    def test_version_timeout_or_http_error_preserves_page(self):
        for response in (views.requests.Timeout(),
                         self.response({}, views.requests.HTTPError('503'))):
            with self.subTest(response=type(response).__name__):
                self.check_page([response], unavailable=True, version_available=False)

    def test_version_invalid_json_preserves_page(self):
        response = self.response()
        response.json.side_effect = ValueError('Invalid JSON')
        self.check_page([response], unavailable=True, version_available=False)

    def test_invalid_release_shape_refuses_commit_lookup_but_preserves_page(self):
        for payload in (None, [], {}, {'version': '3.0'},
                        {'version': '3.0?bad', 'build': '8'},
                        {'version': '3.0', 'build': True}):
            with self.subTest(payload=payload):
                self.check_page([self.response(payload)], unavailable=True, version_available=False)


    def test_untrusted_local_version_cannot_form_a_fallback_option(self):
        contexts = []
        def render_page(proc):
            contexts.append(proc.data)
            return HttpResponse(get_template(proc.templateName).render(proc.data))
        request = RequestFactory().get('/base/versionManagment')
        request.session = {'userID': 1, 'softUpgradeRun': 'a' * 32}
        with patch.object(views, 'VERSION', "invalid'branch"), \
                patch.object(views.requests, 'get', side_effect=views.requests.Timeout()), \
                patch.object(views.ProcessUtilities, 'outputExecutioner', return_value='b' * 40), \
                patch.object(views.httpProc, 'render', autospec=True, side_effect=render_page):
            response = resolve('/base/versionManagment').func(request)
        self.assertIsNone(contexts[0]['currentRelease'])
        self.assertContains(response, '<option value="stable">stable</option>', count=1)
        self.assertContains(response, 'data-resume-upgrade="1"', count=1)
        self.assertContains(response, 'ng-init="branchSelect=\'stable\'"', count=1)
