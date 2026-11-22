"""n8n sites deployed by earlier versions are reported with what is open about them; nothing is changed."""
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import Docker_Sites, n8n_container_remarks, n8n_owner_missing

try:
    import requests
except ImportError:
    requests = None

OLD = {
    'Config': {'User': 'root', 'Env': ['DB_TYPE=postgresdb', 'N8N_ENCRYPTION_KEY=auto', 'N8N_PORT=5678']},
    'HostConfig': {'PortBindings': {'5678/tcp': [{'HostIp': '', 'HostPort': '11000'}]}},
}
NEW = {
    'Config': {'User': '', 'Env': ['DB_TYPE=postgresdb', 'N8N_ENCRYPTION_KEY=q7Zr0mB1x', 'N8N_PORT=5678']},
    'HostConfig': {'PortBindings': {'5678/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '11001'}]}},
}
DATABASE = {'Config': {'User': 'root', 'Env': ['POSTGRES_USER=postgres']}, 'HostConfig': {'PortBindings': {}}}


class ContainerTests(unittest.TestCase):
    def test_a_container_started_the_old_way(self):
        remarks = n8n_container_remarks(OLD)
        self.assertEqual(3, len(remarks))
        self.assertIn('port 11000 is published on every address', remarks[0])
        self.assertIn('key every older site shares', remarks[1])
        self.assertIn('runs as root', remarks[2])

    def test_a_container_started_the_new_way_needs_no_remark(self):
        self.assertEqual([], n8n_container_remarks(NEW))

    def test_every_address_is_recognised_in_each_form(self):
        for address in ('', '0.0.0.0', '::', None, '203.0.113.7'):
            attrs = {'HostConfig': {'PortBindings': {'5678/tcp': [{'HostIp': address, 'HostPort': '11000'}]}}}
            self.assertEqual(1, len(n8n_container_remarks(attrs)), address)
        for address in ('127.0.0.1', '::1'):
            attrs = {'HostConfig': {'PortBindings': {'5678/tcp': [{'HostIp': address, 'HostPort': '11000'}]}}}
            self.assertEqual([], n8n_container_remarks(attrs), address)

    def test_inspection_data_with_parts_missing(self):
        for attrs in ({}, {'Config': None, 'HostConfig': None}, {'HostConfig': {'PortBindings': None}},
                      {'HostConfig': {'PortBindings': {'5678/tcp': None}}}, {'Config': {'Env': None}}):
            self.assertEqual([], n8n_container_remarks(attrs))


@unittest.skipIf(requests is None, 'requests not installed')
class OwnerTests(unittest.TestCase):
    def ask(self, reply=None, error=None):
        session = mock.Mock()
        if error is not None:
            session.get.side_effect = error
        else:
            session.get.return_value.json.return_value = reply
        with mock.patch('requests.Session', return_value=session):
            return n8n_owner_missing('11000'), session

    def test_an_instance_that_still_offers_its_owner_account(self):
        answer, session = self.ask({'data': {'userManagement': {'showSetupOnFirstLoad': True}}})
        self.assertIs(True, answer)
        session.get.assert_called_once_with('http://127.0.0.1:11000/rest/settings', timeout=10)
        self.assertIs(False, session.trust_env)

    def test_an_instance_with_an_owner(self):
        answer, session = self.ask({'data': {'userManagement': {'showSetupOnFirstLoad': False}}})
        self.assertIs(False, answer)

    def test_an_instance_that_does_not_answer_is_not_called_open(self):
        for error in (requests.ConnectionError('refused'), ValueError('not JSON'), KeyError('data')):
            answer, session = self.ask(error=error)
            self.assertIsNone(answer)
        answer, session = self.ask({'unexpected': 1})
        self.assertIsNone(answer)


class ReportTests(unittest.TestCase):
    def report(self, missing):
        sites = [SimpleNamespace(SiteName='flows', port='11000', admin=SimpleNamespace(domain='flows.example')),
                 SimpleNamespace(SiteName='fresh', port='11001', admin=SimpleNamespace(domain='fresh.example'))]
        models = SimpleNamespace(DockerSites=mock.Mock())
        models.DockerSites.objects.filter.return_value = sites
        containers = {('flows', 'flows'): [SimpleNamespace(attrs=OLD)], ('flows', None): [SimpleNamespace(attrs=OLD), SimpleNamespace(attrs=DATABASE)],
                      ('fresh', 'fresh'): [SimpleNamespace(attrs=NEW)], ('fresh', None): [SimpleNamespace(attrs=NEW), SimpleNamespace(attrs=DATABASE)]}

        def select(client, name, domain, service=None):
            self.assertEqual(name + '.example', domain)
            return containers[(name, service)]

        with mock.patch.dict(sys.modules, {'websiteFunctions.models': models}), \
                mock.patch.object(docker_sites.docker, 'from_env'), \
                mock.patch.object(docker_sites, 'site_containers', side_effect=select), \
                mock.patch.object(docker_sites, 'n8n_owner_missing', side_effect=lambda port: missing[port]):
            report = Docker_Sites.CheckN8NSites()
        models.DockerSites.objects.filter.assert_called_once_with(SiteType=Docker_Sites.N8N)
        return report

    def test_an_old_site_without_an_owner_is_reported_first_of_all(self):
        report = self.report({'11000': True, '11001': False})
        self.assertEqual(4, len(report))
        self.assertTrue(report[0].startswith('flows.example (flows): HAS NO OWNER ACCOUNT'))
        self.assertTrue(all(line.startswith('flows.example (flows): ') for line in report))

    def test_an_old_site_with_an_owner_keeps_its_other_remarks(self):
        report = self.report({'11000': False, '11001': False})
        self.assertEqual(3, len(report))
        self.assertFalse([line for line in report if 'OWNER' in line])

    def test_a_site_deployed_the_new_way_is_not_listed(self):
        # Its database container runs as root in both ways of deploying; that is not a remark about n8n.
        report = self.report({'11000': None, '11001': None})
        self.assertFalse([line for line in report if 'fresh' in line])

    def test_the_check_is_reachable_from_the_command_line(self):
        with mock.patch.object(sys, 'argv', ['DockerSites.py', 'CheckN8NSites']), \
                mock.patch.object(docker_sites, 'django') as framework, \
                mock.patch.object(Docker_Sites, 'CheckN8NSites', return_value=[]) as check, \
                mock.patch('builtins.print') as output:
            docker_sites.Main()
        framework.setup.assert_called_once_with()
        check.assert_called_once_with()
        output.assert_called_once_with('No n8n site needs attention.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
