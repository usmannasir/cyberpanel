"""What a Docker site's containers write on the server stays out of reach of the server's other accounts."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import DOCKER_APPS
from websiteFunctions.test_docker_apps import make_site
from websiteFunctions.test_docker_n8n_owner import deploy, position

try:
    import yaml
except ImportError:
    yaml = None

ENTRYPOINT = Path(__file__).resolve().parents[1] / 'dockerManager/entrypoint.sh'
ROOT_DIRECTORY = 'install -d -m 700 -o root -g root /home/docker/example.com'
N8N_DATA = 'install -d -m 700 -o 1000 -g 1000 /home/docker/example.com/data'


def create_directory(owner=None, failing=None):
    site = make_site('n8n')
    commands = []

    def output(command, *args):
        commands.append(command)
        return (0, 'no space left') if failing and failing in command else (1, '')

    with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output):
        return site.create_site_directory(owner), commands


class DirectoryTests(unittest.TestCase):
    def test_the_site_directory_is_made_for_root_alone(self):
        result, commands = create_directory()
        self.assertEqual((1, None), result)
        self.assertEqual([ROOT_DIRECTORY], commands)

    def test_an_image_with_its_own_user_gets_its_data_directory(self):
        result, commands = create_directory('1000:1000')
        self.assertEqual((1, None), result)
        self.assertEqual([ROOT_DIRECTORY, N8N_DATA], commands)

    def test_a_failure_is_reported_and_nothing_more_is_run(self):
        result, commands = create_directory('1000:1000', failing='-o root')
        self.assertEqual((0, 'no space left'), result)
        self.assertEqual([ROOT_DIRECTORY], commands)
        result, commands = create_directory('1000:1000', failing='-o 1000')
        self.assertEqual((0, 'no space left'), result)

    def test_an_owner_that_is_not_two_numbers_is_refused(self):
        for owner in ('node:node', '1000', '1000:1000; id', '$(id):0'):
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                create_directory(owner)


class ComposeAppTests(unittest.TestCase):
    def test_n8n_gets_both_directories_before_its_containers_start(self):
        run = deploy('n8n')
        self.assertIs(True, run.result)
        self.assertLess(position(run.events, ROOT_DIRECTORY), position(run.events, N8N_DATA))
        self.assertLess(position(run.events, N8N_DATA), position(run.events, ' up -d'))
        self.assertLess(position(run.events, ROOT_DIRECTORY), position(run.events, 'COMPOSE FILE'))
        self.assertEqual([], [event for event in run.events if event.startswith('mkdir')])

    def test_an_application_that_runs_as_root_gets_the_private_directory_only(self):
        run = deploy('Hermes')
        self.assertIs(True, run.result)
        self.assertLess(position(run.events, ROOT_DIRECTORY), position(run.events, ' up -d'))
        self.assertEqual([], [event for event in run.events if '/data' in event and event.startswith('install')])

    def test_a_directory_that_cannot_be_made_fails_the_deployment(self):
        site = make_site('n8n')
        site.JobID = site.data['JobID']
        with mock.patch.object(site, 'create_site_directory', return_value=(0, 'no space left')), \
                mock.patch.object(site, 'verify_system_resources'), \
                mock.patch.object(site, 'cleanup_failed_deployment'), \
                mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner',
                                  return_value='Usage: docker') as output, \
                mock.patch.object(docker_sites.ProcessUtilities, 'executioner') as execute, \
                mock.patch.object(docker_sites.logging, 'statusWriter') as status, \
                mock.patch.object(docker_sites.logging, 'writeToFile'):
            self.assertIs(False, site.DeployComposeApp('n8n'))
        execute.assert_not_called()
        self.assertTrue(any('no space left' in call[0][1] and '[404]' in call[0][1]
                            for call in status.call_args_list))

    def test_only_n8n_declares_an_image_user(self):
        self.assertEqual('1000:1000', DOCKER_APPS['n8n']['dataOwner'])
        for app in ('WordPress', 'Hermes'):
            self.assertNotIn('dataOwner', DOCKER_APPS[app])


class WordPressTests(unittest.TestCase):
    def test_the_site_directory_is_made_for_root_alone_before_anything_is_put_in_it(self):
        site = make_site('WordPress')
        site.JobID = site.data['JobID']
        site.data['htaccessPath'] = '/home/example.com/public_html/.htaccess'
        events = []

        def output(command, *args):
            events.append(command)
            return 'Usage: docker' if command == 'docker --help' else (1, '')

        def execute(command, *args):
            events.append(command)
            return 1

        utilities = SimpleNamespace(installUtilities=mock.Mock())
        with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
                mock.patch.object(docker_sites.ProcessUtilities, 'executioner', side_effect=execute), \
                mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value=0), \
                mock.patch('plogical.DockerSites.os.path.exists', return_value=False), \
                mock.patch.object(site, 'install_compose_file',
                                  side_effect=lambda content: events.append('COMPOSE FILE') or (1, None)), \
                mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities}), \
                mock.patch.object(site, 'wait_for_wordpress'), \
                mock.patch.object(docker_sites.logging, 'statusWriter') as status, \
                mock.patch.object(docker_sites.logging, 'writeToFile'):
            site.DeployWPContainer()
        self.assertTrue(any('[200]' in call[0][1] for call in status.call_args_list))
        self.assertLess(position(events, ROOT_DIRECTORY), position(events, 'COMPOSE FILE'))
        self.assertLess(position(events, ROOT_DIRECTORY), position(events, ' up -d'))
        self.assertEqual([], [event for event in events if event.startswith('mkdir')])


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class ComposeTests(unittest.TestCase):
    def test_n8n_runs_as_the_user_of_its_image(self):
        compose = yaml.safe_load(make_site('n8n').generate_compose_config())
        self.assertNotIn('user', compose['services']['testapp'])
        self.assertIn('/home/docker/example.com/data:/home/node/.n8n', compose['services']['testapp']['volumes'])


@unittest.skipIf(shutil.which('bash') is None, 'bash not installed')
class EntrypointTests(unittest.TestCase):
    """Runs the definitions of the real entrypoint with stand-ins for the commands they call."""

    ENVIRONMENT = {'DB_NAME': 'd', 'DB_USER': 'u', 'DB_PASSWORD': 'p', 'WP_ADMIN_EMAIL': 'a@example.test',
                   'WP_ADMIN_USER': 'a', 'WP_ADMIN_PASSWORD': 'p', 'WP_URL': 'https://example.test',
                   'DB_Host': 'db:3306'}

    def run_wp(self, tools):
        script = ENTRYPOINT.read_text()
        definitions = script[:script.index('rm -f "$READY"')]
        directory = tempfile.mkdtemp(prefix='docker-entrypoint-')
        self.addCleanup(shutil.rmtree, directory)
        for tool in tools:
            path = os.path.join(directory, tool)
            with open(path, 'w') as handle:
                handle.write('#!/bin/sh\necho "%s HOME=$HOME CACHE=$WP_CLI_CACHE_DIR $*"\n' % tool)
            os.chmod(path, 0o755)
        # The stand-in for PHP shows what would have run without a change of user.
        harness = definitions + '\nPHP=/bin/echo\nwp core is-installed\n'
        environment = dict(self.ENVIRONMENT, PATH=directory + ':/nonexistent')
        done = subprocess.run([shutil.which('bash'), '-c', harness], env=environment, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)
        return done.returncode, done.stdout.strip()

    def test_wp_cli_runs_as_the_web_servers_user(self):
        code, output = self.run_wp(['setpriv', 'runuser'])
        self.assertEqual(0, code, output)
        self.assertEqual('setpriv HOME=/tmp CACHE=/tmp/.wp-cli-cache --reuid=nobody --regid=nogroup '
                         '--clear-groups /bin/echo -d memory_limit=512M /usr/bin/wp '
                         '--path=/usr/local/lsws/Example/html core is-installed', output)

    def test_an_image_with_runuser_only(self):
        code, output = self.run_wp(['runuser'])
        self.assertEqual(0, code, output)
        self.assertEqual('runuser HOME=/tmp CACHE=/tmp/.wp-cli-cache -u nobody -g nogroup -- /bin/echo '
                         '-d memory_limit=512M /usr/bin/wp --path=/usr/local/lsws/Example/html '
                         'core is-installed', output)

    def test_an_image_without_either_tool_keeps_working_as_before(self):
        code, output = self.run_wp([])
        self.assertEqual(0, code, output)
        self.assertEqual('-d memory_limit=512M /usr/bin/wp --path=/usr/local/lsws/Example/html '
                         'core is-installed --allow-root', output)

    def test_the_files_belong_to_the_web_servers_user_before_wp_cli_first_runs(self):
        script = ENTRYPOINT.read_text()
        body = script[script.index('rm -f "$READY"'):]
        self.assertLess(body.index('chown -R nobody:nogroup "$ROOT"'), body.index('wp '))
        self.assertEqual(0, subprocess.call(['bash', '-n', str(ENTRYPOINT)]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
