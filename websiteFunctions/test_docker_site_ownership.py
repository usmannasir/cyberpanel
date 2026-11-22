"""An application is put on a website that already exists only for someone who owns that website."""
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import DockerSites as docker_sites

try:
    from .test_wordpress_entitlements import load_wordpress_manager
except ImportError:
    from test_wordpress_entitlements import load_wordpress_manager

REQUEST = {
    'sitename': 'shop', 'Owner': 'reseller', 'Domain': 'victim.example',
    'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 512, 'App': 'WordPress',
    'WPusername': 'admin', 'WPemal': 'admin@example.test', 'WPpasswd': 'inert-password',
}


def submit(website=0, child=0, owns=0, **changes):
    """Run the real entry point for a reseller who may create websites."""
    cls, env, services = load_wordpress_manager()
    acl = services['ACLManager']
    acl.loadedACL.return_value = {'admin': 0}
    acl.currentContextPermission.return_value = 1
    acl.checkOwnerProtection.return_value = 1
    acl.CheckDomainBlackList.return_value = 1
    acl.checkOwnership.return_value = owns
    acl.loadErrorJson.return_value = 'refused'
    services['Websites'].objects.filter.return_value.count.return_value = website
    env['ChildDomains'] = mock.Mock()
    env['ChildDomains'].objects.filter.return_value.count.return_value = child
    env['PackageAssignment'] = mock.Mock()
    env['DockerPackages'] = mock.Mock()
    env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=4, Ram=4096)
    env['DOCKER_APPS'] = docker_sites.DOCKER_APPS
    env['Docker_Sites'] = mock.Mock()
    result = cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST, **changes))
    return result, env, services


class EntryPointTests(unittest.TestCase):
    def test_another_customers_website_is_refused_before_any_job_starts(self):
        for rows in ({'website': 1}, {'child': 1}, {'website': 1, 'child': 1}):
            with self.subTest(rows=rows):
                result, env, services = submit(owns=0, **rows)
                self.assertEqual('refused', result)
                services['ACLManager'].loadErrorJson.assert_called_once_with('createWebSiteStatus', 0)
                env['Docker_Sites'].assert_not_called()

    def test_ownership_is_asked_for_the_named_domain_and_the_signed_in_user(self):
        result, env, services = submit(website=1, owns=0)
        services['Websites'].objects.filter.assert_called_with(domain='victim.example')
        admin = services['Administrator'].objects.get.return_value
        services['ACLManager'].checkOwnership.assert_called_once_with(
            'victim.example', admin, {'admin': 0})
        services['Administrator'].objects.get.assert_any_call(pk=7)

    def test_an_unusable_ownership_answer_is_a_refusal(self):
        for answer in (None, 0, '1', 2, mock.Mock()):
            with self.subTest(answer=answer):
                result, env, services = submit(website=1, owns=answer)
                self.assertEqual('refused', result)
                env['Docker_Sites'].assert_not_called()

    def test_the_owner_of_the_website_may_deploy_on_it(self):
        for rows in ({'website': 1}, {'child': 1}):
            with self.subTest(rows=rows):
                result, env, services = submit(owns=1, **rows)
                self.assertEqual(1, json.loads(result.content)['status'])
                job, data = env['Docker_Sites'].call_args[0]
                self.assertEqual('SubmitDockersiteCreation', job)
                self.assertEqual('victim.example', data['Domain'])
                self.assertEqual(7, data['userID'])
                env['Docker_Sites'].return_value.start.assert_called_once_with()

    def test_a_domain_that_does_not_exist_yet_needs_no_ownership(self):
        result, env, services = submit()
        self.assertEqual(1, json.loads(result.content)['status'])
        services['ACLManager'].checkOwnership.assert_not_called()
        env['Docker_Sites'].return_value.start.assert_called_once_with()

    def test_a_domain_that_is_not_text_is_refused(self):
        for domain in (['victim.example'], {'a': 1}, 7, None):
            with self.subTest(domain=domain):
                result, env, services = submit(website=1, owns=1, Domain=domain)
                self.assertEqual('refused', result)
                env['Docker_Sites'].assert_not_called()

    def test_the_earlier_checks_still_refuse_first(self):
        for name in ('currentContextPermission', 'checkOwnerProtection'):
            with self.subTest(check=name):
                cls, env, services = load_wordpress_manager()
                acl = services['ACLManager']
                acl.loadedACL.return_value = {'admin': 0}
                acl.currentContextPermission.return_value = 1
                acl.checkOwnerProtection.return_value = 1
                getattr(acl, name).return_value = 0
                acl.loadErrorJson.return_value = 'refused'
                env['PackageAssignment'] = mock.Mock()
                env['DockerPackages'] = mock.Mock()
                env['DockerPackages'].objects.get.return_value = SimpleNamespace(CPUs=4, Ram=4096)
                env['DOCKER_APPS'] = docker_sites.DOCKER_APPS
                env['Docker_Sites'] = mock.Mock()
                self.assertEqual('refused', cls().submitDockerSiteCreation(userID=7, data=dict(REQUEST)))
                acl.checkOwnership.assert_not_called()
                env['Docker_Sites'].assert_not_called()


class WorkerTests(unittest.TestCase):
    """The job runs after the request has been answered and decides again."""

    def run_job(self, requested, stored, exists=1, owns=1, manager=None):
        real = docker_sites.Docker_Sites
        handle, status = tempfile.mkstemp(prefix='docker-site-ownership-')
        os.close(handle)
        self.addCleanup(os.remove, status)
        site = real.__new__(real)
        site.JobID = status
        site.data = {
            'JobID': status, 'Domain': requested, 'WPemal': 'admin@example.test', 'Owner': 'reseller',
            'userID': 7, 'MysqlCPU': 1, 'MYsqlRam': 256, 'SiteCPU': 1, 'SiteRam': 512, 'sitename': 'shop',
            'WPusername': 'admin', 'WPpasswd': 'inert-password', 'externalApp': 'victi1234',
            'App': 'WordPress',
        }
        row = mock.Mock(domain=stored, externalApp='owner5678')
        row.dockersites_set.all.return_value.count.return_value = 0
        models = SimpleNamespace(DockerSites=mock.Mock(), Websites=mock.Mock())
        models.Websites.objects.filter.return_value.count.return_value = exists
        models.Websites.objects.get.return_value = row
        models.DockerSites.objects.values_list.return_value = []
        website = SimpleNamespace(WebsiteManager=manager or mock.Mock())
        login = SimpleNamespace(Administrator=mock.Mock())
        acl = mock.Mock()
        acl.checkOwnership.return_value = owns
        acl.loadedACL.return_value = {'admin': 0}
        modules = {'websiteFunctions.models': models, 'websiteFunctions.website': website,
                   'loginSystem.models': login}
        with mock.patch.dict(sys.modules, modules), \
                mock.patch.object(docker_sites, 'ACLManager', acl, create=True), \
                mock.patch.object(docker_sites, 'randomPassword', mock.Mock(), create=True), \
                mock.patch.object(docker_sites.logging, 'writeToFile'), \
                mock.patch.object(docker_sites, 'Docker_Sites') as deployment:
            deployment.web_server_config.return_value = ''
            result = real.SubmitDockersiteCreation(site)
        with open(status) as handle:
            written = handle.read()
        return SimpleNamespace(result=result, status=written, deployment=deployment, models=models,
                               acl=acl, login=login, website=website)

    def test_a_website_the_caller_does_not_own_gets_no_application(self):
        for answer in (0, None, 2):
            with self.subTest(answer=answer):
                run = self.run_job('victim.example', 'victim.example', owns=answer)
                self.assertEqual(0, run.result)
                self.assertIn('[404]', run.status)
                run.models.DockerSites.assert_not_called()
                run.deployment.assert_not_called()
                run.models.Websites.objects.get.assert_not_called()

    def test_ownership_is_decided_for_the_user_who_sent_the_request(self):
        run = self.run_job('victim.example', 'victim.example', owns=0)
        run.login.Administrator.objects.get.assert_called_once_with(pk=7)
        run.acl.loadedACL.assert_called_once_with(7)
        run.acl.checkOwnership.assert_called_once_with(
            'victim.example', run.login.Administrator.objects.get.return_value, {'admin': 0})

    def test_paths_come_from_the_stored_website_not_from_the_request(self):
        # The database matches a domain without regard to case or trailing spaces.
        run = self.run_job('OWNED.example ', 'owned.example')
        job, data = run.deployment.call_args[0]
        self.assertEqual('DeployWPContainer', job)
        self.assertEqual('owned.example', data['finalURL'])
        self.assertEqual('/home/docker/owned.example/docker-compose.yml', data['ComposePath'])
        self.assertEqual('/home/owned.example/public_html/.htaccess', data['htaccessPath'])
        self.assertEqual('/home/owned.example', data['docRoot'])
        self.assertEqual('owner5678', data['externalApp'])
        for value in data.values():
            self.assertNotIn('OWNED', str(value))
        self.assertEqual('owned.example', run.models.DockerSites.call_args[1]['finalURL'])
        run.deployment.return_value.start.assert_called_once_with()

    def test_a_new_domain_is_created_for_the_selected_owner_without_an_ownership_question(self):
        handle, creation = tempfile.mkstemp(prefix='docker-site-ownership-')
        os.write(handle, b'Successfully created. [200]')
        os.close(handle)
        self.addCleanup(os.remove, creation)
        manager = mock.Mock()
        manager.return_value.submitWebsiteCreation.return_value = SimpleNamespace(
            content=json.dumps({'tempStatusPath': creation}))
        run = self.run_job('new.example', 'new.example', exists=0, manager=manager)
        run.acl.checkOwnership.assert_not_called()
        self.assertEqual(1, manager.return_value.submitWebsiteCreation.call_count)
        user, creation_data = manager.return_value.submitWebsiteCreation.call_args[0]
        self.assertEqual(7, user)
        self.assertEqual('new.example', creation_data['domainName'])
        self.assertEqual('reseller', creation_data['websiteOwner'])
        run.deployment.return_value.start.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2)
