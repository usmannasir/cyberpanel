"""Execute the actual reset writers in a relocated disposable filesystem."""
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
from install.test_application_identity import ServiceWriterTests, load_method, ROOT


class ResetWriterTests(ServiceWriterTests):
    def prepare_reset(self):
        installation=self.root/'usr/local/CyberCP/install';installation.mkdir(parents=True)
        for folder in ('email-configs-one','pure-ftpd-one','dns-one'):
            shutil.copytree(ROOT/'install'/folder,installation/folder)
        self.ns['ProcessUtilities']=SimpleNamespace(centos=0,cent8=2,ubuntu=1,ubuntu20=3,
            decideDistro=lambda:1,executioner=Mock(return_value=1),ubuntu22Check=False)
        from plogical.ftpConfiguration import write_chroot_everyone
        self.ns['write_chroot_everyone']=write_chroot_everyone
        self.ns['ACLManager']=SimpleNamespace(fetchIP=lambda:'192.0.2.1')
        self.ns['logging'].CyberCPLogFileWriter=SimpleNamespace(writeToFile=Mock(),statusWriter=Mock())
        self.obj.extraArgs={'tempStatusPath':str(self.root/'status')}
        self.settings=SimpleNamespace(DATABASES={'default':{'NAME':'panel_a','USER':'panel_a_user'}})
        return installation

    def test_reset_mail_preserves_application_identity(self):
        installation=self.prepare_reset()
        method=load_method('plogical/mailUtilities.py','MailServerManagerUtils','setup_email_Passwords',self.ns,self.root)
        with patch.dict(sys.modules,{'CyberCP':SimpleNamespace(settings=self.settings)}):
            self.assertEqual(method(self.obj,'fixtureSecret'),1)
        for path in (installation/'email-configs-one').glob('mysql-virtual*.cf'):
            self.assertIn('user = panel_a_user',path.read_text());self.assertIn('dbname = panel_a',path.read_text())
        content=(installation/'email-configs-one/dovecot-sql.conf.ext').read_text()
        self.assertIn('user=panel_a_user',content);self.assertIn('dbname=panel_a',content)

    def test_reset_dns_preserves_application_identity(self):
        self.prepare_reset()
        method=load_method('dns/dnsManager.py','DNSManager','installPowerDNSConfigurations',self.ns,self.root)
        with patch.dict(sys.modules,{'CyberCP':SimpleNamespace(settings=self.settings)}):
            self.assertEqual(method(self.obj,'fixtureSecret'),1)
        content=(self.root/'etc/powerdns/pdns.conf').read_text()
        self.assertIn('gmysql-user=panel_a_user',content);self.assertIn('gmysql-dbname=panel_a',content)

    def test_reset_ftp_preserves_application_identity(self):
        self.prepare_reset()
        method=load_method('ftp/ftpManager.py','FTPManager','installPureFTPDConfigurations',self.ns,self.root)
        with patch.dict(sys.modules,{'CyberCP':SimpleNamespace(settings=self.settings)}):
            self.assertNotEqual(method(self.obj,'fixtureSecret'),0)
        content=(self.root/'etc/pure-ftpd/pureftpd-mysql.conf').read_text()
        self.assertIn('MYSQLUser panel_a_user',content);self.assertIn('MYSQLDatabase panel_a',content)
        self.assertEqual(content,(self.root/'etc/pure-ftpd/db/mysql.conf').read_text())

if __name__=='__main__':unittest.main()
