"""A website creation that is refused ends the WordPress flows with the reason in the status file."""
import json
import os
import sys
import tempfile
import types
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.phpConfig import normalized_php_selection, stored_php_selection
from plogical.test_php_restart_marker import load_methods
from plogical.wordpressInstallerUtilities import worker_failure_reason

REFUSAL = 'Apache is not set up on this server yet.'


class Response:
    def __init__(self, payload):
        self.content = json.dumps(payload).encode()


class WordPressCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wp-create-test-')
        self.addCleanup(self.temp.cleanup)
        self.status = os.path.join(self.temp.name, 'status')
        self.creation_status = os.path.join(self.temp.name, 'creation')
        self.manager = mock.Mock()
        website_module = types.ModuleType('websiteFunctions.website')
        website_module.WebsiteManager = lambda: self.manager
        patcher = mock.patch.dict(sys.modules, {'websiteFunctions.website': website_module})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.websites = mock.Mock()
        self.websites.objects.get.side_effect = LookupError('no such website')
        process = mock.Mock(debugPath=os.path.join(self.temp.name, 'no-debug'))
        self.namespace = dict(
            Websites=self.websites, Administrator=mock.Mock(), ACLManager=mock.Mock(), ProcessUtilities=process,
            logging=mock.Mock(), os=os, time=mock.Mock(), wpplugins=mock.Mock(),
            normalized_php_selection=normalized_php_selection, stored_php_selection=stored_php_selection,
            worker_failure_reason=worker_failure_reason)
        self.create, self.staging_site = load_methods(
            'plogical/applicationInstaller.py', 'ApplicationInstaller',
            ['wordpressInstallNew', '_createStagingWebsite'], self.namespace)
        data = dict(tempStatusPath=self.status, domainName='new.example', adminEmail='owner@example.test',
                    websiteOwner='owner', package='Default', adminID=7, apacheBackend=1, StagingDomain='stage.example')
        self.installer = NS(data=data, extraArgs=data, foundBeforeCreation=lambda domain: ())
        self.source = NS(owner=NS(adminEmail='owner@example.test', phpSelection='PHP 8.3',
                                  admin=NS(userName='owner')))

    def refuse(self):
        self.manager.submitWebsiteCreation.return_value = Response(
            {'status': 0, 'createWebSiteStatus': 0, 'error_message': REFUSAL})

    def accept(self, line):
        with open(self.creation_status, 'w') as handle:
            handle.write(line)
        self.manager.submitWebsiteCreation.return_value = Response(
            {'status': 1, 'createWebSiteStatus': 1, 'error_message': 'None', 'tempStatusPath': self.creation_status})

    def status_text(self):
        with open(self.status) as handle:
            return handle.read()

    def test_new_wordpress_site_reports_the_refusal_and_stops(self):
        self.refuse()
        self.assertEqual(0, self.create(self.installer))
        self.assertEqual('Failed to Create Website: error: %s. [404]' % REFUSAL, self.status_text())
        self.manager.submitWebsiteCreation.assert_called_once()

    def test_new_wordpress_site_reports_a_refusal_without_a_status_number(self):
        self.manager.submitWebsiteCreation.return_value = Response({'error_message': REFUSAL})
        self.assertEqual(0, self.create(self.installer))
        self.assertEqual('Failed to Create Website: error: %s. [404]' % REFUSAL, self.status_text())

    def test_new_wordpress_site_still_reports_a_failed_creation_worker(self):
        self.accept('Invalid PHP version selected. [404]')
        self.assertEqual(0, self.create(self.installer))
        self.assertIn('[404]', self.status_text())
        self.assertIn('Invalid PHP version selected.', self.status_text())

    def test_staging_site_reports_the_refusal_and_stops(self):
        self.refuse()
        self.assertIsNone(self.staging_site(self.installer, self.source, 7, self.status, self.status))
        self.assertEqual('Failed to Create Website: error: %s[404]' % REFUSAL, self.status_text())
        self.websites.objects.get.assert_not_called()

    def test_staging_site_is_returned_when_the_creation_succeeds(self):
        self.accept('Website created. [200]')
        self.websites.objects.get.side_effect = None
        site = self.staging_site(self.installer, self.source, 7, self.status, self.status)
        self.assertIs(self.websites.objects.get.return_value, site)
        self.websites.objects.get.assert_called_once_with(domain='stage.example')

    def test_staging_site_is_created_with_the_stored_version_in_the_panels_form(self):
        self.accept('Website created. [200]')
        self.websites.objects.get.side_effect = None
        for stored, selection in (('PHP 74', 'PHP 7.4'), ('php 8.1', 'PHP 8.1'), ('PHP 8.3', 'PHP 8.3')):
            with self.subTest(stored=stored):
                self.source.owner.phpSelection = stored
                self.staging_site(self.installer, self.source, 7, self.status, self.status)
                self.assertEqual(selection, self.manager.submitWebsiteCreation.call_args[0][1]['phpSelection'])


if __name__ == '__main__':
    unittest.main()
