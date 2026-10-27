"""Opt-in remote application identities: validation, consumers, and safety."""
import ast
import contextlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
from env_generator import build_database_config, DatabaseConfigError, rewrite_application_identity, require_fresh_application_installation
from test_env_generator import CreateEnvFileTests
from test_mysql_utilities import CreateDatabaseTests, FakeCursor

ROOT = Path(__file__).resolve().parents[1]


def config(**kw):
    values = dict(remote=True, host='db.internal', port=3307, root_db='mysql', root_user='bootstrap',
                  app_db='panel_a', app_user='panel_a_user')
    values.update(kw)
    return build_database_config(**values)


class IdentityValidationTests(unittest.TestCase):
    def test_defaults_unchanged(self):
        self.assertEqual(build_database_config()['db_name'], 'cyberpanel')
        self.assertEqual(config(app_db=None, app_user=None)['db_user'], 'cyberpanel')

    def test_custom_distinct_from_bootstrap(self):
        c = config()
        self.assertEqual((c['db_name'], c['db_user'], c['root_db_user']), ('panel_a', 'panel_a_user', 'bootstrap'))

    def test_invalid_identities(self):
        for values in ({'remote':False}, {'app_db':None}, {'app_user':None},
                       {'app_db':'mysql'}, {'app_db':'cyberpanel'}, {'app_user':'root'},
                       {'app_user':'bootstrap'}, {'app_db':'a;DROP'}, {'app_db':'x\ny'},
                       {'app_user':'a'*33}, {'app_db':'a'*65}, {'app_user':'üser'}):
            with self.subTest(values=values), self.assertRaises(DatabaseConfigError): config(**values)

    def test_shell_options_reach_python_preflight(self):
        import argparse
        import subprocess
        shell=(ROOT/'cyberpanel.sh').read_text()
        start=shell.rindex('Final_Flags=()')
        end=shell.index('#form up the final',start)
        script=shell[start:end]+'\nprintf "%s\\n" "${Final_Flags[@]}"\n'
        env=os.environ.copy();env.update(Server_IP='192.0.2.1',Remote_MySQL='On',MySQL_Host='10.0.0.2',
            MySQL_DB='mysql',MySQL_User='bootstrap',MySQL_Port='3307',Postfix_Switch='off',PowerDNS_Switch='off',
            PureFTPd_Switch='off',CP_INSTALL_APP_DB='panel_a',CP_INSTALL_APP_USER='panel_a_user')
        args=subprocess.check_output(['bash','-c',script],env=env,text=True).splitlines()
        tree=ast.parse((ROOT/'install/install.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        cutoff=next(i for i,n in enumerate(main.body) if isinstance(n,ast.If))
        ns={'argparse':argparse,'build_database_config':build_database_config,'DatabaseConfigError':DatabaseConfigError,'require_fresh_application_installation':require_fresh_application_installation}
        with patch.object(sys,'argv',['install.py']+args), patch.object(os.path,'exists',return_value=False):
            exec(compile(ast.Module(body=main.body[:cutoff+1],type_ignores=[]),'preflight','exec'),ns)
        self.assertEqual(ns['args'].appdb,'panel_a');self.assertEqual(ns['args'].appuser,'panel_a_user')

    def test_existing_installation_cannot_be_repointed(self):
        with patch.object(os.path,'exists',return_value=True):
            with self.assertRaisesRegex(DatabaseConfigError,'existing configuration was not changed'):
                require_fresh_application_installation('panel_a')
            require_fresh_application_installation(None)

    def test_rewrite_only_identity_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'service'
            path.write_text('user = cyberpanel\ndbname = cyberpanel\npassword = cyberpanel\nquery = SELECT cyberpanel FROM table\n')
            path.chmod(0o640)
            rewrite_application_identity(path,'panel_a','panel_a_user')
            self.assertEqual(path.read_text(),'user = panel_a_user\ndbname = panel_a\npassword = cyberpanel\nquery = SELECT cyberpanel FROM table\n')
            self.assertEqual(path.stat().st_mode & 0o777,0o640)


class CustomEnvTests(CreateEnvFileTests):
    def test_custom_application_env(self):
        values=self._write(database_config=config())
        self.assertEqual(values['DB_NAME'],'panel_a')
        self.assertEqual(values['DB_USER'],'panel_a_user')
        self.assertEqual(values['ROOT_DB_USER'],'bootstrap')


class FreshAccountTests(CreateDatabaseTests):
    def test_collisions_fail_before_any_mutation(self):
        from mysqlUtilities import mysqlUtilities
        for answers in [('10.0.0.4',None,1),('10.0.0.4',None,None,1)]:
            cursor=FakeCursor(); results=iter(answers)
            cursor.fetchone=lambda: (lambda x: None if x is None else (x,))(next(results))
            self._with_connection(cursor)
            self.assertEqual(mysqlUtilities.createDatabase('panel_a','panel_a_user','secret','203.0.113.1',require_fresh=True),0)
            self.assertFalse(any(sql.startswith(('CREATE','ALTER','GRANT')) for sql,_ in cursor.statements))

    def test_fresh_creation_does_not_use_if_not_exists(self):
        from mysqlUtilities import mysqlUtilities
        cursor=FakeCursor();results=iter([('10.0.0.4',),None,None,None]);cursor.fetchone=lambda:next(results)
        self._with_connection(cursor)
        self.assertEqual(mysqlUtilities.createDatabase('panel_a','panel_a_user','secret','203.0.113.1',require_fresh=True),1)
        self.assertNotIn('IF NOT EXISTS',self._sql(cursor))


def load_method(filename, class_name, method_name, namespace, prefix=None):
    tree=ast.parse((ROOT/filename).read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name)
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==method_name)
    method.decorator_list=[]
    class Relocate(ast.NodeTransformer):
        def visit_Constant(self,node):
            if prefix and isinstance(node.value,str) and node.value.startswith(('/etc/','/usr/local/')):
                return ast.copy_location(ast.Constant(str(prefix)+node.value),node)
            return node
    tree=ast.fix_missing_locations(Relocate().visit(ast.Module(body=[method],type_ignores=[])))
    exec(compile(tree,filename,'exec'),namespace)
    return namespace[method_name]


class ServiceWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cwd=Path.cwd();self.addCleanup(os.chdir,self.cwd)
        self.install=self.root/'install';self.install.mkdir()
        shutil.copytree(ROOT/'install/email-configs-one',self.install/'email-configs-one')
        self.obj=SimpleNamespace(cwd=str(self.install),distro=1,remotemysql='ON',mysqlhost='10.0.0.2',mysqlport='3307',appdb='panel_a',appuser='panel_a_user',publicip='192.0.2.1',stdOut=Mock())
        self.ns=dict(os=os,shutil=shutil,sys=sys,stat=__import__('stat'),errno=__import__('errno'),ubuntu=1,centos=0,cent8=2,openeuler=3,
                     subprocess=SimpleNamespace(call=Mock(),run=Mock(return_value=SimpleNamespace(returncode=0)),DEVNULL=-3),
                     logging=SimpleNamespace(InstallLog=SimpleNamespace(writeToFile=Mock())),
                     InstallCyberPanel=SimpleNamespace(stdOut=Mock(),mysqlPassword='fixtureSecret'),
                     install_utils=SimpleNamespace(call=Mock()),preFlightsChecks=SimpleNamespace(call=Mock()),
                     rewrite_application_identity=rewrite_application_identity,get_Ubuntu_release=lambda:24.0)
        from database_consumers import dovecot_connect_line
        self.ns['dovecot_connect_line']=dovecot_connect_line

    def test_actual_mail_writer_24_and_26(self):
        for version in (24.0,26.0):
            self.ns['get_Ubuntu_release']=lambda:version
            method=load_method('install/install.py','preFlightsChecks','setup_email_Passwords',self.ns,self.root)
            self.assertEqual(method(self.obj,'fixtureSecret','One'),1)
            for path in (self.install/'email-configs-one').glob('mysql-virtual*.cf'):
                self.assertIn('user = panel_a_user',path.read_text());self.assertIn('dbname = panel_a',path.read_text())
            path=self.install/'email-configs-one'/('dovecot-sql-2.4.conf' if version==26 else 'dovecot-sql.conf.ext')
            content=path.read_text()
            self.assertIn('panel_a_user',content);self.assertIn('panel_a',content)
            self.assertNotIn('user=cyberpanel',content);self.assertNotIn('dbname = cyberpanel',content)

    def test_actual_powerdns_writer(self):
        (self.root/'etc/powerdns').mkdir(parents=True)
        self.obj.copy_config_file=lambda kind,target,mysql:shutil.copy2(ROOT/'install/dns-one/pdns.conf',target)
        method=load_method('install/installCyberPanel.py','InstallCyberPanel','installPowerDNSConfigurations',self.ns,self.root)
        self.assertEqual(method(self.obj,'fixtureSecret','One'),1)
        content=(self.root/'etc/powerdns/pdns.conf').read_text()
        self.assertIn('gmysql-user=panel_a_user',content);self.assertIn('gmysql-dbname=panel_a',content)

    def test_actual_ftp_writer(self):
        def copy(kind,target,mysql):shutil.copytree(ROOT/'install/pure-ftpd-one',target,dirs_exist_ok=True)
        self.obj.copy_config_file=copy
        method=load_method('install/installCyberPanel.py','InstallCyberPanel','installPureFTPDConfigurations',self.ns,self.root)
        method(self.obj,'One')
        content=(self.root/'etc/pure-ftpd/pureftpd-mysql.conf').read_text()
        self.assertIn('MYSQLUser panel_a_user',content);self.assertIn('MYSQLDatabase panel_a',content)
        self.assertEqual(content,(self.root/'etc/pure-ftpd/db/mysql.conf').read_text())

    def test_actual_fallback_settings(self):
        self.obj.cyberPanelPath=str(self.root);(self.root/'CyberCP').mkdir()
        shutil.copy2(ROOT/'CyberCP/settings.py',self.root/'CyberCP/settings.py')
        self.obj.mysqluser='bootstrap';self.obj.mysqldb='mysql'
        self.ns['generate_pass']=lambda count:'fixtureSecretKey'
        method=load_method('install/install.py','preFlightsChecks','fallback_settings_update',self.ns)
        method(self.obj,'rootSecret','appSecret')
        tree=ast.parse((self.root/'CyberCP/settings.py').read_text())
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATABASES' for t in n.targets))
        ns={'os':os};exec(compile(ast.Module(body=[assignment],type_ignores=[]),'settings','exec'),ns)
        self.assertEqual(ns['DATABASES']['default']['NAME'],'panel_a')
        self.assertEqual(ns['DATABASES']['default']['USER'],'panel_a_user')
        self.assertEqual(ns['DATABASES']['rootdb']['USER'],'bootstrap')
        self.assertIn("'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'", (self.root/'CyberCP/settings.py').read_text())

    def test_upgrade_preserves_custom_env_and_database_identity(self):
        from plogical.test_upgrade_source import preserve_installation_state
        current=self.root/'current';staged=self.root/'staged';current.mkdir();staged.mkdir()
        env=current/'.env';env.write_text('DB_NAME=panel_a\nDB_USER=panel_a_user\n')
        preserve_installation_state(str(current),str(staged),{str(env):str(env)})
        self.assertEqual((staged/'.env').read_text(),env.read_text())
        tree=ast.parse((ROOT/'plogical/upgrade.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Upgrade')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='downloadAndUpgrade')
        statements=[]
        for n in ast.walk(method):
            if isinstance(n,ast.Assign):
                names={t.id for t in ast.walk(n.targets[0]) if isinstance(t,ast.Name)}
                if names & {'database_pattern','database_config','replacements'}:statements.append(n)
        settings={'default':{'NAME':'panel_a','USER':'panel_a_user','PASSWORD':'fixture','HOST':'10.0.0.2','PORT':'3307'},'rootdb':{'NAME':'mysql','USER':'bootstrap'}}
        ns={'settings':SimpleNamespace(DATABASES=settings),'settingsData':(ROOT/'CyberCP/settings.py').read_text(),'re':__import__('re'),'pprint':__import__('pprint')}
        exec(compile(ast.Module(body=sorted(statements,key=lambda x:x.lineno),type_ignores=[]),'upgrade','exec'),ns)
        self.assertEqual(ns['replacements'],1)
        assignment=next(n for n in ast.parse(ns['settingsData']).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATABASES' for t in n.targets))
        self.assertEqual(ast.literal_eval(assignment.value),settings)

    def test_remote_recovery_fails_before_mysql_connect(self):
        tree=ast.parse((ROOT/'plogical/upgrade.py').read_text())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='recover_database_credentials')
        ns={'os':os,'sys':sys,'mysql':Mock()}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'upgrade','exec'),ns)
        from unittest.mock import mock_open
        with patch.object(os.path,'exists',return_value=True),patch('builtins.open',mock_open(read_data='{"mysqlhost":"10.0.0.2"}')):
            with self.assertRaisesRegex(RuntimeError,'no database accounts were changed'):ns[method.name]()
        ns['mysql'].connect.assert_not_called()


if __name__=='__main__':unittest.main()
