"""Real ORM rollback/retention checks on explicitly isolated in-memory tables."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from django.db import connection
from cli.cyberPanel import cyberPanel
from dns.models import Domains as DNSDomains, Records
from emailPremium.models import DomainLimits, EmailLimits, EmailLogs
from loginSystem.models import ACL, Administrator
from mailServer.models import (Domains, EUsers, CatchAllEmail, PlusAddressingOverride,
                               PatternForwarding)
from packages.models import Package
from websiteFunctions.models import Websites, ChildDomains
from plogical import storageQuota
from plogical.mailUtilities import mailUtilities


class MailDomainDeletionTests(unittest.TestCase):
    models = (ACL, Administrator, Package, Websites, ChildDomains, DNSDomains, Records,
              Domains, EUsers, DomainLimits, EmailLimits, EmailLogs, CatchAllEmail,
              PlusAddressingOverride, PatternForwarding)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != 'sqlite' or connection.settings_dict['NAME'] != ':memory:':
            raise RuntimeError('These fixtures require an isolated SQLite memory database.')
        with connection.schema_editor() as schema:
            for model in cls.models:
                schema.create_model(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema:
            for model in reversed(cls.models):
                schema.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        for model in reversed(self.models):
            model.objects.all()._raw_delete('default')
        self.acl = ACL.objects.create(name='fixture')
        self.admin = Administrator.objects.create(userName='fixture', password='unused',
                                                  email='fixture@example.test', type=1, acl=self.acl)
        self.package = Package.objects.create(admin=self.admin, packageName='fixture',
                                              diskSpace=100, bandwidth=100, emailAccounts=0)
        self.site = Websites.objects.create(admin=self.admin, package=self.package,
                                            domain='example.test', adminEmail='fixture@example.test',
                                            phpSelection='PHP 8.3', ssl=0, externalApp='fixture')
        self.zone = DNSDomains.objects.create(admin=self.admin, name='example.test', type='NATIVE')
        self.record = Records.objects.create(domainOwner=self.zone, name='example.test',
                                              type='MX', content='mail.example.test', ttl=300)
        self.domain = Domains.objects.create(domain='example.test', domainOwner=self.site)
        self.account = EUsers.objects.create(email='one@example.test', emailOwner=self.domain,
                                               password='unused', mail='maildir:/owned/fixture/Maildir')
        self.domain_limit = DomainLimits.objects.create(domain=self.domain)
        self.email_limit = EmailLimits.objects.create(email=self.account)
        enrollment_patch = patch.object(storageQuota, 'has_enrollment', return_value=False)
        self.enrollment = enrollment_patch.start()
        self.addCleanup(enrollment_patch.stop)
        logging_patch = patch('plogical.CyberCPLogFileWriter.CyberCPLogFileWriter.writeToFile')
        logging_patch.start()
        self.addCleanup(logging_patch.stop)

    def delete(self, **kwargs):
        return mailUtilities.deleteEmailAccount(self.account.pk, **kwargs)

    def assert_retained(self):
        self.assertTrue(EUsers.objects.filter(pk=self.account.pk).exists())
        self.assertTrue(Domains.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(EmailLimits.objects.filter(pk=self.email_limit.pk).exists())
        self.assertTrue(DomainLimits.objects.filter(pk=self.domain_limit.pk).exists())

    def test_cli_last_mailbox_removes_empty_unenrolled_domain(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cyberPanel().deleteEmail(self.account.pk)
        self.assertEqual({'success': 1, 'errorMessage': 'None'}, json.loads(output.getvalue()))
        self.assertFalse(EUsers.objects.exists())
        self.assertFalse(Domains.objects.exists())
        self.assertFalse(DomainLimits.objects.exists())
        self.assertFalse(EmailLimits.objects.exists())
        self.assertTrue(Websites.objects.filter(pk=self.site.pk).exists())
        self.assertTrue(DNSDomains.objects.filter(pk=self.zone.pk).exists())
        self.assertTrue(Records.objects.filter(pk=self.record.pk).exists())

    def test_native_ui_last_mailbox_uses_same_cleanup(self):
        from django.test import RequestFactory
        from mailServer.mailserverManager import MailServerManager
        from plogical.acl import ACLManager
        request = RequestFactory().post('/email/submitEmailDeletion', json.dumps({'email': self.account.pk}),
                                        content_type='application/json')
        request.session = {'userID': self.admin.pk}
        with patch.object(ACLManager, 'loadedACL', return_value={}), \
                patch.object(ACLManager, 'currentContextPermission', return_value=1), \
                patch.object(ACLManager, 'checkOwnership', return_value=1) as ownership:
            response = json.loads(MailServerManager(request).submitEmailDeletion().content)
        self.assertEqual(1, response['deleteEmailStatus'])
        ownership.assert_called_once_with(self.site.domain, self.admin, {})
        self.assertFalse(EUsers.objects.exists())
        self.assertFalse(Domains.objects.exists())

    def test_nonlast_mailbox_keeps_domain_and_other_account(self):
        other = EUsers.objects.create(email='two@example.test', emailOwner=self.domain, password='unused')
        self.assertEqual((1, 'None'), self.delete())
        self.assertTrue(EUsers.objects.filter(pk=other.pk).exists())
        self.assertTrue(Domains.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(DomainLimits.objects.filter(pk=self.domain_limit.pk).exists())
        self.assertFalse(EmailLimits.objects.filter(pk=self.email_limit.pk).exists())

    def test_any_registered_scope_keeps_empty_domain(self):
        self.enrollment.return_value = True
        self.assertEqual((1, 'None'), self.delete())
        self.enrollment.assert_called_once_with(self.site)
        self.assertTrue(Domains.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(DomainLimits.objects.filter(pk=self.domain_limit.pk).exists())

    def test_registry_failure_refuses_before_any_deletion(self):
        self.enrollment.side_effect = ValueError('Registry unavailable')
        self.assertEqual((0, 'Registry unavailable'), self.delete())
        self.assert_retained()

    def test_child_domain_uses_master_enrollment(self):
        child = ChildDomains.objects.create(master=self.site, domain='child.example.test',
                                             path='/owned/child', ssl=0, phpSelection='PHP 8.3')
        self.domain.domainOwner = None; self.domain.childOwner = child; self.domain.save()
        self.enrollment.return_value = True
        self.assertEqual((1, 'None'), self.delete())
        self.enrollment.assert_called_once_with(self.site)
        self.assertTrue(ChildDomains.objects.filter(pk=child.pk).exists())
        self.assertTrue(Domains.objects.exists())

    def test_matching_child_and_domain_owner_is_accepted(self):
        child = ChildDomains.objects.create(master=self.site, domain='child.example.test',
                                             path='/owned/child', ssl=0, phpSelection='PHP 8.3')
        self.domain.childOwner = child; self.domain.save()
        self.assertEqual((1, 'None'), self.delete())
        self.assertTrue(ChildDomains.objects.filter(pk=child.pk).exists())
        self.assertFalse(Domains.objects.exists())

    def test_conflicting_child_ownership_refuses(self):
        other = Websites.objects.create(admin=self.admin, package=self.package, domain='other.test',
                                         adminEmail='fixture@other.test', phpSelection='PHP 8.3', ssl=0,
                                         externalApp='otherfixture')
        child = ChildDomains.objects.create(master=other, domain='child.example.test',
                                             path='/owned/child', ssl=0, phpSelection='PHP 8.3')
        self.domain.childOwner = child; self.domain.save()
        self.assertEqual(0, self.delete()[0])
        self.enrollment.assert_not_called()
        self.assert_retained()

    def test_ownerless_domain_refuses(self):
        self.domain.domainOwner = None; self.domain.save()
        self.assertEqual(0, self.delete()[0])
        self.enrollment.assert_not_called()
        self.assert_retained()

    def test_authorization_uses_resolved_owner_before_enrollment(self):
        owners = []
        def authorize(website):
            owners.append((website.pk, connection.in_atomic_block))
            return False
        self.assertEqual(0, self.delete(authorize=authorize)[0])
        self.assertEqual([(self.site.pk, True)], owners)
        self.enrollment.assert_not_called()
        self.assert_retained()

    def test_authorization_exception_rolls_back(self):
        def authorize(website):
            raise ValueError('Ownership changed')
        self.assertEqual((0, 'Ownership changed'), self.delete(authorize=authorize))
        self.assert_retained()

    def test_mailbox_deletion_failure_retains_domain_and_limits(self):
        with patch.object(EUsers, 'delete', side_effect=RuntimeError('Mailbox deletion refused')):
            self.assertEqual((0, 'Mailbox deletion refused'), self.delete())
        self.assert_retained()

    def test_domain_deletion_failure_rolls_back_mailbox_and_limits(self):
        with patch.object(Domains, 'delete', side_effect=RuntimeError('Domain deletion refused')):
            self.assertEqual((0, 'Domain deletion refused'), self.delete())
        self.assert_retained()

    def test_quota_check_runs_inside_transaction(self):
        observed = []
        self.enrollment.side_effect = lambda website: observed.append(connection.in_atomic_block) or False
        self.assertEqual((1, 'None'), self.delete())
        self.assertEqual([True], observed)

    def test_missing_account_is_failure_and_does_not_remove_empty_domain(self):
        self.account.delete()
        self.assertEqual(0, self.delete()[0])
        self.assertTrue(Domains.objects.exists())
        self.enrollment.assert_not_called()

    def test_existing_mail_content_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory)/'owned-message'
            message.write_bytes(b'Preserve retained Maildir content.')
            self.account.mail = 'maildir:'+directory; self.account.save()
            self.assertEqual((1, 'None'), self.delete())
            self.assertEqual(b'Preserve retained Maildir content.', message.read_bytes())
