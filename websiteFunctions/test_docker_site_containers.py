"""A Docker site's containers are the ones of its Docker Compose project, whatever other containers are called."""
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import (
    COMPOSE_DIRECTORY_LABEL, Docker_Sites, compose_project_names, container_of_site, site_containers,
    site_directory_name, site_name_in_use)


class Container:
    def __init__(self, name, project=None, service=None, status='running', directory=None):
        self.name = name
        self.id = 'full-id-of-' + name
        self.short_id = 'short-' + name
        self.status = status
        self.labels = {}
        if project is not None:
            self.labels = {'com.docker.compose.project': project, 'com.docker.compose.service': service}
        if directory is not None:
            self.labels[COMPOSE_DIRECTORY_LABEL] = directory
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
        Container('n8n_n8n_1', 'n8n', 'n8n', directory='/home/docker/n8n.example'),
        Container('n8n_n8n-db_1', 'n8n', 'n8n-db', directory='/home/docker/n8n.example'),
        Container('n_n_1', 'n', 'n', directory='/home/docker/n.example'),
        Container('n_n-db_1', 'n', 'n-db', status='exited', directory='/home/docker/n.example'),
        # Started by a Docker Compose that records no directory.
        Container('shop_shop_1', 'shop', 'shop'),
        Container('shop_shop-db_1', 'shop', 'shop-db'),
        Container('myshop_myshop_1', 'myshop', 'myshop', directory='/home/docker/myshop.example'),
        Container('myshop_myshop-db_1', 'myshop', 'myshop-db', directory='/home/docker/myshop.example'),
        Container('n_n_copy'),
    ]


def server_with_other_projects():
    """The same server, where somebody also runs Docker Compose projects named like two of the sites."""
    return server() + [
        Container('n8n_editor_1', 'n8n', 'editor', directory='/opt/n8n'),
        Container('n8n_n8n-db_2', 'n8n', 'n8n-db', status='exited', directory='/opt/n8n'),
        Container('shop_cache_1', 'shop', 'cache', directory='/root/shop'),
    ]


DOMAINS = {'n': 'n.example', 'n8n': 'n8n.example', 'shop': 'shop.example', 'myshop': 'myshop.example'}


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

    def test_hyphens_and_underscores_stay_as_compose_keeps_them(self):
        # The site "my-shop" has no claim on the project of the site "myshop".
        self.assertEqual(['my-shop'], compose_project_names('my-shop'))
        self.assertEqual(['my_shop'], compose_project_names('my_shop'))
        self.assertEqual(['My-Shop_1', 'my-shop_1'], compose_project_names('My-Shop_1'))
        client = Client(server())
        self.assertEqual([], site_containers(client, 'my-shop', 'myshop.example'))

    def test_nothing_usable_names_no_project(self):
        for name in (None, '', 7, ['shop'], {'a': 1}):
            self.assertEqual([], compose_project_names(name))


class SelectionTests(unittest.TestCase):
    def test_only_the_containers_of_the_sites_project_are_selected(self):
        client = Client(server())
        self.assertEqual(['n_n-db_1', 'n_n_1'], names(site_containers(client, 'n', 'n.example')))
        self.assertEqual(['shop_shop-db_1', 'shop_shop_1'], names(site_containers(client, 'shop', 'shop.example')))
        self.assertEqual(['n8n_n8n-db_1', 'n8n_n8n_1'], names(site_containers(client, 'n8n', 'n8n.example')))

    def test_one_service_of_the_project(self):
        client = Client(server())
        self.assertEqual(['shop_shop-db_1'], names(site_containers(client, 'shop', 'shop.example', 'shop-db')))
        self.assertEqual(['shop_shop_1'], names(site_containers(client, 'shop', 'shop.example', 'shop')))
        self.assertEqual([], names(site_containers(client, 'shop', 'shop.example', 'myshop')))

    def test_the_daemon_is_asked_by_label_and_for_stopped_containers_too(self):
        client = Client(server())
        site_containers(client, 'shop', 'shop.example', 'shop')
        self.assertEqual([{'label': ['com.docker.compose.project=shop', 'com.docker.compose.service=shop']}],
                         client.filters)

    def test_a_site_without_a_name_selects_nothing(self):
        client = Client(server())
        for name in (None, '', 7):
            self.assertEqual([], site_containers(client, name, 'shop.example'))
        self.assertEqual([], client.filters)

    def test_a_project_of_the_same_name_started_from_another_directory_is_not_the_sites(self):
        client = Client(server_with_other_projects())
        self.assertEqual(['n8n_n8n-db_1', 'n8n_n8n_1'], names(site_containers(client, 'n8n', 'n8n.example')))
        self.assertEqual(['n8n_n8n-db_1'], names(site_containers(client, 'n8n', 'n8n.example', 'n8n-db')))
        self.assertEqual([], names(site_containers(client, 'n8n', 'n8n.example', 'editor')))
        # The site's own containers carry no directory here; the other project's do.
        self.assertEqual(['shop_shop-db_1', 'shop_shop_1'], names(site_containers(client, 'shop', 'shop.example')))

    def test_the_directory_is_the_one_of_the_website_the_site_is_on(self):
        client = Client(server_with_other_projects())
        self.assertEqual([], site_containers(client, 'n8n', 'other.example'))
        for domain in (None, '', '..', '../n8n.example', 'a/b', ['n8n.example']):
            self.assertEqual([], site_containers(client, 'n8n', domain))

    def test_what_counts_as_the_sites_own_directory(self):
        def belongs(directory, domain='shop.example'):
            return container_of_site(Container('c', 'shop', 'shop', directory=directory), 'shop', domain)

        for directory in ('/home/docker/shop.example', '/home/docker/shop.example/', '/home/docker//shop.example',
                          '/home/docker/Shop.Example'):
            self.assertTrue(belongs(directory), directory)
        # A site of an earlier release whose domain was typed with capitals.
        self.assertTrue(belongs('/home/docker/Shop.Example', 'shop.example'))
        self.assertTrue(belongs('/home/docker/shop.example', 'Shop.Example'))
        for directory in ('/opt/shop', '/home/docker', '/home/docker/shop.example.org', '/home/shop.example',
                          '/home/docker/shop.example/data', 'shop.example', '/home/docker/../docker/other.example'):
            self.assertFalse(belongs(directory), directory)
        self.assertFalse(container_of_site(Container('c', 'shop', 'shop'), 'shop', None))
        self.assertFalse(container_of_site(Container('c'), 'shop', 'shop.example'))
        self.assertFalse(container_of_site(SimpleNamespace(labels=None), 'shop', 'shop.example'))

    def test_a_site_directory_reached_through_a_link_is_still_the_sites_own(self):
        with mock.patch.object(docker_sites.os.path, 'realpath', return_value='/data/home/docker/shop.example'):
            self.assertTrue(container_of_site(
                Container('c', 'shop', 'shop', directory='/data/home/docker/shop.example'), 'shop', 'shop.example'))
            self.assertTrue(container_of_site(
                Container('c', 'shop', 'shop', directory='/home/docker/shop.example'), 'shop', 'shop.example'))


class NameInUseTests(unittest.TestCase):
    """A new site does not get a name under which containers already run on the server."""

    def test_a_name_no_container_runs_under_is_free(self):
        client = Client(server_with_other_projects())
        for name in ('flows', 'sho', 'shop2', 'n8'):
            self.assertFalse(site_name_in_use(client, name), name)

    def test_the_project_of_another_site_or_of_somebody_else_is_in_use(self):
        client = Client(server_with_other_projects())
        for name in ('shop', 'n8n', 'n', 'myshop'):
            self.assertTrue(site_name_in_use(client, name), name)
        # Only the other project is left, and it is stopped.
        client = Client([Container('n8n_n8n-db_2', 'n8n', 'n8n-db', status='exited', directory='/opt/n8n')])
        self.assertTrue(site_name_in_use(client, 'n8n'))
        self.assertEqual([{'label': ['com.docker.compose.project=n8n']}], client.filters)

    def problem(self, rows=0, containers=(), docker_error=None):
        models = SimpleNamespace(DockerSites=mock.Mock())
        models.DockerSites.objects.filter.return_value.count.return_value = rows
        client = Client(list(containers))
        with mock.patch.dict(sys.modules, {'websiteFunctions.models': models}), \
                mock.patch.object(docker_sites.docker, 'from_env', return_value=client,
                                  side_effect=docker_error), \
                mock.patch.object(docker_sites.logging, 'writeToFile'):
            answer = Docker_Sites.site_name_problem('n8n')
        models.DockerSites.objects.filter.assert_called_once_with(SiteName='n8n')
        return answer

    def test_the_customer_is_told_to_choose_another_name(self):
        message = 'The site name "n8n" is in use on this server; choose another.'
        self.assertEqual(message, self.problem(containers=server_with_other_projects()))
        self.assertEqual(message, self.problem(rows=1))
        self.assertIsNone(self.problem(containers=[Container('shop_shop_1', 'shop', 'shop')]))

    def test_a_server_whose_docker_does_not_answer_has_no_such_containers(self):
        self.assertIsNone(self.problem(docker_error=OSError('no Docker here')))


class DeleteTests(unittest.TestCase):
    def delete(self, name, domain=DOMAINS, containers=None):
        domain = DOMAINS[name] if domain is DOMAINS else domain
        site, client = make_site({'domain': domain, 'name': name, 'JobID': None},
                                 server() if containers is None else containers)
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

    def test_deleting_a_site_leaves_a_project_of_the_same_name_alone(self):
        result, commands = self.delete('n8n', containers=server_with_other_projects())
        removed = [command for command in commands if command.startswith('docker rm')]
        self.assertEqual(['docker rm -f full-id-of-n8n_n8n_1', 'docker rm -f full-id-of-n8n_n8n-db_1'], removed)

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
        site, client = make_site(dict(self.DATA), self.containers() + [
            Container('shop_cache_1', 'shop', 'cache', directory='/root/shop')])
        result, commands = run(site, client, 'cleanup_failed_deployment')
        self.assertIs(True, result)
        self.assertEqual('docker-compose -f /home/docker/shop.example/docker-compose.yml -p shop down -v',
                         commands[0])
        removed = [command for command in commands if command.startswith('docker rm')]
        self.assertEqual(['docker rm -f full-id-of-shop_shop_1', 'docker rm -f full-id-of-shop_shop-db_1'],
                         removed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
