"""n8n is offered and accepted with the memory it needs, and a deployment that fails says why and can be tried again."""
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites
from plogical.DockerSites import DOCKER_APPS, DockerDeploymentError, Docker_Sites
from websiteFunctions.test_docker_apps import make_site

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager

ROOT = Path(__file__).resolve().parent.parent
PAGE_SCRIPTS = ('websiteFunctions/static/websiteFunctions/websiteFunctions.js',
                'static/websiteFunctions/websiteFunctions.js')

REQUEST = {
    'sitename': 'flows', 'Owner': 'reseller', 'Domain': 'flows.example',
    'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 768, 'App': 'n8n',
    'WPusername': 'admin', 'WPemal': 'admin@example.test', 'WPpasswd': 'AdminPass123',
}


def submit(package=(4, 4096), **changes):
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': 0}
    acl.currentContextPermission.return_value = 1
    acl.checkOwnerProtection.return_value = 1
    acl.CheckDomainBlackList.return_value = 1
    services['Websites'].objects.filter.return_value.count.return_value = 0
    services['validators'].email.return_value = True
    env['ChildDomains'] = mock.Mock()
    env['ChildDomains'].objects.filter.return_value.count.return_value = 0
    env['PackageAssignment'] = mock.Mock()
    env['DockerPackages'] = mock.Mock()
    env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=package[0], Ram=package[1])
    env['DOCKER_APPS'] = DOCKER_APPS
    env['n8n_password_problem'] = docker_sites.n8n_password_problem
    env['Docker_Sites'] = mock.Mock()
    env['Docker_Sites'].site_name_problem.return_value = None
    reply = json.loads(cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST, **changes)).content)
    return reply, env


def page_defaults(path):
    """The RAM the creation page offers per application, and what it starts with, read from its script."""
    script = (ROOT / path).read_text()
    controller = script[script.index("app.controller('createDockerSite'"):]
    controller = controller[:controller.index('$scope.createdockersite = function')]
    table = {name: (int(site), int(database)) for name, site, database in re.findall(
        r"'(\w+)': \{site: (\d+), database: (\d+)\}", controller)}
    first = re.search(r"\$scope\.App = '(\w+)';", controller).group(1)
    cores = (int(re.search(r'\$scope\.CPUSite = (\d+);', controller).group(1)),
             int(re.search(r'\$scope\.CPUMysql = (\d+);', controller).group(1)))
    return SimpleNamespace(table=table, first=first, cores=cores, controller=controller)


def first_package():
    """The CPUs and RAM of the package the panel creates when the creation page is first opened."""
    source = (ROOT / 'websiteFunctions/website.py').read_text()
    method = source[source.index('    def CreateDockersite('):]
    method = method[:method.index('    def AddDockerpackage(')]
    return (int(re.search(r'\n\s+cpu = (\d+)\n', method).group(1)),
            int(re.search(r'\n\s+Memory = (\d+)\n', method).group(1)))


class MinimumTests(unittest.TestCase):
    def test_n8n_needs_the_memory_it_was_measured_to_start_with(self):
        self.assertEqual(768, DOCKER_APPS['n8n']['minSiteRam'])

    def test_less_is_refused_with_a_message_that_names_the_minimum(self):
        for ram in (767, 512, 256, '512'):
            with self.subTest(ram=ram):
                reply, env = submit(SiteRam=ram)
                self.assertEqual({'status': 0, 'error_message': 'Minimum site ram for n8n should be 768MB.'}, reply)
                env['Docker_Sites'].assert_not_called()

    def test_the_minimum_and_more_are_accepted(self):
        for ram in (768, 1024, 2048):
            with self.subTest(ram=ram):
                reply, env = submit(SiteRam=ram)
                self.assertEqual(1, reply['status'], reply)
                self.assertEqual(ram, env['Docker_Sites'].call_args[0][1]['SiteRam'])

    def test_the_other_applications_keep_their_minimum(self):
        self.assertEqual(256, DOCKER_APPS['WordPress']['minSiteRam'])
        self.assertEqual(2048, DOCKER_APPS['Hermes']['minSiteRam'])


class PageDefaultTests(unittest.TestCase):
    def test_every_application_is_offered_with_at_least_its_minimum(self):
        for path in PAGE_SCRIPTS:
            page = page_defaults(path)
            self.assertEqual(set(DOCKER_APPS), set(page.table), path)
            for app, (site, database) in page.table.items():
                with self.subTest(path=path, app=app):
                    self.assertGreaterEqual(site, DOCKER_APPS[app]['minSiteRam'])
                    self.assertGreaterEqual(database, 256)

    def test_the_page_opens_with_n8n_and_its_values_and_follows_the_selected_application(self):
        for path in PAGE_SCRIPTS:
            with self.subTest(path=path):
                page = page_defaults(path)
                self.assertEqual('n8n', page.first)
                self.assertIn("$scope.RamSite = dockerAppRam['n8n'].site;", page.controller)
                self.assertIn("$scope.rammysql = dockerAppRam['n8n'].database;", page.controller)
                changed = page.controller[page.controller.index('$scope.appChanged = function'):]
                self.assertIn("dockerAppRam[$scope.App] || dockerAppRam['WordPress']", changed)
                self.assertIn('$scope.RamSite = ram.site;', changed)
                self.assertIn('$scope.rammysql = ram.database;', changed)
                self.assertNotIn('512;', page.controller)

    def test_both_copies_of_the_script_offer_the_same(self):
        first, second = (page_defaults(path) for path in PAGE_SCRIPTS)
        self.assertEqual(first.table, second.table)
        self.assertEqual(first.controller, second.controller)

    def test_the_untouched_page_is_accepted_under_the_first_package_the_panel_creates(self):
        cores, memory = first_package()
        self.assertEqual((2, 1024), (cores, memory))
        for path in PAGE_SCRIPTS:
            page = page_defaults(path)
            site, database = page.table[page.first]
            self.assertLessEqual(site + database, memory, path)
            self.assertLessEqual(sum(page.cores), cores, path)
            reply, env = submit(package=(cores, memory), App=page.first, SiteRam=site, MYsqlRam=database,
                                SiteCPU=page.cores[0], MysqlCPU=page.cores[1])
            self.assertEqual(1, reply['status'], reply)

    def test_the_page_loads_the_changed_script(self):
        # The page asks for the script under a suffix of its own, so browsers fetch the version with the
        # memory defaults (and anything changed later) instead of an older cached copy.
        template = (ROOT / 'websiteFunctions/templates/websiteFunctions/CreateDockerSite.html').read_text()
        self.assertRegex(template, r"websiteFunctions/websiteFunctions\.js' %\}\?v=\{\{ CP_VERSION \}\}-2026\d{4}-docker-")
        self.assertNotIn("websiteFunctions/websiteFunctions.js' %}?v={{ CP_VERSION }}\"", template)


OOM_LOG = b'''Initializing n8n process
 - N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES -> The default for this variable will be reduced.

<--- Last few GCs --->

[7:0x7ff8e870e000]    21869 ms: Mark-Compact 248.2 (256.9) -> 248.1 (256.9) MB, pooled: 2.2 MB

FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory
----- Native stack trace -----
Initializing n8n process
[license SDK] Skipping renewal on init: license cert is not initialized
(node:8) DeprecationWarning: Calling client.query() is deprecated [200]
'''


def trouble(log=b'', restarts=0, oom_killed=False, found=True, error=None):
    site = make_site('n8n')
    site.data['MemorySite'] = 512
    container = mock.Mock()
    container.attrs = {'State': {'OOMKilled': oom_killed}, 'RestartCount': restarts}
    container.logs.return_value = log
    with mock.patch.object(site, 'find_container_by_service', return_value=container if found else None,
                           side_effect=error) as find, \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        text = site.container_trouble('testapp')
    find.assert_called_once_with('testapp')
    return text, container


class ContainerTroubleTests(unittest.TestCase):
    def test_an_application_that_runs_out_of_memory_is_named_with_its_limit_and_restarts(self):
        text, container = trouble(OOM_LOG, restarts=15)
        self.assertTrue(text.startswith('It ran out of memory with its limit of 512 MB and was restarted 15 times; '
                                        'give the application more RAM. Last lines of its log: FATAL ERROR: '
                                        'Ineffective mark-compacts near heap limit Allocation failed - JavaScript '
                                        'heap out of memory | '), text)
        container.logs.assert_called_once_with(tail=400)

    def test_the_text_is_one_line_that_cannot_end_the_job_on_the_creation_page(self):
        text, container = trouble(OOM_LOG + b'\x1b[31mred\x1b[0m [404] \xff\n', restarts=2)
        self.assertNotIn('\n', text)
        self.assertNotIn('[', text)
        self.assertNotIn(']', text)
        self.assertNotIn('\x1b', text)
        self.assertIn('(200)', text)
        self.assertLess(len(text), 1000)

    def test_memory_taken_by_the_kernel_is_out_of_memory_too(self):
        text, container = trouble(b'starting\n', restarts=3, oom_killed=True)
        self.assertTrue(text.startswith('It ran out of memory with its limit of 512 MB and was restarted 3 times;'))

    def test_restarts_for_another_reason_are_counted_and_the_log_is_shown(self):
        text, container = trouble(b'one\ntwo\n\nthree   spaced\nError: connect ECONNREFUSED db:5432\n', restarts=4)
        self.assertEqual('It was restarted 4 times. Last lines of its log: two | three spaced | '
                         'Error: connect ECONNREFUSED db:5432', text)

    def test_a_long_line_is_cut(self):
        text, container = trouble(b'x' * 5000 + b'\n')
        self.assertEqual('Last lines of its log: ' + 'x' * 200, text)

    def test_nothing_to_show_is_an_empty_text(self):
        self.assertEqual('', trouble(b'')[0])
        self.assertEqual('', trouble(found=False)[0])
        self.assertEqual('', trouble(error=OSError('Docker does not answer'))[0])


def deploy(failure, cleaned=True, site_id=41, app='n8n', unhealthy=(), trouble=''):
    """Run the real deployment of a compose application and let its first-run step fail."""
    site = make_site(app)
    site.JobID = site.data['JobID']
    if site_id is not None:
        site.data['DockerSiteID'] = site_id
    events = []
    rows = mock.Mock()
    rows.objects.filter.return_value.delete.side_effect = lambda: events.append('ENTRY REMOVED')
    models = SimpleNamespace(DockerSites=rows)

    def output(command, *args):
        return 'Usage: docker [OPTIONS] COMMAND' if command == 'docker --help' else (1, '')

    def owner():
        if failure is not None:
            raise failure
        return True

    utilities = SimpleNamespace(installUtilities=mock.Mock())
    with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
            mock.patch.object(docker_sites.ProcessUtilities, 'executioner', return_value=1), \
            mock.patch.object(docker_sites.ProcessUtilities, 'decideDistro', return_value=0), \
            mock.patch('plogical.DockerSites.os.path.exists', return_value=False), \
            mock.patch.object(site, 'install_compose_file', return_value=(1, None)), \
            mock.patch.dict(sys.modules, {'plogical.installUtilities': utilities, 'websiteFunctions.models': models}), \
            mock.patch.object(site, 'verify_system_resources'), \
            mock.patch.object(site, 'check_container_health',
                              side_effect=lambda service: service not in unhealthy) as health, \
            mock.patch.object(site, 'container_trouble', return_value=trouble) as shown, \
            mock.patch.object(site, 'monitor_deployment'), \
            mock.patch.object(site, 'log_deployment_metrics'), \
            mock.patch.object(site, 'cleanup_failed_deployment',
                              side_effect=lambda: events.append('CLEANED') or cleaned) as cleanup, \
            mock.patch.object(site, 'create_n8n_owner', side_effect=owner), \
            mock.patch.object(docker_sites.time, 'sleep'), \
            mock.patch.object(docker_sites.logging, 'statusWriter',
                              side_effect=lambda path, message: events.append(message)), \
            mock.patch.object(docker_sites.logging, 'writeToFile'):
        result = site.DeployComposeApp(app)
    return SimpleNamespace(result=result, events=events, rows=rows, cleanup=cleanup, health=health, shown=shown)


NOT_READY = DockerDeploymentError('n8n did not become ready to create its administrator account within 6 minutes. '
                                  'It ran out of memory with its limit of 512 MB and was restarted 15 times; give '
                                  'the application more RAM.')


class RetryTests(unittest.TestCase):
    def test_a_failed_deployment_tells_the_customer_why(self):
        run = deploy(NOT_READY)
        self.assertIs(False, run.result)
        self.assertEqual('Deployment failed: %s [404]' % NOT_READY.message, run.events[-1])

    def test_a_container_that_does_not_come_up_is_named_with_what_it_shows(self):
        for service in ('testapp-db', 'testapp'):
            with self.subTest(service=service):
                run = deploy(None, unhealthy=(service,), trouble='It was restarted 4 times.')
                self.assertIs(False, run.result)
                self.assertEqual('Deployment failed: Containers failed to reach healthy state. It was restarted 4 '
                                 'times. [404]', run.events[-1])
                run.shown.assert_called_once_with(service)
        run = deploy(None, unhealthy=('testapp',))
        self.assertEqual('Deployment failed: Containers failed to reach healthy state [404]', run.events[-1])
        run = deploy(None, app='Hermes', site_id=None)
        self.assertEqual([mock.call('testapp')], run.health.call_args_list)

    def test_its_entry_is_removed_after_the_clean_up_and_before_the_page_is_told(self):
        for failure in (NOT_READY, RuntimeError('unexpected')):
            with self.subTest(failure=failure):
                run = deploy(failure)
                run.rows.objects.filter.assert_called_once_with(pk=41, SiteName='testapp')
                self.assertEqual(['CLEANED', 'ENTRY REMOVED'], run.events[-3:-1])
                self.assertIn('[404]', run.events[-1])

    def test_the_entry_stays_when_the_clean_up_did_not_work(self):
        for cleaned in (False, None):
            with self.subTest(cleaned=cleaned):
                run = deploy(NOT_READY, cleaned=cleaned)
                run.rows.objects.filter.assert_not_called()
                self.assertIn('[404]', run.events[-1])

    def test_a_deployment_that_was_not_started_for_an_entry_removes_none(self):
        run = deploy(NOT_READY, site_id=None)
        run.rows.objects.filter.assert_not_called()

    def test_a_deployment_that_succeeds_keeps_its_entry(self):
        run = deploy(None)
        self.assertIs(True, run.result)
        run.rows.objects.filter.assert_not_called()
        self.assertNotIn('CLEANED', run.events)

    def test_an_entry_that_cannot_be_removed_does_not_hide_the_failure(self):
        site = make_site('n8n')
        site.data['DockerSiteID'] = 41
        site.cleaned_up = True
        rows = mock.Mock()
        rows.objects.filter.side_effect = OSError('database gone')
        with mock.patch.dict(sys.modules, {'websiteFunctions.models': SimpleNamespace(DockerSites=rows)}), \
                mock.patch.object(docker_sites.logging, 'writeToFile'):
            self.assertIs(False, site.forget_failed_site())

    def test_the_creation_job_hands_the_number_of_its_entry_to_the_deployment(self):
        site = Docker_Sites.__new__(Docker_Sites)
        site.JobID = '/home/cyberpanel/4711'
        site.data = {
            'JobID': '/home/cyberpanel/4711', 'Domain': 'flows.example', 'WPemal': 'admin@example.test',
            'Owner': 'reseller', 'userID': 7, 'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 768,
            'sitename': 'flows', 'WPusername': 'admin', 'WPpasswd': 'AdminPass123', 'externalApp': 'flows1234',
            'App': 'n8n',
        }
        website = mock.Mock(domain='flows.example', externalApp='flows1234')
        website.dockersites_set.all.return_value.count.return_value = 0
        models = SimpleNamespace(DockerSites=mock.Mock(), Websites=mock.Mock())
        models.Websites.objects.filter.return_value.count.return_value = 1
        models.Websites.objects.get.return_value = website
        models.DockerSites.objects.values_list.return_value = []
        models.DockerSites.objects.filter.return_value.count.return_value = 0
        models.DockerSites.return_value.pk = 41
        acl = mock.Mock()
        acl.checkOwnership.return_value = 1
        modules = {'websiteFunctions.models': models,
                   'websiteFunctions.website': SimpleNamespace(WebsiteManager=mock.Mock()),
                   'loginSystem.models': SimpleNamespace(Administrator=mock.Mock())}
        real_open = open
        with mock.patch.dict(sys.modules, modules), \
                mock.patch.object(docker_sites, 'ACLManager', acl, create=True), \
                mock.patch.object(docker_sites, 'randomPassword', mock.Mock(), create=True), \
                mock.patch('builtins.open', side_effect=lambda path, *more: real_open(
                    '/dev/null' if path == '/home/cyberpanel/4711' else path, *more)), \
                mock.patch.object(docker_sites.logging, 'statusWriter'), \
                mock.patch.object(docker_sites.logging, 'writeToFile'), \
                mock.patch.object(docker_sites.docker, 'from_env'), \
                mock.patch.object(docker_sites, 'site_name_in_use', return_value=False), \
                mock.patch.object(docker_sites, 'Docker_Sites') as deployment:
            deployment.web_server_config.return_value = 'extprocessor docker11000 {\n'
            Docker_Sites.SubmitDockersiteCreation(site)
        models.DockerSites.return_value.save.assert_called_once_with()
        job, data = deployment.call_args[0]
        self.assertEqual('DeployN8NContainer', job)
        self.assertEqual(41, data['DockerSiteID'])
        deployment.return_value.start.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2)
