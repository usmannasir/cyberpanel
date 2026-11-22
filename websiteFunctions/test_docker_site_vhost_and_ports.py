"""A deleted Docker site leaves no website pointing at its port, and its port is never given to another site."""
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import APP_VHOST_BLOCK, Docker_Sites, next_site_port

VHOST = '''docRoot                   $VH_ROOT/public_html
vhDomain                  $VH_NAME
enableGzip                1

context /.well-known/acme-challenge {
  location                /usr/local/lsws/Example/html/.well-known/acme-challenge
  allowBrowse             1
}

rewrite  {
  enable                  1
  autoLoadHtaccess        1
}
'''

OWN_CONTEXT = '''
context / {
  type                    proxy
  handler                 mybackend
  addDefaultCharset       off
}
'''


class VhostTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='docker-site-vhost-')
        self.addCleanup(shutil.rmtree, self.directory)
        self.path = os.path.join(self.directory, 'vhost.conf')
        real_open = open
        real_exists = os.path.exists

        def redirected(path, *args, **kwargs):
            if str(path).startswith('/usr/local/lsws/conf/vhosts/'):
                path = self.path
            return real_open(path, *args, **kwargs)

        def exists(path):
            if str(path).startswith('/usr/local/lsws/conf/vhosts/'):
                return real_exists(self.path)
            return real_exists(path)

        for patcher in (mock.patch('builtins.open', side_effect=redirected),
                        mock.patch('os.path.exists', side_effect=exists),
                        mock.patch.object(docker_sites.logging, 'writeToFile')):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, content):
        with open(self.path, 'w') as handle:
            handle.write(content)

    def read(self):
        with open(self.path) as handle:
            return handle.read()

    def test_the_context_the_panel_added_is_taken_out_again(self):
        self.write(VHOST)
        self.assertTrue(Docker_Sites.SetupAppVhost('shop.example', '11007'))
        self.assertIn('handler                 docker11007', self.read())
        self.assertTrue(Docker_Sites.RemoveAppVhost('shop.example'))
        self.assertEqual(VHOST, self.read())

    def test_what_follows_the_context_stays_in_place(self):
        self.write(VHOST)
        Docker_Sites.SetupAppVhost('shop.example', '11007')
        with open(self.path, 'a') as handle:
            handle.write('errorlog $VH_ROOT/logs/error.log {\n  logLevel WARN\n}\n')
        self.assertTrue(Docker_Sites.RemoveAppVhost('shop.example'))
        self.assertEqual(VHOST + 'errorlog $VH_ROOT/logs/error.log {\n  logLevel WARN\n}\n', self.read())

    def test_a_context_the_administrator_wrote_is_not_touched(self):
        self.write(VHOST + OWN_CONTEXT)
        self.assertFalse(Docker_Sites.RemoveAppVhost('shop.example'))
        self.assertEqual(VHOST + OWN_CONTEXT, self.read())

    def test_a_virtual_host_without_the_context_is_not_rewritten(self):
        self.write(VHOST)
        before = os.stat(self.path).st_mtime_ns
        self.assertFalse(Docker_Sites.RemoveAppVhost('shop.example'))
        self.assertEqual(before, os.stat(self.path).st_mtime_ns)

    def test_no_virtual_host_and_unusable_domains(self):
        self.assertFalse(Docker_Sites.RemoveAppVhost('shop.example'))
        self.write(VHOST)
        Docker_Sites.SetupAppVhost('shop.example', '11007')
        for domain in (None, '', '../shop.example', 'a/b', 'a b'):
            self.assertFalse(Docker_Sites.RemoveAppVhost(domain))
        self.assertIn('docker11007', self.read())

    def test_a_new_site_replaces_the_context_left_by_a_site_deleted_earlier(self):
        self.write(VHOST)
        Docker_Sites.SetupAppVhost('shop.example', '11007')
        self.assertTrue(Docker_Sites.SetupAppVhost('shop.example', '11012'))
        content = self.read()
        self.assertNotIn('docker11007', content)
        self.assertEqual(1, content.count('handler                 docker11012'))
        self.assertEqual(1, content.count('context / {'))

    def test_a_new_site_still_leaves_the_administrators_own_context_alone(self):
        self.write(VHOST + OWN_CONTEXT)
        self.assertTrue(Docker_Sites.SetupAppVhost('shop.example', '11012'))
        self.assertEqual(VHOST + OWN_CONTEXT, self.read())

    def test_the_pattern_needs_the_panels_comment_and_a_docker_handler(self):
        self.assertIsNone(APP_VHOST_BLOCK.search(
            '# Docker App Proxy Configuration\ncontext / {\n  type proxy\n}\ncontext /x {\n  handler docker11000\n}\n'))
        self.assertIsNone(APP_VHOST_BLOCK.search('context / {\n  handler docker11000\n}\n'))


class PortTests(unittest.TestCase):
    CONFIG = '''extprocessor docker11000 {
  type                    proxy
  address                 127.0.0.1:11000
}
extprocessor docker11004 {
  type                    proxy
  address                 127.0.0.1:11004
}
'''

    def test_the_first_site(self):
        self.assertEqual('11000', next_site_port([], ''))
        self.assertEqual('11000', next_site_port([], None))

    def test_above_every_site_there_is_not_just_the_newest(self):
        self.assertEqual('11003', next_site_port(['11000', '11002', '11001']))

    def test_the_port_of_a_deleted_site_is_not_handed_out_again(self):
        # 11004 was deleted; the web server still knows it and a website may still point at it.
        self.assertEqual('11005', next_site_port(['11000', '11001'], self.CONFIG))
        self.assertEqual('11005', next_site_port([], self.CONFIG))
        self.assertEqual('11008', next_site_port(['11007'], self.CONFIG))

    def test_the_other_web_server_format(self):
        self.assertEqual('11010', next_site_port(
            [], '<extProcessor><type>proxy</type><name>docker11009</name></extProcessor>'))

    def test_values_that_are_not_ports_are_ignored(self):
        self.assertEqual('11002', next_site_port(['11001', '', None, 'abc'], 'docker docker- dockerabc'))

    def test_no_port_beyond_the_last_one(self):
        with self.assertRaises(ValueError):
            next_site_port(['65535'])


def create(ports, config):
    site = Docker_Sites.__new__(Docker_Sites)
    site.JobID = '/dev/null'
    site.data = {
        'JobID': '/dev/null', 'Domain': 'shop.example', 'WPemal': 'admin@example.test', 'Owner': 'reseller',
        'userID': 7, 'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 512, 'sitename': 'shop',
        'WPusername': 'admin', 'WPpasswd': 'inert-password', 'externalApp': 'shop1234', 'App': 'WordPress',
    }
    row = mock.Mock(domain='shop.example', externalApp='shop1234')
    row.dockersites_set.all.return_value.count.return_value = 0
    models = SimpleNamespace(DockerSites=mock.Mock(), Websites=mock.Mock())
    models.Websites.objects.filter.return_value.count.return_value = 1
    models.Websites.objects.get.return_value = row
    models.DockerSites.objects.values_list.return_value = ports
    models.DockerSites.objects.count.return_value = len(ports)
    models.DockerSites.objects.last.return_value = SimpleNamespace(port=ports[-1] if ports else None)
    acl = mock.Mock()
    acl.checkOwnership.return_value = 1
    modules = {'websiteFunctions.models': models, 'websiteFunctions.website': SimpleNamespace(WebsiteManager=mock.Mock()),
               'loginSystem.models': SimpleNamespace(Administrator=mock.Mock())}
    with mock.patch.dict(sys.modules, modules), \
            mock.patch.object(docker_sites, 'ACLManager', acl, create=True), \
            mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', return_value=config) as output, \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideServer',
                              return_value=docker_sites.ProcessUtilities.OLS), \
            mock.patch.object(docker_sites.logging, 'writeToFile'), \
            mock.patch.object(docker_sites, 'Docker_Sites') as deployment:
        deployment.web_server_config = Docker_Sites.web_server_config
        Docker_Sites.SubmitDockersiteCreation(site)
    return deployment.call_args[0][1]['port'], models, output


class AllocationTests(unittest.TestCase):
    def test_a_new_site_gets_a_port_no_site_ever_had(self):
        # The newest row is not the highest port, and 11004 belonged to a site that was deleted.
        port, models, output = create(['11002', '11001'], PortTests.CONFIG)
        self.assertEqual('11005', port)
        self.assertEqual('11005', models.DockerSites.call_args[1]['port'])
        output.assert_called_once_with('cat /usr/local/lsws/conf/httpd_config.conf')

    def test_a_web_server_configuration_that_cannot_be_read_still_gives_a_port(self):
        port, models, output = create(['11002', '11001'], None)
        self.assertEqual('11003', port)


class DeleteTests(unittest.TestCase):
    def test_delete_takes_the_context_out_before_the_web_server_is_restarted(self):
        site = Docker_Sites.__new__(Docker_Sites)
        site.data = {'domain': 'shop.example', 'name': 'shop', 'JobID': None}
        site.DockerAppName = 'shop_shop'
        events = []
        utilities = SimpleNamespace(installUtilities=mock.Mock())
        utilities.installUtilities.reStartLiteSpeed.side_effect = lambda: events.append('RESTART')
        client = mock.Mock()
        client.containers.list.return_value = []
        models = SimpleNamespace(Websites=mock.Mock())
        models.Websites.objects.get.return_value = SimpleNamespace(externalApp='shop1234')
        with mock.patch.object(docker_sites.docker, 'from_env', return_value=client), \
                mock.patch.object(docker_sites.ProcessUtilities, 'executioner',
                                  side_effect=lambda command, *more: events.append((command,) + more)), \
                mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value='ubuntu'), \
                mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities,
                                              'websiteFunctions.models': models}), \
                mock.patch.object(docker_sites.logging, 'writeToFile'):
            site.DeleteDockerApp()
        removal = ('/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py RemoveAppVhost '
                   '--domain shop.example',)
        self.assertIn(removal, events)
        self.assertLess(events.index(removal), events.index('RESTART'))

    def test_the_helper_is_reachable_from_the_command_line(self):
        with mock.patch.object(sys, 'argv', ['DockerSites.py', 'RemoveAppVhost', '--domain', 'shop.example']), \
                mock.patch.object(Docker_Sites, 'RemoveAppVhost') as remove:
            docker_sites.Main()
        remove.assert_called_once_with('shop.example')


if __name__ == '__main__':
    unittest.main(verbosity=2)
