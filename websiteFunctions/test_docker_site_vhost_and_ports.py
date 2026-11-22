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

PASSWORD_PROTECTION = '''
### PASSWORD PROTECTION CONF STARTS /home/shop.example/public_html

realm shop {

  userDB  {
    location              /home/shop.example/.htpasswd
  }
}

context / {
  location                /home/shop.example/public_html
  allowBrowse             1
  realm                   shop
}
### PASSWORD PROTECTION CONF ENDS /home/shop.example/public_html
'''


def block(comment, headers):
    """The text a release appended to a virtual host for a Docker site on port 11003."""
    return ('\n\n# %s\ncontext / {\n  type                    proxy\n  handler                 docker11003\n'
            '  addDefaultCharset       off\n  websocket               1\n\n'
            '  extraHeaders            <<<END_extraHeaders\n%s  END_extraHeaders\n}\n' % (
                comment, ''.join('  RequestHeader %s\n' % header for header in headers)))


FORWARDED = ['set X-Forwarded-For $ip', 'set X-Forwarded-Proto https', 'set X-Forwarded-Host "shop.example"']

## Every form of the block that a release has written, oldest first.
RELEASED_BLOCKS = {
    'n8n, origin only': block('N8N Proxy Configuration', ['set Origin "https://shop.example"']),
    'n8n, forwarded for replaced': block('N8N Proxy Configuration', ['unset X-Forwarded-For'] + FORWARDED
                                          + ['set Host "shop.example"']),
    'n8n, with origin': block('N8N Proxy Configuration', FORWARDED + [
        'set Origin "shop.example, shop.example"', 'set Host "shop.example"']),
    'n8n, without origin': block('N8N Proxy Configuration', FORWARDED + ['set Host "shop.example"']),
    'present': block('Docker App Proxy Configuration', FORWARDED + ['set Host "shop.example"']),
}


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

    def test_the_present_block_is_the_one_in_the_list_of_released_blocks(self):
        self.write(VHOST)
        Docker_Sites.SetupAppVhost('shop.example', '11003')
        self.assertEqual(VHOST + RELEASED_BLOCKS['present'], self.read())

    def test_the_block_of_every_release_is_taken_out_when_its_site_is_deleted(self):
        for release, text in RELEASED_BLOCKS.items():
            with self.subTest(release=release):
                self.write(VHOST + text)
                self.assertTrue(Docker_Sites.RemoveAppVhost('shop.example'))
                self.assertEqual(VHOST, self.read())

    def test_a_new_site_replaces_the_block_of_every_release(self):
        # The old site is gone and its block was left behind; the new site has another port.
        for release, text in RELEASED_BLOCKS.items():
            with self.subTest(release=release):
                self.write(VHOST + text)
                self.assertIsNone(Docker_Sites.AppVhostProblem('shop.example'))
                self.assertTrue(Docker_Sites.SetupAppVhost('shop.example', '11012'))
                content = self.read()
                self.assertNotIn('docker11003', content)
                self.assertNotIn('N8N Proxy Configuration', content)
                self.assertEqual(1, content.count('handler                 docker11012'))
                self.assertEqual(1, content.count('context / {'))
                self.assertTrue(content.startswith(VHOST))

    def test_a_website_with_a_context_of_its_own_is_not_reported_as_pointed_at_the_site(self):
        for own in (OWN_CONTEXT, PASSWORD_PROTECTION, '\ncontext /{\n  type proxy\n}\n',
                    '\n  context   /   {\n  type proxy\n}\n'):
            with self.subTest(own=own):
                self.write(VHOST + own)
                with mock.patch('builtins.print') as shown:
                    self.assertFalse(Docker_Sites.SetupAppVhost('shop.example', '11012'))
                self.assertEqual(VHOST + own, self.read())
                problem = Docker_Sites.AppVhostProblem('shop.example')
                self.assertIn('shop.example already has a "context /" block of its own', problem)
                shown.assert_called_once_with(problem)

    def test_a_context_of_its_own_beside_a_block_the_panel_left_is_still_an_obstacle(self):
        content = VHOST + RELEASED_BLOCKS['n8n, with origin'] + OWN_CONTEXT
        self.write(content)
        self.assertFalse(Docker_Sites.SetupAppVhost('shop.example', '11012'))
        self.assertEqual(content, self.read())

    def test_contexts_for_parts_of_the_website_are_no_obstacle(self):
        # VHOST has a context for /.well-known/acme-challenge.
        self.write(VHOST + '\ncontext /blog {\n  type proxy\n  handler other\n}\n')
        self.assertIsNone(Docker_Sites.AppVhostProblem('shop.example'))
        self.assertTrue(Docker_Sites.SetupAppVhost('shop.example', '11012'))

    def test_a_website_without_a_virtual_host_is_an_obstacle(self):
        self.assertIn('no virtual host configuration', Docker_Sites.AppVhostProblem('shop.example'))
        self.assertFalse(Docker_Sites.SetupAppVhost('shop.example', '11012'))
        self.write(VHOST)
        for domain in (None, '', '../shop.example', 'a/b', 'a b'):
            self.assertIsNotNone(Docker_Sites.AppVhostProblem(domain))
            self.assertFalse(Docker_Sites.SetupAppVhost(domain, '11012'))
        self.assertEqual(VHOST, self.read())

    def test_the_pattern_needs_the_panels_comment_and_a_docker_handler(self):
        self.assertIsNone(APP_VHOST_BLOCK.search(
            '# Docker App Proxy Configuration\ncontext / {\n  type proxy\n}\ncontext /x {\n  handler docker11000\n}\n'))
        self.assertIsNone(APP_VHOST_BLOCK.search('context / {\n  handler docker11000\n}\n'))


class VhostCommandTests(unittest.TestCase):
    """The helpers end with a status the deployment can read."""

    def main(self, *arguments, **results):
        with mock.patch.object(sys, 'argv', ['DockerSites.py'] + list(arguments)), \
                mock.patch.object(Docker_Sites, 'SetupAppVhost', return_value=results.get('setup')) as setup, \
                mock.patch.object(Docker_Sites, 'AppVhostProblem', return_value=results.get('problem')) as check, \
                mock.patch('builtins.print') as shown:
            return docker_sites.Main(), setup, check, shown

    def test_setting_up_the_virtual_host_reports_failure(self):
        for name in ('SetupAppVhost', 'SetupN8NVhost'):
            status, setup, check, shown = self.main(name, '--domain', 'shop.example', '--port', '11012', setup=False)
            self.assertEqual(1, status)
            setup.assert_called_once_with('shop.example', '11012')
            status, setup, check, shown = self.main(name, '--domain', 'shop.example', '--port', '11012', setup=True)
            self.assertFalse(status)

    def test_the_check_reports_the_obstacle_and_changes_nothing(self):
        status, setup, check, shown = self.main('CheckAppVhost', '--domain', 'shop.example', problem='in the way')
        self.assertEqual(1, status)
        shown.assert_called_once_with('in the way')
        setup.assert_not_called()
        status, setup, check, shown = self.main('CheckAppVhost', '--domain', 'shop.example', problem=None)
        self.assertFalse(status)
        check.assert_called_once_with('shop.example')

    def test_the_file_ends_with_the_status_of_its_command(self):
        with open(docker_sites.__file__.replace('.pyc', '.py')) as handle:
            self.assertTrue(handle.read().rstrip().endswith('sys.exit(Main())'))


def deploy(answers):
    """Run the real deployment of an n8n site; ``answers`` maps part of a helper command to its (status, output)."""
    site = Docker_Sites.__new__(Docker_Sites)
    site.JobID = '/dev/null'
    site.data = {
        'JobID': '/dev/null', 'ComposePath': '/home/docker/shop.example/docker-compose.yml', 'MySQLDBName': 'db',
        'MySQLPassword': 'inert-password', 'CPUsMySQL': 1, 'MemoryMySQL': 512, 'port': '11012', 'CPUsSite': 1,
        'MemorySite': 1024, 'SiteName': 'shop', 'finalURL': 'shop.example', 'adminUser': 'admin',
        'adminPassword': 'inert-password', 'adminEmail': 'admin@example.test',
    }
    commands = []

    def output(command, *more):
        commands.append(command)
        if command == 'docker --help':
            return 'Usage: docker [OPTIONS] COMMAND'
        for part, answer in answers.items():
            if part in command:
                return answer
        return 1, ''

    utilities = SimpleNamespace(installUtilities=mock.Mock())
    with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
            mock.patch.object(docker_sites.ProcessUtilities, 'executioner',
                              side_effect=lambda command, *more: commands.append(command) or 1), \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value=0), \
            mock.patch('plogical.DockerSites.os.path.exists', return_value=False), \
            mock.patch.object(site, 'install_compose_file', return_value=(1, None)), \
            mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities}), \
            mock.patch.object(site, 'verify_system_resources'), \
            mock.patch.object(site, 'check_container_health', return_value=True), \
            mock.patch.object(site, 'monitor_deployment'), \
            mock.patch.object(site, 'log_deployment_metrics'), \
            mock.patch.object(site, 'cleanup_failed_deployment') as cleanup, \
            mock.patch.object(site, 'create_n8n_owner', return_value=True), \
            mock.patch.object(docker_sites.time, 'sleep'), \
            mock.patch.object(docker_sites.logging, 'statusWriter') as status, \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        result = site.DeployComposeApp('n8n')
    return SimpleNamespace(result=result, commands=commands, cleanup=cleanup,
                           messages=[call[0][1] for call in status.call_args_list],
                           restarts=utilities.installUtilities.reStartLiteSpeedSocket.call_count)


OBSTACLE = 'The website shop.example already has a "context /" block of its own'


class DeploymentTests(unittest.TestCase):
    def test_a_website_that_can_be_pointed_at_the_site_is_deployed(self):
        run = deploy({})
        self.assertIs(True, run.result)
        self.assertIn('[200]', run.messages[-1])
        helper = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py '
        self.assertIn(helper + 'CheckAppVhost --domain shop.example', run.commands)
        self.assertIn(helper + 'SetupAppVhost --domain shop.example --port 11012', run.commands)

    def test_an_obstacle_is_reported_before_any_container_is_started(self):
        run = deploy({'CheckAppVhost': (0, 'a warning of the interpreter\n' + OBSTACLE + '\n')})
        self.assertIs(False, run.result)
        self.assertEqual('Deployment failed: %s [404]' % OBSTACLE, run.messages[-1])
        self.assertFalse([command for command in run.commands if ' up -d' in command or 'SetupProxy' in command])
        self.assertFalse([message for message in run.messages if '[200]' in message or 'completed' in message])
        self.assertEqual(0, run.restarts)

    def test_an_obstacle_found_when_the_website_is_pointed_at_the_site_fails_the_deployment(self):
        run = deploy({'SetupAppVhost': (0, OBSTACLE + '\n')})
        self.assertIs(False, run.result)
        self.assertEqual('Deployment failed: %s [404]' % OBSTACLE, run.messages[-1])
        self.assertFalse([message for message in run.messages if '[200]' in message or 'completed' in message])
        run.cleanup.assert_called_once_with()
        self.assertEqual(0, run.restarts)

    def test_a_helper_that_says_nothing_or_cannot_be_run_still_fails_the_deployment(self):
        for answer in ((0, ''), (0, None), None, 'text'):
            with self.subTest(answer=answer):
                run = deploy({'SetupAppVhost': answer})
                self.assertIs(False, run.result)
                self.assertEqual('Deployment failed: The website could not be pointed at the application. [404]',
                                 run.messages[-1])


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
