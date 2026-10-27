"""Opt-in real MySQL multi-panel identity tests; requires disposable test server.

Uses the same CP_TEST_MYSQL_* variables as test_remote_mysql_integration.
Never point integration tests at a customer server.
"""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from install.test_remote_mysql_integration import MYSQL, HOST, PORT, ROOT_USER, ROOT_PASSWORD, _reachable, REASON
from install.env_generator import build_database_config, create_env_file
from install.test_env_generator import parse_env
import mysqlUtilities


@unittest.skipUnless(_reachable(),REASON)
class ApplicationIdentityIntegrationTests(unittest.TestCase):
    def test_two_panels_settings_migrations_and_isolation(self):
        admin=MYSQL.connect(host=HOST,port=int(PORT),user=ROOT_USER,passwd=ROOT_PASSWORD,connect_timeout=10)
        admin.autocommit(True)
        suffix=uuid.uuid4().hex[:8]
        accounts=[];panels=[]
        params=dict(host=HOST,port=int(PORT),user=ROOT_USER,passwd=ROOT_PASSWORD)
        try:
            with tempfile.TemporaryDirectory() as folder:
                for label in ('a','b'):
                    db=('cpdb_'+suffix+'_a' if label=='a' else 'cpdbX'+suffix+'Xa');user='cpuser_'+suffix+label;password=secrets.token_urlsafe(24)
                    accounts.append((db,user))
                    config=build_database_config(remote=True,host=HOST,port=PORT,root_db='mysql',root_user=ROOT_USER,app_db=db,app_user=user)
                    with patch.object(mysqlUtilities.mysqlUtilities,'_load_admin_connection',return_value=(params,1)),patch.object(mysqlUtilities.mysqlUtilities,'_connect',side_effect=lambda p:MYSQL.connect(**p)):
                        self.assertEqual(mysqlUtilities.mysqlUtilities.createDatabase(db,user,password,'203.0.113.7',require_fresh=True),1)
                    path=Path(folder)/label;path.mkdir()
                    with patch('install.env_generator.get_public_ip',return_value='192.0.2.1'),patch('install.env_generator.get_local_ip',return_value='10.0.0.1'),contextlib.redirect_stdout(io.StringIO()):
                        create_env_file(path,ROOT_PASSWORD,password,database_config=config)
                    values=parse_env(path/'.env');self.assertEqual(values['DB_USER'],user);self.assertEqual(values['DB_NAME'],db)
                    self.assertEqual(values['ROOT_DB_USER'],ROOT_USER)
                    # Execute the shipped DATABASES expression with generated env.
                    tree=ast.parse((Path(__file__).parents[1]/'CyberCP/settings.py').read_text())
                    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATABASES' for t in n.targets))
                    with patch.dict(os.environ,values,clear=True):
                        ns={'os':os};exec(compile(ast.Module(body=[node],type_ignores=[]),'settings','exec'),ns)
                    connection=MYSQL.connect(host=HOST,port=int(PORT),user=user,passwd=password,db=db)
                    with connection.cursor() as cursor:
                        cursor.execute('CREATE TABLE identity_probe (marker VARCHAR(16))')
                        cursor.execute('INSERT INTO identity_probe VALUES (%s)',(label,));connection.commit()
                        cursor.execute('SELECT marker FROM identity_probe');self.assertEqual(cursor.fetchone()[0],label)
                    connection.close()
                    # Real Django schema migration using the generated default connection.
                    # Built-in auth/contenttypes avoid unrelated external app startup hooks.
                    runner="""import json, os
from django.conf import settings
settings.configure(SECRET_KEY='disposable-test',INSTALLED_APPS=['django.contrib.contenttypes','django.contrib.auth'],DATABASES={'default':json.loads(os.environ['CP_TEST_APP_SETTINGS'])},USE_TZ=True)
import django
django.setup()
from django.core.management import call_command
call_command('migrate',interactive=False,verbosity=0)
from django.contrib.auth.models import User
User.objects.create(username=os.environ['CP_TEST_PANEL_LABEL'])
assert list(User.objects.values_list('username',flat=True)) == [os.environ['CP_TEST_PANEL_LABEL']]
"""
                    childenv=os.environ.copy();childenv['CP_TEST_APP_SETTINGS']=json.dumps(ns['DATABASES']['default']);childenv['CP_TEST_PANEL_LABEL']=label
                    result=subprocess.run([sys.executable,'-c',runner],env=childenv,capture_output=True,text=True,timeout=60)
                    self.assertEqual(result.returncode,0,'Django migration failed (credentials omitted)')
                    panels.append((db,user,password,ns['DATABASES']))
                for index,(db,user,password,settings_db) in enumerate(panels):
                    other=panels[1-index][0]
                    conn=MYSQL.connect(host=HOST,port=int(PORT),user=user,passwd=password,db=db)
                    try:
                        with conn.cursor() as cursor:
                            for sql in ('SELECT * FROM `%s`.identity_probe'%other,'INSERT INTO `%s`.identity_probe VALUES (\'cross\')'%other,'DROP DATABASE `%s`'%other):
                                with self.assertRaises(Exception):cursor.execute(sql)
                    finally:conn.close()
                # Collisions refuse before resetting either password or touching data.
                for db,user,_password,_ in panels:
                    with patch.object(mysqlUtilities.mysqlUtilities,'_load_admin_connection',return_value=(params,1)),patch.object(mysqlUtilities.mysqlUtilities,'_connect',side_effect=lambda p:MYSQL.connect(**p)),patch.object(mysqlUtilities.mysqlUtilities,'_report'):
                        self.assertEqual(mysqlUtilities.mysqlUtilities.createDatabase(db,user,'wrong-new-password','203.0.113.7',require_fresh=True),0)
                for db,user,password,_ in panels:
                    conn=MYSQL.connect(host=HOST,port=int(PORT),user=user,passwd=password,db=db)
                    with conn.cursor() as cursor:cursor.execute('SELECT COUNT(*) FROM auth_user');self.assertEqual(cursor.fetchone()[0],1)
                    conn.close()
        finally:
            with admin.cursor() as cursor:
                for db,user in accounts:
                    cursor.execute('DROP DATABASE IF EXISTS `%s`'%db)
                    cursor.execute('SELECT Host FROM mysql.user WHERE User=%s',(user,))
                    for row in cursor.fetchall():cursor.execute('DROP USER %s@%s',(user,row[0]))
            admin.close()

if __name__=='__main__':unittest.main()
