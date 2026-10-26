"""DNS cleanup failures must not become successful website deletion."""
import ast
import contextlib
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest import mock
from plogical import test_unix_account_deletion as website_tests

class DNSDeletionTests(unittest.TestCase):
    def setUp(self):
        self.domains=mock.Mock();self.domains.DoesNotExist=type('DoesNotExist',(Exception,),{})
        self.log=mock.Mock()
        atomic=mock.patch('django.db.transaction.atomic',return_value=contextlib.nullcontext());atomic.start();self.addCleanup(atomic.stop)
        self.records,self.comments,self.keys,self.metadata=[mock.Mock() for _ in range(4)]
        tree=ast.parse((Path(__file__).parent/'dnsUtilities.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DNS')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='deleteDNSZone');method.decorator_list=[]
        scope={'Records':self.records,'Comments':self.comments,'Cryptokeys':self.keys,'Domainmetadata':self.metadata,'Domains':self.domains,'logging':NS(CyberCPLogFileWriter=NS(writeToFile=self.log))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'dns-delete','exec'),scope);self.delete=scope['deleteDNSZone']
    def test_success_confirms_deletion(self):
        self.assertEqual(1,self.delete('fixture.test'));self.domains.objects.select_for_update.return_value.get.return_value.delete.assert_called_once()
    def test_current_pdns_children_are_removed_before_zone(self):
        self.assertEqual(1,self.delete('fixture.test'))
        for model in (self.records,self.comments,self.keys,self.metadata):
            model.objects.filter.assert_called_once_with(domain_id=self.domains.objects.select_for_update.return_value.get.return_value.pk)
            model.objects.filter.return_value.delete.assert_called_once()

    def test_absent_zone_is_safe_for_retry(self):
        self.domains.objects.select_for_update.return_value.get.side_effect=self.domains.DoesNotExist()
        self.assertEqual(1,self.delete('fixture.test'))
    def test_lookup_failure_is_not_absence(self):
        self.domains.objects.select_for_update.return_value.get.side_effect=RuntimeError('database unavailable')
        self.assertEqual(0,self.delete('fixture.test'));self.log.assert_called_once()
    def test_foreign_key_failure_is_reported(self):
        self.domains.objects.select_for_update.return_value.get.return_value.delete.side_effect=RuntimeError('foreign key constraint')
        self.assertEqual(0,self.delete('fixture.test'));self.log.assert_called_once()

class WebsiteDNSDeletionTests(unittest.TestCase):
    setUp=website_tests.UnixAccountDeletionTests.setUp
    deletion=website_tests.UnixAccountDeletionTests.deletion
    def test_failed_dns_cleanup_keeps_website_and_databases_for_retry(self):
        for server in (1,2):
            with self.subTest(server=server):
                self.setUp();self.server=server;self.scope['DNS'].deleteDNSZone=lambda domain:0
                self.assertEqual(0,self.deletion());self.assertTrue(self.row_exists)
                self.assertNotIn('database-delete',self.events);self.assertNotIn('website-row-delete',self.events)
    def test_dns_cleanup_precedes_model_and_sql_deletion(self):
        for server in (1,2):
            with self.subTest(server=server):
                self.setUp();self.server=server;self.scope['DNS'].deleteDNSZone=lambda domain:self.events.append('dns-delete') or 1
                self.assertEqual(1,self.deletion())
                self.assertLess(self.events.index('dns-delete'),self.events.index('database-delete'))
                self.assertLess(self.events.index('dns-delete'),self.events.index('website-row-delete'))
