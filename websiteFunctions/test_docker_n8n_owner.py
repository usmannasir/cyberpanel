"""A new n8n site is reachable only through the website, and only after the panel has made its owner account."""
import json
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import DOCKER_APPS, DockerDeploymentError, n8n_password_problem
from websiteFunctions.test_docker_apps import make_site

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager

try:
    import requests
except ImportError:
    requests = None

try:
    import yaml
except ImportError:
    yaml = None


class Reply:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body

    def json(self):
        if isinstance(self.body, str):
            raise ValueError('not JSON')
        return self.body


STARTING = Reply(200, 'n8n is starting up. Please wait')
CREATED = Reply(200, {'data': {'id': 'fixture', 'email': 'admin@example.com', 'isOwner': True}})


def create_owner(replies, **data):
    site = make_site('n8n')
    site.data.update(data)
    session = mock.Mock()
    session.post.side_effect = replies
    with mock.patch('requests.Session', return_value=session), \
            mock.patch.object(docker_sites.time, 'sleep') as sleep, \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        try:
            return site.create_n8n_owner(attempts=4, delay=2), session, sleep
        except DockerDeploymentError as error:
            return error, session, sleep


@unittest.skipIf(requests is None, 'requests not installed')
class OwnerCreationTests(unittest.TestCase):
    def test_the_owner_is_created_on_loopback_with_the_values_from_the_form(self):
        result, session, sleep = create_owner([CREATED])
        self.assertIs(True, result)
        session.post.assert_called_once_with(
            'http://127.0.0.1:11007/rest/owner/setup',
            json={'email': 'admin@example.com', 'firstName': 'cyberpanel', 'lastName': 'Admin',
                  'password': 'AdminPass123'},
            timeout=30)
        self.assertIs(False, session.trust_env)
        sleep.assert_not_called()

    def test_it_waits_while_n8n_is_not_listening_or_still_starting(self):
        result, session, sleep = create_owner(
            [requests.ConnectionError('refused'), STARTING, requests.Timeout('slow'), CREATED])
        self.assertIs(True, result)
        self.assertEqual(4, session.post.call_count)
        self.assertEqual([mock.call(2)] * 3, sleep.call_args_list)

    def test_an_instance_somebody_else_claimed_fails_the_deployment(self):
        result, session, sleep = create_owner(
            [Reply(400, {'code': 400, 'message': 'Instance owner already setup'})])
        self.assertIsInstance(result, DockerDeploymentError)
        self.assertIn('Instance owner already setup', str(result))
        self.assertEqual(1, session.post.call_count)

    def test_values_n8n_refuses_fail_the_deployment_with_its_reason(self):
        result, session, sleep = create_owner(
            [Reply(400, {'code': 'custom', 'message': 'Password must contain at least 1 number.'})])
        self.assertIsInstance(result, DockerDeploymentError)
        self.assertIn('Password must contain at least 1 number.', str(result))

    def test_an_answer_that_is_not_a_created_owner_is_never_taken_for_one(self):
        for reply in (Reply(200, {'status': 'ok'}), Reply(200, []), Reply(200, {'data': None}),
                      Reply(201, {'data': {'id': 'x'}}), Reply(500, {'code': 0, 'message': 'value too long'}),
                      Reply(404, {'message': 'Cannot POST /rest/owner/setup'})):
            with self.subTest(status=reply.status_code, body=reply.body):
                result, session, sleep = create_owner([reply])
                self.assertIsInstance(result, DockerDeploymentError)

    def test_an_instance_that_never_becomes_ready_fails_the_deployment(self):
        result, session, sleep = create_owner([STARTING] * 4)
        self.assertIsInstance(result, DockerDeploymentError)
        self.assertEqual(4, session.post.call_count)

    def test_the_name_is_one_n8n_accepts_and_is_never_empty(self):
        for given, sent in (('u' * 40, 'u' * 32), ('john.doe_1', 'johndoe_1'), ('<b>admin</b>', 'badminb'),
                            ('http://x.test/a', 'httpxtesta'), (' Jane Doe ', 'Jane Doe'),
                            ('', 'Administrator'), (None, 'Administrator'), ('...', 'Administrator')):
            with self.subTest(given=given):
                result, session, sleep = create_owner([CREATED], adminUser=given)
                self.assertEqual(sent, session.post.call_args[1]['json']['firstName'])


class PasswordRuleTests(unittest.TestCase):
    def test_passwords_n8n_accepts(self):
        for password in ('AdminPass123', 'A1aaaaaa', 'P@ss w0rd$"quote', 'A1' + 'a' * 62):
            self.assertIsNone(n8n_password_problem(password), password)

    def test_passwords_n8n_refuses(self):
        for password in ('', 'weak', 'Short1A', 'NoDigitsHere', 'alllowercase1', 'A1' + 'a' * 63,
                         None, 12345678, ['AdminPass123']):
            self.assertIn('8 to 64 characters', n8n_password_problem(password), password)


def deploy(app, first_run=None):
    """Run the real deployment with every command, file and container faked."""
    site = make_site(app)
    site.JobID = site.data['JobID']
    events = []

    def output(command, *args):
        events.append(command)
        return 'Usage: docker [OPTIONS] COMMAND' if command == 'docker --help' else (1, '')

    def execute(command, *args):
        events.append(command)
        return 1

    def owner():
        events.append('OWNER')
        if first_run is not None:
            raise first_run
        return True

    utilities = SimpleNamespace(installUtilities=mock.Mock())
    utilities.installUtilities.reStartLiteSpeedSocket.side_effect = lambda: events.append('RESTART')
    with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
            mock.patch.object(docker_sites.ProcessUtilities, 'executioner', side_effect=execute), \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value=0), \
            mock.patch('plogical.DockerSites.os.path.exists', return_value=False), \
            mock.patch('builtins.open', mock.mock_open()), \
            mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities}), \
            mock.patch.object(site, 'verify_system_resources'), \
            mock.patch.object(site, 'check_container_health', return_value=True), \
            mock.patch.object(site, 'monitor_deployment'), \
            mock.patch.object(site, 'log_deployment_metrics'), \
            mock.patch.object(site, 'cleanup_failed_deployment') as cleanup, \
            mock.patch.object(site, 'create_n8n_owner', side_effect=owner), \
            mock.patch.object(docker_sites.time, 'sleep'), \
            mock.patch.object(docker_sites.logging, 'statusWriter') as status, \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        result = site.DeployComposeApp(app)
    messages = [call[0][1] for call in status.call_args_list]
    return SimpleNamespace(result=result, events=events, messages=messages, cleanup=cleanup)


def position(events, text):
    return next(index for index, event in enumerate(events) if text in event)


class DeploymentOrderTests(unittest.TestCase):
    def test_n8n_declares_its_first_run_step(self):
        self.assertEqual('create_n8n_owner', DOCKER_APPS['n8n']['firstRun'])
        self.assertTrue(callable(getattr(docker_sites.Docker_Sites, DOCKER_APPS['n8n']['firstRun'])))
        for app in ('WordPress', 'Hermes'):
            self.assertNotIn('firstRun', DOCKER_APPS[app])

    def test_the_website_is_pointed_at_n8n_only_after_the_owner_exists(self):
        run = deploy('n8n')
        self.assertIs(True, run.result)
        started = position(run.events, ' up -d')
        owner = position(run.events, 'OWNER')
        self.assertLess(started, owner)
        self.assertLess(owner, position(run.events, 'SetupProxy'))
        self.assertLess(owner, position(run.events, 'SetupAppVhost'))
        self.assertLess(owner, position(run.events, 'RESTART'))
        self.assertTrue(any('[200]' in message for message in run.messages))

    def test_without_an_owner_the_site_is_removed_and_never_published(self):
        run = deploy('n8n', first_run=DockerDeploymentError(
            'n8n did not accept the administrator account: Instance owner already setup'))
        self.assertIs(False, run.result)
        self.assertFalse([event for event in run.events
                          if 'SetupProxy' in event or 'SetupAppVhost' in event or event == 'RESTART'])
        run.cleanup.assert_called_once_with()
        self.assertTrue(any('[404]' in message and 'Instance owner already setup' in message
                            for message in run.messages))
        self.assertFalse(any('[200]' in message for message in run.messages))

    def test_an_application_without_a_first_run_step_is_deployed_as_before(self):
        run = deploy('Hermes')
        self.assertIs(True, run.result)
        self.assertNotIn('OWNER', run.events)
        self.assertLess(position(run.events, ' up -d'), position(run.events, 'SetupProxy'))


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class ComposeTests(unittest.TestCase):
    def test_the_editor_is_published_on_loopback_only(self):
        compose = yaml.safe_load(make_site('n8n').generate_compose_config())
        self.assertEqual(['127.0.0.1:11007:5678'], compose['services']['testapp']['ports'])
        self.assertNotIn('ports', compose['services']['testapp-db'])


REQUEST = {
    'sitename': 'flows', 'Owner': 'reseller', 'Domain': 'flows.example',
    'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 512, 'App': 'n8n',
    'WPusername': 'admin', 'WPemal': 'admin@example.test', 'WPpasswd': 'AdminPass123',
}


def submit(email_is_valid=True, **changes):
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': 0}
    acl.currentContextPermission.return_value = 1
    acl.checkOwnerProtection.return_value = 1
    acl.CheckDomainBlackList.return_value = 1
    services['Websites'].objects.filter.return_value.count.return_value = 0
    services['validators'].email.return_value = email_is_valid
    env['ChildDomains'] = mock.Mock()
    env['ChildDomains'].objects.filter.return_value.count.return_value = 0
    env['PackageAssignment'] = mock.Mock()
    env['DockerPackages'] = mock.Mock()
    env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=4, Ram=4096)
    env['DOCKER_APPS'] = DOCKER_APPS
    env['n8n_password_problem'] = n8n_password_problem
    env['Docker_Sites'] = mock.Mock()
    reply = json.loads(cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST, **changes)).content)
    return reply, env


class CreationPageTests(unittest.TestCase):
    def test_a_password_n8n_would_refuse_is_refused_before_anything_is_deployed(self):
        for password in ('weak', 'NoDigitsHere', 'alllowercase1', 'A1' + 'a' * 63, None, 7):
            with self.subTest(password=password):
                reply, env = submit(WPpasswd=password)
                self.assertEqual(0, reply['status'])
                self.assertIn('8 to 64 characters', reply['error_message'])
                env['Docker_Sites'].assert_not_called()

    def test_an_email_n8n_would_refuse_is_refused_before_anything_is_deployed(self):
        for email, valid in (('not-an-email', False), (['a@example.test'], True), (None, True)):
            with self.subTest(email=email):
                reply, env = submit(email_is_valid=valid, WPemal=email)
                self.assertEqual(0, reply['status'])
                self.assertIn('valid administrator email', reply['error_message'])
                env['Docker_Sites'].assert_not_called()

    def test_acceptable_values_start_the_deployment(self):
        reply, env = submit()
        self.assertEqual(1, reply['status'])
        data = env['Docker_Sites'].call_args[0][1]
        self.assertEqual(('admin@example.test', 'AdminPass123'), (data['WPemal'], data['WPpasswd']))

    def test_the_rule_is_for_n8n_only(self):
        for app, ram in (('WordPress', 512), ('Hermes', 2048)):
            with self.subTest(app=app):
                reply, env = submit(email_is_valid=False, App=app, SiteRam=ram, WPpasswd='weak')
                self.assertEqual(1, reply['status'])
                self.assertEqual(1, env['Docker_Sites'].call_count)


if __name__ == '__main__':
    unittest.main(verbosity=2)
