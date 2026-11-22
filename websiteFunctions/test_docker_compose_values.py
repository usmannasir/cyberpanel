"""Whatever a customer types on the creation page stays one value in the compose file of the site."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import compose_file
from websiteFunctions.test_docker_apps import make_site

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager

try:
    import yaml
except ImportError:
    yaml = None

## Line breaks in every form YAML knows, and the characters that open YAML structure.
AWKWARD = ('pass\rprivileged: true', 'pass\x85- EXTRA=1', 'pass\u2028EXTRA=1', 'pass\u2029EXTRA=1',
           'pass\nEXTRA=1', "it's", 'say "hi"', 'a: b', 'a #b', '{x: y}', '[x]', '- x', '& *x', '%TAG', '| x',
           '> x', '!!python/object', ' padded ', 'tab\there', 'back\\slash', '`cmd`', 'x' * 300)


def environment(service):
    return dict(item.split('=', 1) for item in service['environment'])


class BuilderTests(unittest.TestCase):
    def test_the_file_is_json(self):
        for app, method in (('n8n', 'generate_compose_config'), ('Hermes', 'generate_hermes_compose_config'),
                            ('WordPress', 'generate_wordpress_compose_config')):
            with self.subTest(app=app):
                site = make_site(app)
                self.assertIsInstance(json.loads(getattr(site, method)()), dict)

    def test_a_dollar_sign_is_not_a_compose_variable(self):
        self.assertEqual({'a': ['x=$$HOME', {'b': 'c$$d'}], 'n': 5},
                         json.loads(compose_file({'a': ['x=$HOME', {'b': 'c$d'}], 'n': 5})))


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class ValueTests(unittest.TestCase):
    """Read the file back the way Docker Compose does, as YAML."""

    def test_a_hermes_user_name_and_password_stay_what_they_are(self):
        expected = set(environment(yaml.safe_load(make_site('Hermes').generate_hermes_compose_config())
                                   ['services']['testapp']))
        for value in AWKWARD:
            with self.subTest(value=value):
                site = make_site('Hermes')
                site.data['adminUser'] = value
                site.data['adminPassword'] = value
                compose = yaml.safe_load(site.generate_hermes_compose_config())
                self.assertEqual(['testapp'], list(compose['services']))
                self.assertEqual({'version', 'services', 'networks'}, set(compose))
                service = compose['services']['testapp']
                self.assertEqual({'image', 'restart', 'command', 'healthcheck', 'environment', 'ports', 'volumes',
                                  'networks', 'deploy'}, set(service))
                variables = environment(service)
                self.assertEqual(expected, set(variables))
                self.assertEqual(value, variables['HERMES_DASHBOARD_BASIC_AUTH_USERNAME'])
                self.assertEqual(value, variables['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'])

    def test_n8n_database_values_stay_what_they_are(self):
        expected = set(environment(yaml.safe_load(make_site('n8n').generate_compose_config())
                                   ['services']['testapp']))
        for value in AWKWARD:
            with self.subTest(value=value):
                site = make_site('n8n')
                site.data['MySQLPassword'] = value
                site.data['MySQLDBName'] = value
                compose = yaml.safe_load(site.generate_compose_config())
                self.assertEqual(['testapp-db', 'testapp'], list(compose['services']))
                variables = environment(compose['services']['testapp'])
                self.assertEqual(expected, set(variables))
                self.assertEqual(value, variables['DB_POSTGRESDB_PASSWORD'])
                self.assertEqual(value, variables['DB_POSTGRESDB_DATABASE'])
                database = environment(compose['services']['testapp-db'])
                self.assertEqual({'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'}, set(database))
                self.assertEqual(value, database['POSTGRES_PASSWORD'])

    def test_a_dollar_sign_in_a_password_reaches_the_application_unchanged(self):
        site = make_site('Hermes')
        site.data['adminPassword'] = 'pa$$word$HOME${X}'
        variables = environment(yaml.safe_load(site.generate_hermes_compose_config())['services']['testapp'])
        # Docker Compose turns $$ back into $ when it reads the file.
        self.assertEqual('pa$$$$word$$HOME$${X}', variables['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'])

    def test_the_compose_files_say_what_they_said_before(self):
        n8n = yaml.safe_load(make_site('n8n').generate_compose_config())
        self.assertEqual('3.8', n8n['version'])
        self.assertEqual({'db_storage': {'driver': 'local'}, 'n8n_storage': {'driver': 'local'}}, n8n['volumes'])
        self.assertEqual({'n8n-network': {'driver': 'bridge', 'name': 'testapp_network'}}, n8n['networks'])
        database = n8n['services']['testapp-db']
        self.assertEqual({'test': ['CMD-SHELL', 'pg_isready -U postgres'], 'interval': '10s', 'timeout': '5s',
                          'retries': 5, 'start_period': '30s'}, database['healthcheck'])
        self.assertEqual(['/home/docker/example.com/db:/var/lib/postgresql/data'], database['volumes'])
        self.assertEqual({'resources': {'limits': {'cpus': '1', 'memory': '512M'}}}, database['deploy'])
        self.assertEqual('always', database['restart'])
        application = n8n['services']['testapp']
        self.assertEqual({'test': ['CMD', 'wget', '--spider', 'http://localhost:5678'], 'interval': '20s',
                          'timeout': '10s', 'retries': 3}, application['healthcheck'])
        self.assertEqual(['testapp-db'], application['depends_on'])
        self.assertEqual(['n8n-network'], application['networks'])
        self.assertEqual({'resources': {'limits': {'cpus': '2', 'memory': '2048M'}}}, application['deploy'])
        variables = environment(application)
        self.assertEqual('testapp-db', variables['DB_POSTGRESDB_HOST'])
        self.assertEqual('https://example.com', variables['WEBHOOK_URL'])
        self.assertEqual(19, len(variables))

        hermes = yaml.safe_load(make_site('Hermes').generate_hermes_compose_config())
        self.assertEqual({'hermes-network': {'driver': 'bridge', 'name': 'testapp_network'}}, hermes['networks'])
        service = hermes['services']['testapp']
        self.assertEqual(['CMD-SHELL', "python3 -c \"import socket; socket.create_connection(('127.0.0.1', 9119), "
                                       "5).close()\""], service['healthcheck']['test'])
        self.assertEqual('60s', service['healthcheck']['start_period'])
        self.assertEqual(['hermes-network'], service['networks'])
        self.assertEqual('always', service['restart'])


REQUEST = {
    'sitename': 'agent', 'Owner': 'reseller', 'Domain': 'agent.example',
    'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 2048, 'App': 'Hermes',
    'WPusername': 'admin', 'WPemal': 'admin@example.test', 'WPpasswd': 'AdminPass123',
}


def submit(**changes):
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': 0}
    acl.currentContextPermission.return_value = 1
    acl.checkOwnerProtection.return_value = 1
    acl.CheckDomainBlackList.return_value = 1
    services['Websites'].objects.filter.return_value.count.return_value = 0
    env['ChildDomains'] = mock.Mock()
    env['ChildDomains'].objects.filter.return_value.count.return_value = 0
    env['PackageAssignment'] = mock.Mock()
    env['DockerPackages'] = mock.Mock()
    env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=4, Ram=4096)
    env['DockerSites'] = mock.Mock()
    env['DOCKER_APPS'] = docker_sites.DOCKER_APPS
    env['n8n_password_problem'] = docker_sites.n8n_password_problem
    env['Docker_Sites'] = mock.Mock()
    env['Docker_Sites'].site_name_problem.return_value = None
    reply = json.loads(cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST, **changes)).content)
    return reply, env


class UserNameTests(unittest.TestCase):
    def test_a_user_name_with_anything_but_plain_characters_is_refused_at_the_door(self):
        for name in ('admin\rprivileged: true', 'admin\x85x', 'admin\u2028x', 'admin\nx', 'ad min', "ad'min",
                     'ad"min', 'ad:min', '-admin', '.admin', '', 'a' * 61, None, 7, ['admin'], {'a': 1}):
            for app in ('Hermes', 'n8n', 'WordPress'):
                with self.subTest(name=name, app=app):
                    reply, env = submit(WPusername=name, App=app)
                    self.assertEqual(0, reply['status'])
                    self.assertIn('Invalid admin username', reply['error_message'])
                    env['Docker_Sites'].assert_not_called()

    def test_ordinary_user_names_are_accepted(self):
        for name in ('admin', 'cyberpanel', 'john.doe', 'j_doe-2', 'me@example.test', 'A', 'a' * 60):
            with self.subTest(name=name):
                reply, env = submit(WPusername=name)
                self.assertEqual(1, reply['status'], reply)
                self.assertEqual(name, env['Docker_Sites'].call_args[0][1]['WPusername'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
