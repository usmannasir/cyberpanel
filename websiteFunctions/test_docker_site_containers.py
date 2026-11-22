"""A Docker site's containers are the ones of its Docker Compose project, whatever other containers are called."""
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import compose_project_names, site_containers, site_directory_name


class Container:
    def __init__(self, name, project=None, service=None, status='running'):
        self.name = name
        self.id = 'full-id-of-' + name
        self.short_id = 'short-' + name
        self.status = status
        self.labels = {}
        if project is not None:
            self.labels = {'com.docker.compose.project': project, 'com.docker.compose.service': service}
        self.attrs = {'State': {}}

    def __repr__(self):
        return self.name


class Client:
    """Answers container listings the way the Docker daemon does."""

    def __init__(self, containers):
        self.containers = self
        self.known = containers
        self.filters = []

    def list(self, all=False, filters=None):
        self.filters.append(filters)
        selected = []
        for container in self.known:
            if not all and container.status != 'running':
                continue
            matches = True
            for key, wanted in (filters or {}).items():
                if key == 'name':
                    # The daemon selects every container whose name contains the text.
                    matches = matches and wanted in container.name
                elif key == 'label':
                    for label in ([wanted] if isinstance(wanted, str) else wanted):
                        name, value = label.split('=', 1)
                        matches = matches and container.labels.get(name) == value
                else:
                    raise AssertionError('unexpected filter %s' % key)
            if matches:
                selected.append(container)
        return selected


def server():
    """Three customers' sites and a container the administrator started by hand."""
    return [
        Container('n8n_n8n_1', 'n8n', 'n8n'),
        Container('n8n_n8n-db_1', 'n8n', 'n8n-db'),
        Container('n_n_1', 'n', 'n'),
        Container('n_n-db_1', 'n', 'n-db', status='exited'),
        Container('shop_shop_1', 'shop', 'shop'),
        Container('shop_shop-db_1', 'shop', 'shop-db'),
        Container('myshop_myshop_1', 'myshop', 'myshop'),
        Container('myshop_myshop-db_1', 'myshop', 'myshop-db'),
        Container('n_n_copy'),
    ]


def names(containers):
    return sorted(container.name for container in containers)


def make_site(data, containers):
    site = docker_sites.Docker_Sites.__new__(docker_sites.Docker_Sites)
    site.data = data
    site.JobID = data.get('JobID')
    client = Client(containers)
    return site, client


def run(site, client, method, *args, **kwargs):
    commands = []

    def execute(command, *more):
        commands.append(command)
        return 1

    def output(command, *more):
        commands.append(command)
        return 1, 'accepting connections'

    utilities = SimpleNamespace(installUtilities=mock.Mock())
    with mock.patch.object(docker_sites.docker, 'from_env', return_value=client), \
            mock.patch.object(docker_sites.ProcessUtilities, 'executioner', side_effect=execute), \
            mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value='ubuntu'), \
            mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities}), \
            mock.patch.object(docker_sites.time, 'sleep'), \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        result = getattr(site, method)(*args, **kwargs)
    return result, commands


class ProjectNameTests(unittest.TestCase):
    def test_a_site_name_is_its_project_name(self):
        self.assertEqual(['shop'], compose_project_names('shop'))
        self.assertEqual(['n8n'], compose_project_names('n8n'))

    def test_names_from_before_the_lower_case_rule_are_found_as_compose_stored_them(self):
        self.assertEqual(['My Shop', 'my shop', 'myshop'], compose_project_names('My Shop'))
        self.assertEqual(['my-shop', 'myshop'], compose_project_names('my-shop'))

    def test_nothing_usable_names_no_project(self):
        for name in (None, '', 7, ['shop'], {'a': 1}):
            self.assertEqual([], compose_project_names(name))


class SelectionTests(unittest.TestCase):
    def test_only_the_containers_of_the_sites_project_are_selected(self):
        client = Client(server())
        self.assertEqual(['n_n-db_1', 'n_n_1'], names(site_containers(client, 'n')))
        self.assertEqual(['shop_shop-db_1', 'shop_shop_1'], names(site_containers(client, 'shop')))
        self.assertEqual(['n8n_n8n-db_1', 'n8n_n8n_1'], names(site_containers(client, 'n8n')))

    def test_one_service_of_the_project(self):
        client = Client(server())
        self.assertEqual(['shop_shop-db_1'], names(site_containers(client, 'shop', 'shop-db')))
        self.assertEqual(['shop_shop_1'], names(site_containers(client, 'shop', 'shop')))
        self.assertEqual([], names(site_containers(client, 'shop', 'myshop')))

    def test_the_daemon_is_asked_by_label_and_for_stopped_containers_too(self):
        client = Client(server())
        site_containers(client, 'shop', 'shop')
        self.assertEqual([{'label': ['com.docker.compose.project=shop', 'com.docker.compose.service=shop']}],
                         client.filters)

    def test_a_site_without_a_name_selects_nothing(self):
        client = Client(server())
        for name in (None, '', 7):
            self.assertEqual([], site_containers(client, name))
        self.assertEqual([], client.filters)


class DeleteTests(unittest.TestCase):
    def delete(self, name, domain='n.example'):
        site, client = make_site({'domain': domain, 'name': name, 'JobID': None}, server())
        # What the constructor derives from the name on Ubuntu and on AlmaLinux.
        site.DockerAppName = '%s_%s' % (name, name)
        return run(site, client, 'DeleteDockerApp')

    def test_deleting_a_site_leaves_every_other_sites_containers_alone(self):
        for name, own in (('n', ['n_n_1', 'n_n-db_1']), ('shop', ['shop_shop_1', 'shop_shop-db_1'])):
            with self.subTest(site=name):
                result, commands = self.delete(name)
                touched = [command for command in commands if command.startswith('docker ')]
                for container in server():
                    mentioned = [command for command in touched
                                 if container.id in command or container.short_id in command]
                    if container.name in own:
                        self.assertTrue(mentioned, container.name)
                    else:
                        self.assertEqual([], mentioned, container.name)

    def test_the_project_that_was_started_is_the_one_taken_down(self):
        result, commands = self.delete('shop', 'shop.example')
        self.assertEqual('docker-compose -f /home/docker/shop.example/docker-compose.yml -p shop down -v',
                         commands[0])

    def test_the_directory_goes_after_the_containers(self):
        result, commands = self.delete('shop', 'shop.example')
        removal = commands.index('rm -rf /home/docker/shop.example')
        self.assertTrue(all(commands.index(command) < removal
                            for command in commands if command.startswith('docker')))

    def test_a_domain_that_cannot_name_one_directory_removes_nothing(self):
        for domain in (None, '', '.', '..', '../etc', 'a/b', 'a b', '-rf', 'shop.example/..', ['shop.example']):
            with self.subTest(domain=domain):
                result, commands = self.delete('shop', domain)
                self.assertEqual(0, result)
                self.assertEqual([], commands)

    def test_directory_names(self):
        for domain in ('shop.example', 'xn--80ak6aa92e.example', 'a-b.example.co.uk', 'sub_1.example'):
            self.assertEqual(domain, site_directory_name(domain))


class DeploymentLookupTests(unittest.TestCase):
    DATA = {'SiteName': 'shop', 'ServiceName': 'shop', 'finalURL': 'shop.example',
            'ComposePath': '/home/docker/shop.example/docker-compose.yml', 'JobID': None}

    def containers(self):
        # The other customer's containers come first in the daemon's answer.
        ordered = server()
        ordered.sort(key=lambda container: not container.name.startswith('myshop'))
        return ordered

    def test_a_service_is_found_in_the_sites_own_project(self):
        site, client = make_site(dict(self.DATA), self.containers())
        found, commands = run(site, client, 'find_container_by_service', 'shop')
        self.assertEqual('shop_shop_1', found.name)
        found, commands = run(site, client, 'find_container_by_service', 'shop-db')
        self.assertEqual('shop_shop-db_1', found.name)

    def test_a_service_the_project_does_not_have_is_not_found_elsewhere(self):
        site, client = make_site(dict(self.DATA, SiteName='hop', ServiceName='hop'), self.containers())
        found, commands = run(site, client, 'find_container_by_service', 'hop')
        self.assertIsNone(found)

    def test_health_is_read_from_the_sites_own_container(self):
        containers = self.containers()
        for container in containers:
            if container.name.startswith('myshop'):
                container.status = 'running'
            if container.name.startswith('shop_'):
                container.status = 'exited'
        site, client = make_site(dict(self.DATA), containers)
        healthy, commands = run(site, client, 'check_container_health', 'shop', 2, 0)
        self.assertIs(False, healthy)

    def test_monitoring_reads_logs_and_database_state_of_the_sites_own_containers(self):
        site, client = make_site(dict(self.DATA), self.containers())
        result, commands = run(site, client, 'monitor_deployment', True)
        self.assertIs(True, result)
        self.assertEqual(['docker exec shop_shop-db_1 pg_isready -U postgres'], commands)

    def test_a_failed_deployment_removes_its_own_project_and_nothing_else(self):
        site, client = make_site(dict(self.DATA), self.containers())
        result, commands = run(site, client, 'cleanup_failed_deployment')
        self.assertIs(True, result)
        self.assertEqual('docker-compose -f /home/docker/shop.example/docker-compose.yml -p shop down -v',
                         commands[0])
        removed = [command for command in commands if command.startswith('docker rm')]
        self.assertEqual(['docker rm -f full-id-of-shop_shop_1', 'docker rm -f full-id-of-shop_shop-db_1'],
                         removed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
