"""Conversion database boundary tests; native MariaDB acceptance is documented separately."""
import contextlib
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from plogical import childDatabaseOwnership as subject

class IdentityTests(unittest.TestCase):
    def test_constants_are_read_as_site_user_without_password(self):
        execute = Mock(side_effect=[(1,'present'),(1,'site_db\n'),(1,'site_user\n')])
        self.assertEqual({'DB_NAME':'site_db','DB_USER':'site_user'}, subject.wordpress_identity('/home/site/public_html','siteuser','/php',execute))
        for call in execute.call_args_list:
            self.assertEqual('siteuser', call.args[1])
            self.assertNotIn('DB_PASSWORD',call.args[0])
            self.assertNotIn('--allow-root',call.args[0])
        self.assertIn('/usr/bin/timeout 20',execute.call_args.args[0])
    def test_missing_configuration_returns_no_identity(self):
        execute = Mock(return_value=(1,'absent'))
        self.assertIsNone(subject.wordpress_identity('/home/site/public_html','siteuser','/php',execute))
        self.assertEqual(1,execute.call_count)
        self.assertIn('wp-includes',execute.call_args.args[0])
    def test_root_and_invalid_users_are_refused(self):
        for user in ('root','bad;user','../user'):
            with self.assertRaises(ValueError): subject.wordpress_identity('/home/x',user,'/php',Mock())
    def test_failed_or_ambiguous_probe_is_refused(self):
        for result in ((0,'private config'),(1,'unexpected')):
            with self.assertRaises(ValueError) as error: subject.wordpress_identity('/home/x','siteuser','/php',Mock(return_value=result))
            self.assertNotIn('private config',str(error.exception))
    def test_invalid_constant_is_refused_without_printing_output(self):
        execute=Mock(side_effect=[(1,'present'),(1,'secret\nother')])
        with self.assertRaises(ValueError) as error: subject.wordpress_identity('/home/x','siteuser','/php',execute)
        self.assertNotIn('secret',str(error.exception))

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.db=NS(pk=12,dbName='clone_db',dbUser='clone_user',website_id=1)
        self.db.save=Mock()
        self.master=NS(pk=1,domain='parent.example.test',externalApp='siteuser',phpSelection='PHP 8.3')
        self.target=NS(pk=2,domain='child.example.test',externalApp='childuser',phpSelection='PHP 8.3')
        self.child=NS(pk=4,master=self.master,domain=self.target.domain,path='/home/parent.example.test/public_html/child')
        self.DB,self.DBU,self.W,self.S,self.ST,self.C,self.D= [Mock() for _ in range(7)]
        self.DB.objects.filter.return_value.first.return_value=self.db
        self.DB.objects.filter.return_value.exclude.return_value.exists.return_value=False
        self.DB.objects.select_for_update.return_value.get.return_value=self.db
        self.DBU.objects.filter.return_value.values_list.return_value=[]
        self.DBU.objects.filter.return_value.exclude.return_value.exists.return_value=False
        self.W.objects.get.side_effect=lambda **kw: self.master if 'pk' in kw else self.target
        self.S.objects.filter.return_value=[]
        self.ST.objects.filter.return_value.exists.return_value=False
        self.C.objects.filter.return_value.exclude.return_value.values_list.return_value=[]
        self.D.objects.filter.return_value=[]
        self.conn,self.cursor=Mock(),Mock()
        self.cursor.fetchall.return_value=[]
        self.sql=Mock(); self.sql.setupConnection.return_value=(self.conn,self.cursor)
        self.modules={'databases.models':NS(Databases=self.DB,DatabasesUsers=self.DBU),
            'websiteFunctions.models':NS(Websites=self.W,WPSites=self.S,WPStaging=self.ST,ChildDomains=self.C),
            'cloudAPI.models':NS(WPDeployments=self.D),
            'managePHP.phpManager':NS(PHPManager=NS(getPHPString=lambda x:'83')),
            'plogical.processUtilities':NS(ProcessUtilities=Mock()),
            'plogical.mysqlUtilities':NS(mysqlUtilities=self.sql)}
        self.patch=patch.dict(sys.modules,self.modules); self.patch.start(); self.addCleanup(self.patch.stop)
    def test_registered_shared_primary_user_is_refused(self):
        self.DB.objects.filter.return_value.exclude.return_value.exists.return_value=True
        with self.assertRaisesRegex(ValueError,'shared'): subject.assert_independent_accounts(self.db)
    def test_registered_shared_alias_is_refused(self):
        self.DBU.objects.filter.return_value.exclude.return_value.exists.return_value=True
        with self.assertRaisesRegex(ValueError,'shared'): subject.assert_independent_accounts(self.db)
    def test_manual_cross_database_grant_is_refused_and_connection_closed(self):
        self.cursor.fetchall.side_effect=[[('manual_user',)],[('clone_db',),('parent_db',)]]
        with self.assertRaisesRegex(ValueError,'grants'): subject.assert_independent_accounts(self.db)
        self.conn.close.assert_called_once()
    def test_independent_escaped_database_grants_are_accepted(self):
        self.cursor.fetchall.side_effect=[[('clone_user',)],[('clone\\_db',)]]
        subject.assert_independent_accounts(self.db)
        self.conn.close.assert_called_once()
    def test_unavailable_sql_verification_refuses(self):
        self.sql.setupConnection.return_value=(0,0)
        with self.assertRaises(ValueError): subject.assert_independent_accounts(self.db)
    def test_normalized_site_paths_match(self):
        self.S.objects.filter.return_value=[NS(pk=5,path=self.child.path+'/./')]
        ids, paths=subject.child_metadata(1,self.child.path)
        self.assertEqual([5],ids)
    def test_outgoing_staging_is_refused(self):
        self.S.objects.filter.return_value=[NS(pk=5,path=self.child.path)]
        self.ST.objects.filter.return_value.exists.return_value=True
        with self.assertRaisesRegex(ValueError,'owns staging'): subject.child_metadata(1,self.child.path)
    def test_missing_and_empty_deployment_path_mean_parent_root(self):
        for config in ('{"updates":1}','{"path":""}'):
            self.D.objects.filter.return_value=[NS(config=config)]
            self.assertEqual(['/home/parent.example.test/public_html'],[subject._normal(p) for p in subject.child_metadata(1,self.child.path)[1]])
    def test_invalid_deployment_paths_refuse(self):
        for config in ('{"path":null}','[]','{bad'):
            self.D.objects.filter.return_value=[NS(config=config)]
            with self.assertRaises(ValueError): subject.child_metadata(1,self.child.path)
    def test_child_deployment_refuses(self):
        self.D.objects.filter.return_value=[NS(config='{"path":"child"}')]
        with self.assertRaisesRegex(ValueError,'deployment settings'): subject.child_metadata(1,self.child.path)
    def test_managed_site_without_local_config_refuses(self):
        self.S.objects.filter.return_value=[NS(pk=5,path=self.child.path)]
        with patch.object(subject,'wordpress_identity',return_value=None):
            with self.assertRaisesRegex(ValueError,'no local configuration'): subject.capture_child_database(self.child)
    def test_config_change_during_conversion_refuses(self):
        snap=dict(domain=self.target.domain,master_id=1,db_name='clone_db',db_user='clone_user')
        with patch.object(subject,'wordpress_identity',return_value={'DB_NAME':'other','DB_USER':'clone_user'}):
            with self.assertRaisesRegex(ValueError,'settings changed'): subject.transfer_child_database(snap,'/home/child/public_html')
    def test_database_owner_change_refuses(self):
        snap=dict(domain=self.target.domain,master_id=9,db_name='clone_db',db_user='clone_user',database_id=12)
        with patch.object(subject,'wordpress_identity',return_value={'DB_NAME':'clone_db','DB_USER':'clone_user'}), patch('django.db.transaction.atomic',return_value=contextlib.nullcontext()):
            with self.assertRaisesRegex(ValueError,'ownership changed'): subject.transfer_child_database(snap,'/home/child/public_html')
        self.db.save.assert_not_called()

if __name__ == '__main__': unittest.main()
