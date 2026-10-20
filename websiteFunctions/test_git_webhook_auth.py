"""Webhook authentication and scheduler regression coverage (issue #1980)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()
from django.test import RequestFactory
from websiteFunctions.website import WebsiteManager
from websiteFunctions import views
from plogical.IncScheduler import IncScheduler


class GitWebhookAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.secret = Path(self.temp.name) / 'site.webhook_secret'
        self.path_patch = patch.object(WebsiteManager, 'webhookSecretPath', return_value=str(self.secret))
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.factory = RequestFactory()

    def test_unprovisioned_sites_fail_closed(self):
        self.assertFalse(WebsiteManager.verifyWebhookSecret('site.example'))

    def test_empty_secret_fails_closed(self):
        self.secret.write_text('')
        self.assertFalse(WebsiteManager.verifyWebhookSecret('site.example'))

    def test_existing_query_secret_is_accepted(self):
        self.secret.write_text('owned-secret')
        self.assertTrue(WebsiteManager.verifyWebhookSecret('site.example', self.factory.post('/?secret=owned-secret')))

    def test_existing_header_secret_is_accepted(self):
        self.secret.write_text('owned-secret')
        self.assertTrue(WebsiteManager.verifyWebhookSecret('site.example', self.factory.post('/', HTTP_X_WEBHOOK_SECRET='owned-secret')))

    def test_wrong_and_missing_credentials_are_rejected(self):
        self.secret.write_text('owned-secret')
        for request in (None, self.factory.post('/'), self.factory.post('/?secret=incorrect')):
            self.assertFalse(WebsiteManager.verifyWebhookSecret('site.example', request))

    def test_both_real_views_reject_before_side_effects(self):
        with patch('websiteFunctions.website.ApplicationInstaller') as installer, patch('websiteFunctions.website.ProcessUtilities.outputExecutioner') as command:
            for endpoint in (views.webhook, views.gitNotify):
                response = endpoint(self.factory.post('/', data='{}', content_type='application/json'), 'site.example')
                self.assertEqual(response.status_code, 403)
            installer.assert_not_called()
            command.assert_not_called()
        self.assertFalse(self.secret.exists())

    def test_valid_legacy_notification_starts_job(self):
        self.secret.write_text('owned-secret')
        with patch('websiteFunctions.website.ApplicationInstaller') as installer:
            response = views.gitNotify(self.factory.post('/', HTTP_X_WEBHOOK_SECRET='owned-secret'), 'site.example')
            self.assertEqual(json.loads(response.content)['pulled'], 1)
            installer.return_value.start.assert_called_once()

    def test_secret_provisioning_is_stable_and_private(self):
        # Use a real private temporary file, without touching configured sites.
        with patch('websiteFunctions.website.os.path.exists', return_value=True):
            first = WebsiteManager.getOrCreateWebhookSecret('site.example')
            second = WebsiteManager.getOrCreateWebhookSecret('site.example')
        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(self.secret.stat().st_mode & 0o777, 0o600)

    def test_failed_real_git_pull_does_not_create_configuration(self):
        self.secret.write_text('owned-secret')
        folder = Path(self.temp.name) / 'not-a-repository'
        folder.mkdir()
        web = SimpleNamespace(domain='site.example', externalApp='root')
        child = SimpleNamespace(path=str(folder), master=web)
        with patch('websiteFunctions.website.Websites.objects.get', side_effect=LookupError), patch('websiteFunctions.website.ChildDomains.objects.get', return_value=child), patch('websiteFunctions.website.ACLManager.FetchExternalApp', return_value='root'), patch('websiteFunctions.website.GitLogs') as logs, patch('websiteFunctions.website.os.mkdir') as mkdir:
            response = views.webhook(self.factory.post('/', data='{}', content_type='application/json', HTTP_X_WEBHOOK_SECRET='owned-secret'), 'site.example')
            self.assertEqual(json.loads(response.content)['status'], 0)
            self.assertIn('not a git repository', json.loads(response.content)['commandStatus'])
            mkdir.assert_not_called()
            self.assertEqual(logs.call_args.kwargs['type'], 'ERROR')


class GitSchedulerConfigurationTests(unittest.TestCase):
    def test_secret_files_empty_and_invalid_directories_do_not_send(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'site.webhook_secret').write_text('secret')
            Path(folder, 'empty.example').mkdir()
            invalid = Path(folder, 'invalid.example')
            invalid.mkdir()
            (invalid / 'broken').write_text('{}')
            (invalid / 'malformed').write_text('not json')
            with patch.object(IncScheduler, 'gitFolder', folder), patch('plogical.IncScheduler.Websites.objects.get') as get, patch('plogical.IncScheduler.logging.SendEmail') as email:
                IncScheduler.git('Daily')
                get.assert_not_called()
                email.assert_not_called()

    def test_valid_configuration_still_sends_report(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder, 'valid.example')
            site.mkdir()
            (site / 'config').write_text(json.dumps({'domain': 'valid.example', 'folder': '/home/valid.example/public_html', 'autoCommit': 'Never', 'autoPush': 'Never'}))
            web = SimpleNamespace(domain='valid.example', adminEmail='owned@example.invalid')
            with patch.object(IncScheduler, 'gitFolder', folder), patch('plogical.IncScheduler.Websites.objects.get', return_value=web), patch('plogical.IncScheduler.GitLogs'), patch('plogical.IncScheduler.logging.SendEmail') as email:
                IncScheduler.git('Daily')
                email.assert_called_once()


if __name__ == '__main__':
    unittest.main()
