"""Tests for the one-click Docker application registry and the compose files it renders.

Run standalone (no database needed):
    /usr/local/CyberCP/bin/python -m unittest websiteFunctions.test_docker_apps -v
"""

import os
import sys
import unittest
from unittest import mock

sys.path.append('/usr/local/CyberCP')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.DockerSites import DOCKER_APPS, Docker_Sites

try:
    import yaml
except ImportError:
    yaml = None


def make_site(app='Hermes'):
    """Build a Docker_Sites instance without running __init__ (it touches csf and docker)."""
    site = Docker_Sites.__new__(Docker_Sites)
    site.data = {
        'JobID': '/home/cyberpanel/test-job',
        'ComposePath': '/home/docker/example.com/docker-compose.yml',
        'MySQLPath': '/home/example.com/public_html/sqldocker',
        'MySQLRootPass': 'rootpass',
        'MySQLDBName': 'dbname',
        'MySQLDBNUser': 'dbuser',
        'MySQLPassword': 'dbpass',
        'CPUsMySQL': '1',
        'MemoryMySQL': '512',
        'port': '11007',
        'SitePath': '/home/example.com/public_html/wpdocker',
        'CPUsSite': '2',
        'MemorySite': '2048',
        'SiteName': 'testapp',
        'ServiceName': 'testapp',
        'finalURL': 'example.com',
        'blogTitle': 'testapp',
        'adminUser': 'cyberpanel',
        'adminPassword': 'AdminPass123',
        'adminEmail': 'admin@example.com',
        'dashboardSecret': 'a' * 32,
        'externalApp': 'examp1234',
        'docRoot': '/home/example.com',
        'App': app,
    }
    return site


class TestDockerAppRegistry(unittest.TestCase):

    def test_every_app_declares_the_full_contract(self):
        for app, meta in DOCKER_APPS.items():
            for key in ('siteType', 'requiresDB', 'deploy', 'compose', 'minSiteRam'):
                self.assertIn(key, meta, f'{app} is missing "{key}"')

    def test_site_types_are_unique(self):
        siteTypes = [meta['siteType'] for meta in DOCKER_APPS.values()]
        self.assertEqual(len(siteTypes), len(set(siteTypes)))

    def test_site_types_do_not_collide_with_reserved_values(self):
        ## Joomla is reserved on the class but is not deployable as a Docker app yet.
        self.assertNotIn(Docker_Sites.Joomla, [meta['siteType'] for meta in DOCKER_APPS.values()])
        self.assertEqual(DOCKER_APPS['WordPress']['siteType'], Docker_Sites.Wordpress)
        self.assertEqual(DOCKER_APPS['n8n']['siteType'], Docker_Sites.N8N)
        self.assertEqual(DOCKER_APPS['Hermes']['siteType'], Docker_Sites.Hermes)

    def test_deploy_and_compose_functions_exist(self):
        for app, meta in DOCKER_APPS.items():
            self.assertTrue(hasattr(Docker_Sites, meta['deploy']),
                            f'{app} deploy function {meta["deploy"]} does not exist')
            if meta['compose'] is not None:
                self.assertTrue(hasattr(Docker_Sites, meta['compose']),
                                f'{app} compose function {meta["compose"]} does not exist')

    def test_deploy_functions_are_reachable_from_run(self):
        ## Docker_Sites.run() dispatches on the function name stored in the registry.
        import inspect
        source = inspect.getsource(Docker_Sites.run)
        for app, meta in DOCKER_APPS.items():
            self.assertIn(meta['deploy'], source, f'{app} deploy function is not dispatched in run()')

    def test_hermes_needs_more_ram_than_the_others(self):
        self.assertGreaterEqual(DOCKER_APPS['Hermes']['minSiteRam'], 2048)

    def test_hermes_ships_no_database(self):
        self.assertFalse(DOCKER_APPS['Hermes']['requiresDB'])
        self.assertTrue(DOCKER_APPS['n8n']['requiresDB'])


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class TestHermesCompose(unittest.TestCase):

    def setUp(self):
        self.compose = yaml.safe_load(make_site('Hermes').generate_hermes_compose_config())
        self.service = self.compose['services']['testapp']
        self.environment = dict(item.split('=', 1) for item in self.service['environment'])

    def test_uses_the_official_image_and_default_command(self):
        self.assertEqual(self.service['image'], 'nousresearch/hermes-agent:latest')
        self.assertEqual(self.service['command'], 'gateway run')

    def test_no_database_container(self):
        self.assertEqual(list(self.compose['services'].keys()), ['testapp'])
        self.assertNotIn('postgres', str(self.compose))

    def test_dashboard_is_published_on_loopback_only(self):
        ## OpenLiteSpeed proxies to 127.0.0.1:port, so the container must not be
        ## reachable from the internet directly.
        self.assertEqual(self.service['ports'], ['127.0.0.1:11007:9119'])

    def test_state_is_persisted_outside_the_container(self):
        self.assertIn('/home/docker/example.com/data:/opt/data', self.service['volumes'])

    def test_auth_gate_is_satisfied(self):
        ## Hermes refuses to start on a non loopback bind without an auth provider,
        ## so a missing credential here is a failed deployment, not a weak password.
        self.assertEqual(self.environment['HERMES_DASHBOARD'], '1')
        self.assertEqual(self.environment['HERMES_DASHBOARD_HOST'], '0.0.0.0')
        self.assertEqual(self.environment['HERMES_DASHBOARD_BASIC_AUTH_USERNAME'], 'cyberpanel')
        self.assertEqual(self.environment['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'], 'AdminPass123')
        self.assertTrue(len(self.environment['HERMES_DASHBOARD_BASIC_AUTH_SECRET']) >= 32)

    def test_public_url_matches_the_domain(self):
        self.assertEqual(self.environment['HERMES_DASHBOARD_PUBLIC_URL'], 'https://example.com')

    def test_resource_limits_come_from_the_site_fields(self):
        limits = self.service['deploy']['resources']['limits']
        self.assertEqual(str(limits['cpus']), '2')
        self.assertEqual(limits['memory'], '2048M')

    def test_healthcheck_probes_the_dashboard_port(self):
        self.assertIn('9119', ' '.join(self.service['healthcheck']['test']))


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class TestN8NComposeUnchanged(unittest.TestCase):
    """The Hermes work refactored the shared deployment path, n8n must be untouched."""

    def setUp(self):
        self.compose = yaml.safe_load(make_site('n8n').generate_compose_config())

    def test_still_ships_its_database(self):
        self.assertIn('testapp-db', self.compose['services'])
        self.assertEqual(self.compose['services']['testapp-db']['image'], 'postgres:16-alpine')

    def test_still_publishes_the_editor_port(self):
        self.assertEqual(self.compose['services']['testapp']['ports'], ['11007:5678'])


class TestAppVhost(unittest.TestCase):

    def test_n8n_helper_delegates_to_the_shared_one(self):
        with mock.patch.object(Docker_Sites, 'SetupAppVhost', return_value=True) as shared:
            Docker_Sites.SetupN8NVhost('example.com', '11007')
        shared.assert_called_once_with('example.com', '11007')

    def test_writes_a_websocket_proxy_context(self):
        written = []
        handle = mock.mock_open(read_data='docRoot /home/example.com/public_html\n')
        handle.return_value.write = written.append

        with mock.patch('os.path.exists', return_value=True), mock.patch('builtins.open', handle):
            self.assertTrue(Docker_Sites.SetupAppVhost('example.com', '11007'))

        context = ''.join(written)
        self.assertIn('handler                 docker11007', context)
        self.assertIn('websocket               1', context)
        self.assertIn('RequestHeader set X-Forwarded-Proto https', context)
        self.assertIn('RequestHeader set X-Forwarded-Host "example.com"', context)

    def test_is_idempotent(self):
        handle = mock.mock_open(read_data='context / {\n  type proxy\n}\n')
        with mock.patch('os.path.exists', return_value=True), mock.patch('builtins.open', handle):
            self.assertTrue(Docker_Sites.SetupAppVhost('example.com', '11007'))
        handle.return_value.write.assert_not_called()

    def test_missing_vhost_file_is_reported(self):
        with mock.patch('os.path.exists', return_value=False):
            self.assertFalse(Docker_Sites.SetupAppVhost('example.com', '11007'))


if __name__ == '__main__':
    unittest.main()
