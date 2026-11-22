"""Start, stop and restart act on a container only for the owner of the Docker site the container belongs to."""
import ast
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical.DockerSites import COMPOSE_DIRECTORY_LABEL, COMPOSE_PROJECT_LABEL, container_of_site

try:
    from .test_wordpress_entitlements import Response
except ImportError:
    from test_wordpress_entitlements import Response

HERE = Path(__file__).resolve().parent
ACTIONS = ('startContainer', 'stopContainer', 'restartContainer')
METHODS = {'startContainer': 'start', 'stopContainer': 'stop', 'restartContainer': 'restart'}
OWN = object()


class NotFound(Exception):
    pass


def load_views():
    """Run the real view module with its imports replaced by inert services."""
    services = {name: mock.Mock(name=name) for name in (
        'DockerSites', 'Administrator', 'ACLManager', 'docker', 'logging', 'loadLoginPage')}
    services['DockerSites'].DoesNotExist = NotFound
    services['docker'].errors.NotFound = NotFound
    namespace = dict(services, json=json, HttpResponse=Response,
                     redirect=lambda target: Response(status=302, location=target),
                     container_of_site=container_of_site)
    module = ast.parse((HERE / 'dockerviews.py').read_text())
    module.body = [node for node in module.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    exec(compile(module, 'dockerviews.py', 'exec'), namespace)
    return namespace, services


def request(body, method='POST', session=None):
    return SimpleNamespace(method=method, body=json.dumps(body).encode(),
                           session={'userID': 7} if session is None else session)


def call(action='stopContainer', body=None, admin=0, owns=1, labels=OWN, site_name='shop', method='POST'):
    namespace, services = load_views()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': admin}
    acl.checkOwnership.return_value = owns
    site = SimpleNamespace(SiteName=site_name, admin=SimpleNamespace(domain='shop.example'))
    services['DockerSites'].objects.get.return_value = site
    container = mock.Mock(labels={COMPOSE_PROJECT_LABEL: 'shop'} if labels is OWN else labels)
    services['docker'].from_env.return_value.containers.get.return_value = container
    body = {'name': 'shop', 'container_id': 'abc123'} if body is None else body
    reply = namespace[action](request(body, method))
    return SimpleNamespace(reply=reply, container=container, services=services, acl=acl,
                           answer=json.loads(reply.content) if reply.content.startswith(b'{') else None)


def acted(run):
    return [name for name in ('start', 'stop', 'restart') if getattr(run.container, name).called]


class OwnershipTests(unittest.TestCase):
    def test_the_owner_of_the_site_acts_on_its_container(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                run = call(action)
                self.assertEqual({'status': 1}, run.answer)
                self.assertEqual([METHODS[action]], acted(run))
                getattr(run.container, METHODS[action]).assert_called_once_with()

    def test_ownership_is_asked_for_the_website_of_the_stored_site_and_the_signed_in_user(self):
        run = call()
        run.services['DockerSites'].objects.get.assert_called_once_with(SiteName='shop')
        run.services['Administrator'].objects.get.assert_called_once_with(pk=7)
        run.acl.loadedACL.assert_called_once_with(7)
        run.acl.checkOwnership.assert_called_once_with(
            'shop.example', run.services['Administrator'].objects.get.return_value, {'admin': 0})

    def test_somebody_elses_site_is_refused_before_any_container_is_looked_up(self):
        for answer in (0, None, 2, '1', mock.Mock()):
            with self.subTest(answer=answer):
                run = call(owns=answer)
                self.assertEqual(0, run.answer['status'])
                self.assertEqual('Not authorized to access this container', run.answer['error_message'])
                run.services['docker'].from_env.assert_not_called()
                self.assertEqual([], acted(run))

    def test_a_site_that_does_not_exist_is_refused(self):
        namespace, services = load_views()
        services['DockerSites'].objects.get.side_effect = NotFound()
        reply = namespace['stopContainer'](request({'name': 'gone', 'container_id': 'abc123'}))
        self.assertEqual('Docker site not found', json.loads(reply.content)['error_message'])
        services['docker'].from_env.assert_not_called()


class ContainerTests(unittest.TestCase):
    """Owning one site gives no hold on containers of other sites, for the administrator as well."""

    def test_a_container_of_another_project_is_not_found(self):
        # The last two are containers started by hand: no project label, or no labels at all.
        others = ({COMPOSE_PROJECT_LABEL: 'myshop'}, {COMPOSE_PROJECT_LABEL: 'sho'},
                  {COMPOSE_PROJECT_LABEL: 'SHOP2'}, {COMPOSE_PROJECT_LABEL: ''},
                  {'com.docker.compose.service': 'shop'}, {}, None)
        for admin in (0, 1):
            for labels in others:
                for action in ACTIONS:
                    with self.subTest(admin=admin, labels=labels, action=action):
                        run = call(action, admin=admin, labels=labels)
                        self.assertEqual({'status': 0, 'error_message': 'Container not found'}, run.answer)
                        self.assertEqual([], acted(run))

    def test_the_container_is_looked_up_by_the_identifier_in_the_request(self):
        run = call(body={'name': 'shop', 'container_id': ' abc123 '})
        run.services['docker'].from_env.return_value.containers.get.assert_called_once_with('abc123')

    def test_a_container_that_does_not_exist_is_not_found(self):
        namespace, services = load_views()
        services['ACLManager'].checkOwnership.return_value = 1
        services['DockerSites'].objects.get.return_value = SimpleNamespace(
            SiteName='shop', admin=SimpleNamespace(domain='shop.example'))
        services['docker'].from_env.return_value.containers.get.side_effect = NotFound()
        reply = namespace['stopContainer'](request({'name': 'shop', 'container_id': 'abc123'}))
        self.assertEqual({'status': 0, 'error_message': 'Container not found'}, json.loads(reply.content))

    def test_a_site_named_before_the_lower_case_rule_still_reaches_its_containers(self):
        run = call(site_name='My Shop', labels={COMPOSE_PROJECT_LABEL: 'myshop'})
        self.assertEqual({'status': 1}, run.answer)

    def test_a_container_started_from_the_sites_own_directory_is_the_sites(self):
        for directory in ('/home/docker/shop.example', '/home/docker/shop.example/', '/home/docker/Shop.Example'):
            with self.subTest(directory=directory):
                run = call(labels={COMPOSE_PROJECT_LABEL: 'shop', COMPOSE_DIRECTORY_LABEL: directory})
                self.assertEqual({'status': 1}, run.answer)
                self.assertEqual(['stop'], acted(run))

    def test_a_container_of_a_project_of_the_same_name_started_elsewhere_is_not_found(self):
        # Somebody runs a Docker Compose project called "shop" beside the panel.
        for directory in ('/opt/shop', '/root/shop', '/home/docker/shop.example.org', '/home/docker',
                          '/home/docker/shop.example/sub', '/home/shop.example', ['/home/docker/shop.example'], 7):
            for admin in (0, 1):
                for action in ACTIONS:
                    with self.subTest(directory=directory, admin=admin, action=action):
                        run = call(action, admin=admin,
                                   labels={COMPOSE_PROJECT_LABEL: 'shop', COMPOSE_DIRECTORY_LABEL: directory})
                        self.assertEqual({'status': 0, 'error_message': 'Container not found'}, run.answer)
                        self.assertEqual([], acted(run))


class RequestTests(unittest.TestCase):
    def test_values_that_are_not_text_are_refused_without_a_lookup(self):
        for body in ({'name': ['shop'], 'container_id': 'abc123'}, {'name': 'shop', 'container_id': ['abc123']},
                     {'name': 'shop', 'container_id': ''}, {'name': 'shop', 'container_id': '  '},
                     {'name': 'shop'}, {'container_id': 'abc123'}, {'name': None, 'container_id': None},
                     {'name': {'a': 1}, 'container_id': 7}):
            with self.subTest(body=body):
                run = call(body=body)
                self.assertEqual(0, run.answer['status'])
                run.services['DockerSites'].objects.get.assert_not_called()
                run.services['docker'].from_env.assert_not_called()

    def test_a_body_that_is_not_an_object_is_refused(self):
        for body in ([], 'shop', 7, [None]):
            run = call(body=body)
            self.assertEqual(0, run.answer['status'])
            self.assertEqual([], acted(run))

    def test_only_post_acts(self):
        for method in ('GET', 'HEAD', 'PUT', 'DELETE'):
            run = call(method=method)
            self.assertEqual(b'Not allowed', run.reply.content)
            self.assertEqual([], acted(run))
            run.services['DockerSites'].objects.get.assert_not_called()

    def test_without_a_session_the_caller_is_sent_to_the_login_page(self):
        namespace, services = load_views()
        reply = namespace['stopContainer'](
            SimpleNamespace(method='POST', body=b'{"name": "shop", "container_id": "abc123"}', session={}))
        self.assertEqual(302, reply.status_code)
        services['DockerSites'].objects.get.assert_not_called()


class RequestForgeryTests(unittest.TestCase):
    """The views take part in the panel's request-forgery check and the page sends its token."""

    def decorators(self, filename):
        found = {}
        for node in ast.parse((HERE / filename).read_text()).body:
            if isinstance(node, ast.FunctionDef) and node.name in ACTIONS:
                found[node.name] = [ast.dump(decorator) for decorator in node.decorator_list]
        return found

    def test_no_view_is_exempt(self):
        for filename in ('dockerviews.py', 'views.py'):
            found = self.decorators(filename)
            self.assertEqual(set(ACTIONS), set(found), filename)
            for name, decorators in found.items():
                self.assertFalse([text for text in decorators if 'csrf_exempt' in text], (filename, name))

    def test_the_loaded_views_carry_no_exemption_mark(self):
        namespace, services = load_views()
        for name in ACTIONS:
            self.assertFalse(getattr(namespace[name], 'csrf_exempt', False), name)

    def test_the_page_sends_the_token_with_every_action(self):
        script = (HERE / 'static/websiteFunctions/DockerContainers.js').read_text()
        action = script[script.index('$scope.cAction = function'):]
        action = action[:action.index('$scope.setSelectedContainer')]
        for name in ACTIONS:
            self.assertIn('url += "%s"' % name, action)
        self.assertTrue(re.search(r"headers:\s*\{\s*'X-CSRFToken':\s*getCookie\('csrftoken'\)", action))
        self.assertIn('$http.post(url, data, config)', action)


if __name__ == '__main__':
    unittest.main(verbosity=2)
