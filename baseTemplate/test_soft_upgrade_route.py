from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve

from baseTemplate import views


class UpgradePageRouteTests(SimpleTestCase):
    def test_version_page_renders_resume_only_for_its_session(self):
        path = '/base/versionManagment'
        page = resolve(path)
        self.assertIs(page.func, views.versionManagment)
        self.assertIs(resolve('/base/UpgradeStatus').func, views.upgradeStatus)

        def render_page(proc):
            return HttpResponse(get_template(proc.templateName).render(proc.data))

        with patch.object(views.requests, 'get') as get, \
                patch.object(views.logging.CyberCPLogFileWriter, 'writeToFile'), \
                patch.object(views.ProcessUtilities, 'outputExecutioner', return_value='installed\n'), \
                patch.object(views.httpProc, 'render', autospec=True, side_effect=render_page):
            for session, expected in (({'softUpgradeRun': 'a' * 32}, '1'), ({}, '0')):
                with self.subTest(session=session):
                    get.side_effect = [Mock(json=lambda: {'version': '3.0', 'build': '8'}),
                                       Mock(json=lambda: [{'sha': 'available'}])]
                    request = RequestFactory().get(path)
                    request.session = {'userID': 1, **session}
                    response = page.func(request)
                    self.assertContains(response, 'data-resume-upgrade="%s"' % expected, count=1)
