"""The Docker and container installers start only from the panel's own POST, and never over a working Docker."""
import ast
import json
from pathlib import Path
import unittest
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory
from django.views.decorators.http import require_POST

ROOT = Path(__file__).resolve().parents[1]


def load(path, names, scope):
    tree = ast.parse((ROOT / path).read_text())
    tree.body = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(tree.body) == len(names), path
    exec(compile(tree, path, 'exec'), scope)
    return scope


def request(method, path):
    if method == 'post':
        made = RequestFactory().post(path, data='{}', content_type='application/json')
    else:
        made = getattr(RequestFactory(), method)(path)
    made.session = {'userID': 7}
    return made


class InstallDockerTests(unittest.TestCase):
    def setUp(self):
        from django.conf import settings
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET='utf-8')
        self.acl = mock.Mock()
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.loadErrorJson.return_value = HttpResponse('refused')
        self.manager = mock.Mock()
        self.ready = mock.Mock(return_value=False)
        self.view = load('dockerManager/views.py', ('installDocker',), {
            'require_POST': require_POST, 'json': json, 'HttpResponse': HttpResponse,
            'ACLManager': self.acl, 'ContainerManager': self.manager, 'dockerIsReady': self.ready,
        })['installDocker']

    def test_a_link_or_an_image_tag_cannot_start_the_installer(self):
        for method in ('get', 'head', 'options'):
            with self.subTest(method=method):
                self.assertEqual(405, self.view(request(method, '/docker/installDocker')).status_code)
        self.manager.assert_not_called()
        self.acl.loadedACL.assert_not_called()

    def test_the_panels_own_post_starts_the_installer_when_docker_is_missing(self):
        reply = json.loads(self.view(request('post', '/docker/installDocker')).content)
        self.assertEqual({'status': 1, 'error_message': 'None'}, reply)
        self.manager.assert_called_once_with(7, 'submitInstallDocker')
        self.manager.return_value.start.assert_called_once_with()

    def test_a_working_docker_is_never_installed_over(self):
        self.ready.return_value = True
        reply = json.loads(self.view(request('post', '/docker/installDocker')).content)
        self.assertEqual(0, reply['status'])
        self.assertEqual('Docker is already installed.', reply['error_message'])
        self.manager.assert_not_called()

    def test_only_an_administrator_reaches_the_installer(self):
        self.acl.loadedACL.return_value = {'admin': 0}
        self.assertEqual(b'refused', self.view(request('post', '/docker/installDocker')).content)
        self.manager.assert_not_called()
        self.ready.assert_not_called()


class DockerStateTests(unittest.TestCase):
    """Ready means what the Docker pages mean by it: the program is there and the daemon answers."""

    def state(self, installed, answers):
        engine = mock.Mock()
        if not answers:
            engine.from_env.return_value.ping.side_effect = RuntimeError('daemon is not running')
        files = mock.Mock()
        files.path.exists.return_value = installed
        scope = load('dockerManager/decorators.py', ('dockerDaemonAnswers', 'dockerIsReady'), {
            'os': files, 'docker': engine, 'logging': mock.Mock(), 'dockerInstallPath': '/usr/bin/docker'})
        ready = scope['dockerIsReady']()
        if installed:
            files.path.exists.assert_called_once_with('/usr/bin/docker')
        return ready

    def test_ready_only_when_installed_and_answering(self):
        self.assertTrue(self.state(True, True))
        self.assertFalse(self.state(True, False))
        self.assertFalse(self.state(False, True))
        self.assertFalse(self.state(False, False))

    def test_the_docker_pages_use_the_same_two_checks(self):
        source = (ROOT / 'dockerManager/decorators.py').read_text()
        wrapper = source[source.index('def preDockerRun('):]
        self.assertIn('if not os.path.exists(dockerInstallPath):', wrapper)
        self.assertIn('if not dockerDaemonAnswers():', wrapper)


class ContainerInstallTests(unittest.TestCase):
    def setUp(self):
        from django.conf import settings
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET='utf-8')
        self.acl = mock.Mock()
        self.acl.loadedACL.return_value = {'admin': 1}
        self.manager = mock.Mock()
        self.view = load('containerization/views.py', ('submitContainerInstall',), {
            'require_POST': require_POST, 'json': json, 'HttpResponse': HttpResponse,
            'ACLManager': self.acl, 'ContainerManager': self.manager,
        })['submitContainerInstall']

    def test_a_link_cannot_start_the_package_installation(self):
        for method in ('get', 'head'):
            with self.subTest(method=method):
                made = request(method, '/container/submitContainerInstall')
                self.assertEqual(405, self.view(made).status_code)
        self.manager.assert_not_called()

    def test_the_panels_own_post_still_starts_it(self):
        made = request('post', '/container/submitContainerInstall')
        self.assertEqual(1, json.loads(self.view(made).content)['status'])
        self.manager.assert_called_once_with(made, None, 'submitContainerInstall')
        self.manager.return_value.start.assert_called_once_with()


class PageScriptTests(unittest.TestCase):
    """Both install buttons already send a POST that carries the CSRF token."""

    def assert_posts_with_token(self, path, url):
        script = (ROOT / path).read_text(encoding='utf-8')
        start = script.index('url = "%s";' % url)
        call = script[start:script.index('$http.post(url, data, config)', start) + 40]
        self.assertIn("'X-CSRFToken': getCookie('csrftoken')", call)
        self.assertNotIn('$http.get', call)

    def test_install_buttons_post_with_the_token(self):
        self.assert_posts_with_token('dockerManager/static/dockerManager/dockerManager.js',
                                     '/docker/installDocker')
        self.assert_posts_with_token('containerization/static/containerization/containerization.js',
                                     '/container/submitContainerInstall')


if __name__ == '__main__':
    unittest.main(verbosity=2)
