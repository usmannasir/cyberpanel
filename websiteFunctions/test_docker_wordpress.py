import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock

from plogical.DockerSites import DockerDeploymentError
from websiteFunctions.test_docker_apps import make_site


class WordPressComposeTests(TestCase):
    def test_https_loopback_bootstrap_health_and_literal_credentials(self):
        site = make_site('WordPress')
        site.data['adminPassword'] = 'quote"and$VARIABLE\nline'
        config = json.loads(site.generate_wordpress_compose_config())
        app = config['services']['testapp']
        self.assertEqual(app['ports'], ['127.0.0.1:11007:8088'])
        self.assertEqual(app['environment']['WP_URL'], 'https://example.com')
        self.assertEqual(app['environment']['WP_ADMIN_PASSWORD'], 'quote"and$$VARIABLE\nline')
        self.assertIn('/usr/local/CyberCP/dockerManager/entrypoint.sh:/usr/local/bin/entrypoint.sh:ro', app['volumes'])
        self.assertIn('cyberpanel-wordpress-ready', app['healthcheck']['test'][1])
        self.assertIn('wp-login.php', app['healthcheck']['test'][1])
        self.assertIn('"follow_location"=>0', app['healthcheck']['test'][1])
        self.assertIn('loginform', app['healthcheck']['test'][1])
        self.assertEqual(config['services']['testapp-db']['environment']['MYSQL_ROOT_PASSWORD'], 'rootpass')

    def test_running_empty_or_unhealthy_wordpress_never_reports_ready(self):
        site = make_site('WordPress')
        for health in (None, 'starting', 'unhealthy'):
            container = SimpleNamespace(status='running', attrs={'State': {'Health': {'Status': health}}})
            with mock.patch('plogical.DockerSites.docker.from_env') as engine, \
                    mock.patch('plogical.DockerSites.time.sleep'):
                engine.return_value.containers.list.return_value = [container]
                with self.assertRaises(DockerDeploymentError):
                    site.wait_for_wordpress(attempts=1, delay=0)

    def test_readiness_uses_exact_project_and_service_and_rejects_exited_bootstrap(self):
        site = make_site('WordPress')
        container = SimpleNamespace(status='exited', attrs={})
        with mock.patch('plogical.DockerSites.docker.from_env') as engine:
            engine.return_value.containers.list.return_value = [container]
            with self.assertRaisesRegex(DockerDeploymentError, 'initialization failed'):
                site.wait_for_wordpress(attempts=1)
            engine.return_value.containers.list.assert_called_once_with(all=True, filters={'label': [
                'com.docker.compose.project=testapp', 'com.docker.compose.service=testapp']})
            container.status = 'running'
            container.attrs = {'State': {'Health': {'Status': 'healthy'}}}
            self.assertTrue(site.wait_for_wordpress(attempts=1))

    def test_failed_readiness_writes_failure_and_never_completion(self):
        site = make_site('WordPress')
        site.JobID = site.data['JobID']
        output = lambda command, *args: 'Docker installed' if command == 'docker --help' else (1, '')
        with mock.patch('plogical.DockerSites.ProcessUtilities.outputExecutioner', side_effect=output), \
                mock.patch('plogical.DockerSites.ProcessUtilities.executioner', return_value=1), \
                mock.patch('plogical.DockerSites.os.path.exists', return_value=False), \
                mock.patch('builtins.open', mock.mock_open()), \
                mock.patch.object(site, 'wait_for_wordpress', side_effect=DockerDeploymentError('WordPress files missing')), \
                mock.patch('plogical.DockerSites.logging.statusWriter') as status, \
                mock.patch('plogical.DockerSites.logging.writeToFile'):
            site.DeployWPContainer()
        messages = [call.args[1] for call in status.call_args_list]
        self.assertTrue(any('[404]' in message for message in messages))
        self.assertFalse(any('[200]' in message for message in messages))


class WordPressBootstrapTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = self.root / 'data'
        self.content.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        FIXTURE_ROOT=str(self.root), DB_NAME='db', DB_USER='user', DB_PASSWORD='secret',
                        WP_ADMIN_EMAIL='admin@example.test', WP_ADMIN_USER='admin', WP_ADMIN_PASSWORD='private',
                        WP_URL='https://example.test', DB_Host='database:3306')
        php = self.bin / 'php'
        php.write_text('#!' + sys.executable + '\n' + '''
import json, os, sys
from pathlib import Path
root = Path(os.environ['FIXTURE_ROOT'])
args = sys.argv[1:]
if args[0] == '-r':
    sys.exit(0)
assert args[:2] == ['-d', 'memory_limit=512M']
args = [arg for arg in args[3:] if not arg.startswith('--')]
command = ' '.join(args)
with (root / 'commands').open('a') as log:
    log.write(command + '\\n')
if command == 'core download':
    if os.environ.get('FAIL_DOWNLOAD'):
        sys.exit(1)
    (root / 'data/wp-includes').mkdir()
    (root / 'data/wp-includes/version.php').write_text('core')
elif command == 'config create':
    (root / 'data/wp-config.php').write_text(sys.stdin.read())
elif command == 'core is-installed':
    sys.exit(0 if (root / 'installed').exists() else 1)
elif command == 'core install':
    (root / 'installed').write_text('existing database')
''')
        php.chmod(0o755)
        for name in ('chown', 'tail'):
            tool = self.bin / name
            tool.write_text('#!/bin/sh\nexit 0\n')
            tool.chmod(0o755)
        server = self.bin / 'lswsctrl'
        server.write_text('#!/bin/sh\necho "$1" >> "$FIXTURE_ROOT/server"\n')
        server.chmod(0o755)
        source = (Path(__file__).parents[1] / 'dockerManager/entrypoint.sh').read_text()
        source = source.replace('PHP=/usr/local/lsws/lsphp82/bin/php', 'PHP=' + str(php))
        source = source.replace('ROOT=/usr/local/lsws/Example/html', 'ROOT=' + str(self.content))
        source = source.replace('READY=/tmp/cyberpanel-wordpress-ready', 'READY=' + str(self.root / 'ready'))
        source = source.replace('/usr/local/lsws/bin/lswsctrl', str(server))
        self.script = self.root / 'entrypoint.sh'
        self.script.write_text(source)

    def test_restart_preserves_installation_configuration_and_content(self):
        for _ in range(2):
            result = subprocess.run(['bash', str(self.script)], env=self.env, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        commands = (self.root / 'commands').read_text().splitlines()
        self.assertEqual(commands.count('core download'), 1)
        self.assertEqual(commands.count('config create'), 1)
        self.assertEqual(commands.count('core install'), 1)
        config = (self.content / 'wp-config.php').read_text()
        self.assertIn("$_SERVER['HTTPS'] = 'on';", config)
        self.assertNotIn('getenv', config)
        self.assertTrue((self.root / 'ready').exists())

    def test_failed_download_never_publishes_readiness_or_starts_web_server(self):
        self.env['FAIL_DOWNLOAD'] = '1'
        result = subprocess.run(['bash', str(self.script)], env=self.env, capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'ready').exists())
        self.assertFalse((self.root / 'server').exists())
        self.assertFalse((self.root / 'installed').exists())
