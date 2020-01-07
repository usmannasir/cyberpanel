# -*- coding: utf-8 -*-
from django.test import TestCase
import json
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import requests
import time
from plogical.processUtilities import ProcessUtilities
import urllib3
urllib3.disable_warnings()
# Create your tests here.


class TestWebsiteManagement(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/%s' % (endPoint)
        result = TestWebsiteManagement.httpClient.post(path, data=json_data, verify=False)
        return json.loads(result.text)

    def MakeRequestRaw(self, path):
        result = requests.get(path)
        return str(result.text)

    def setUp(self):
        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        response = self.MakeRequest('verifyLogin', data_ret)
        self.assertEqual(response['loginStatus'], 1)

    def test_submitWebsiteCreation(self):

        ## Login

        data_ret = {'domainName': 'hello.cyberpanel.xyz', 'adminEmail': 'usman@cyberpersons.com' , 'phpSelection': 'PHP 7.1',
                    'package': 'Default', 'websiteOwner': 'admin', 'ssl': 0, 'dkimCheck': 0, 'openBasedir': 0}
        response = self.MakeRequest('websites/submitWebsiteCreation', data_ret)

        time.sleep(10)

        self.assertEqual(response['status'], 1)

        exists = 0

        if self.MakeRequestRaw('http://hello.cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_submitWebsiteDeletion(self):

        ## Login

        data_ret = {'websiteName': 'hello.cyberpanel.xyz'}

        response = self.MakeRequest('websites/submitWebsiteDeletion', data_ret)
        time.sleep(10)

        self.assertEqual(response['status'], 1)

    def test_submitWebsiteModify(self):

        data_ret = {'domainName': 'hey.cyberpanel.xyz', 'adminEmail': 'usman@cyberpersons.com',
                    'phpSelection': 'PHP 7.1',
                    'package': 'Default', 'websiteOwner': 'admin', 'ssl': 0, 'dkimCheck': 0, 'openBasedir': 0}
        self.MakeRequest('websites/submitWebsiteCreation', data_ret)

        time.sleep(10)

        ##

        data_ret = {'domain': 'hey.cyberpanel.xyz', 'email': 'usman@cyberpersons.com' , 'phpVersion': 'PHP 7.3',
                    'packForWeb': 'Default', 'admin': 'admin'}

        response = self.MakeRequest('websites/saveWebsiteChanges', data_ret)

        time.sleep(5)

        self.assertEqual(response['status'], 1)

        phpInfoPath = '/home/hey.cyberpanel.xyz/public_html/info.php'
        content = """<?php

phpinfo();

?>
"""
        writeToFile = open(phpInfoPath, 'w')
        writeToFile.write(content)
        writeToFile.close()

        exists = 0

        if self.MakeRequestRaw('http://hey.cyberpanel.xyz/info.php').find('lsphp73') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_submitWebsiteStatus(self):

        data_ret = {'domainName': 'suspend.cyberpanel.xyz', 'adminEmail': 'usman@cyberpersons.com',
                    'phpSelection': 'PHP 7.1',
                    'package': 'Default', 'websiteOwner': 'admin', 'ssl': 0, 'dkimCheck': 0, 'openBasedir': 0}
        self.MakeRequest('websites/submitWebsiteCreation', data_ret)

        ## Suspend  check
        data_ret = {'websiteName': 'suspend.cyberpanel.xyz', 'state': 'Suspend'}

        response = self.MakeRequest('websites/submitWebsiteStatus', data_ret)

        time.sleep(5)

        self.assertEqual(response['websiteStatus'], 1)

        exists = 0

        if self.MakeRequestRaw('http://suspend.cyberpanel.xyz').find('404') > -1 or self.MakeRequestRaw('http://suspend.cyberpanel.xyz').find('Access to this resource on the server is denied!') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        suspend = 0
        import os
        if os.path.exists('/usr/local/lsws/conf/vhosts/suspend.cyberpanel.xyz-suspended'):
            suspend = 1

        self.assertEqual(suspend, 1)

        ## Unsuspend  check

        data_ret = {'websiteName': 'suspend.cyberpanel.xyz', 'state': 'Unsuspend'}

        response = self.MakeRequest('websites/submitWebsiteStatus', data_ret)

        time.sleep(5)

        self.assertEqual(response['websiteStatus'], 1)

        exists = 0

        if self.MakeRequestRaw('http://suspend.cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        suspend = 0
        import os
        if os.path.exists('/usr/local/lsws/conf/vhosts/suspend.cyberpanel.xyz'):
            suspend = 1

        self.assertEqual(suspend, 1)

    def test_installWordpress(self):

        command = 'rm -rf /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'mkdir /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'chown cyberpa:cyberpa /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        ## Suspend  check
        data_ret = {'domain': 'cyberpanel.xyz', 'home': '1', 'blogTitle': 'Unit Test', 'adminUser': 'cyberpanel',
                    'passwordByPass': 'helloworld', 'adminEmail': 'usman@cyberpersons.com'}

        response = self.MakeRequest('websites/installWordpress', data_ret)

        time.sleep(2)

        self.assertEqual(response['status'], 1)
        tempStatusPath = response['tempStatusPath']

        ## Wait for install to complete

        data_ret = {'statusFile': tempStatusPath, 'domainName': 'cyberpanel.xyz'}

        while True:
            response = self.MakeRequest('websites/installWordpressStatus', data_ret)
            if response['abort'] == 1:
                if response['installStatus']:
                    break
                else:
                    logging.writeToFile(response['error_message'])
                    break


        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('Unit Test') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_installJoomla(self):

        command = 'rm -rf /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'mkdir /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'chown cyberpa:cyberpa /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        ## Suspend  check
        data_ret = {'domain': 'cyberpanel.xyz', 'home': '1', 'sitename': 'Unit Test Joomla', 'username': 'cyberpanel',
                    'passwordByPass': 'helloworld', 'prefix': 'db_'}

        response = self.MakeRequest('websites/installJoomla', data_ret)
        time.sleep(2)

        self.assertEqual(response['status'], 1)
        tempStatusPath = response['tempStatusPath']

        ## Wait for install to complete

        data_ret = {'statusFile': tempStatusPath, 'domainName': 'cyberpanel.xyz'}

        while True:
            response = self.MakeRequest('websites/installWordpressStatus', data_ret)
            time.sleep(1)
            if response['abort'] == 1:
                if response['installStatus'] == 1:
                    break
                else:
                    logging.writeToFile(response['error_message'])
                    break


        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('Unit Test Joomla') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_prestaShopInstall(self):

        command = 'rm -rf /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'mkdir /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'chown cyberpa:cyberpa /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        ## Suspend  check
        data_ret = {'domain': 'cyberpanel.xyz', 'home': '1', 'shopName': 'Unit Test PrestaShop', 'firstName': 'Usman', 'lastName': 'Nasir',
                    'passwordByPass': 'helloworld', 'databasePrefix': 'db_', 'email': 'usman@cyberpersons.com'}

        response = self.MakeRequest('websites/prestaShopInstall', data_ret)
        time.sleep(2)

        self.assertEqual(response['status'], 1)
        tempStatusPath = response['tempStatusPath']

        ## Wait for install to complete

        data_ret = {'statusFile': tempStatusPath, 'domainName': 'cyberpanel.xyz'}

        while True:
            response = self.MakeRequest('websites/installWordpressStatus', data_ret)
            time.sleep(1)
            if response['abort'] == 1:
                if response['installStatus'] == 1:
                    break
                else:
                    logging.writeToFile(response['error_message'])
                    break


        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('Unit Test PrestaShop') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_magentoInstall(self):

        command = 'rm -rf /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'mkdir /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'chown cyberpa:cyberpa /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        ## Suspend  check
        data_ret = {'domain': 'cyberpanel.xyz', 'home': '1','firstName': 'Usman', 'lastName': 'Nasir',
                    'passwordByPass': 'helloworld1234', 'sampleData': False, 'email': 'usman@cyberpersons.com', 'username': 'usman'}

        response = self.MakeRequest('websites/magentoInstall', data_ret)
        logging.writeToFile('ps: ' + str(response))
        time.sleep(2)

        self.assertEqual(response['status'], 1)
        tempStatusPath = response['tempStatusPath']

        ## Wait for install to complete

        data_ret = {'statusFile': tempStatusPath, 'domainName': 'cyberpanel.xyz'}

        while True:
            response = self.MakeRequest('websites/installWordpressStatus', data_ret)
            time.sleep(1)
            if response['abort'] == 1:
                if response['installStatus'] == 1:
                    break
                else:
                    logging.writeToFile(response['error_message'])
                    break


        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('Magento') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_checkConfigFile(self):
        ##

        data_ret = {'virtualHost': 'cyberpanel.xyz'}

        response = self.MakeRequest('websites/getDataFromConfigFile', data_ret)

        self.assertEqual(response['status'], 1)

        exists = 0

        if response['configData'].find('phpIniOverride') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        ## Inserting something in config file

        data_ret = {'virtualHost': 'cyberpanel.xyz', 'configData': response['configData'] + '\nhello world'}

        response = self.MakeRequest('websites/saveConfigsToFile', data_ret)

        self.assertEqual(response['configstatus'], 1)

        ## Check again

        data_ret = {'virtualHost': 'cyberpanel.xyz'}

        response = self.MakeRequest('websites/getDataFromConfigFile', data_ret)

        self.assertEqual(response['status'], 1)

        exists = 0

        if response['configData'].find('hello world') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        ## Inserting again

        ## Inserting something in config file

        data_ret = {'virtualHost': 'cyberpanel.xyz', 'configData': response['configData']}

        response = self.MakeRequest('websites/saveConfigsToFile', data_ret)

        self.assertEqual(response['configstatus'], 1)

    def test_checkRewriteFile(self):

        ## Inserting something in rewrite file

        data_ret = {'virtualHost': 'cyberpanel.xyz', 'rewriteRules': 'hello world'}

        response = self.MakeRequest('websites/saveRewriteRules', data_ret)

        self.assertEqual(response['rewriteStatus'], 1)

        ## Check again

        data_ret = {'virtualHost': 'cyberpanel.xyz'}

        response = self.MakeRequest('websites/getRewriteRules', data_ret)

        self.assertEqual(response['rewriteStatus'], 1)

        exists = 0

        if response['rewriteRules'].find('hello world') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_saveSSL(self):

        ## Inserting something in rewrite file

        data_ret = {'virtualHost': 'hey.cyberpanel.xyz', 'key': 'hello world', 'cert': 'hello world'}

        response = self.MakeRequest('websites/saveSSL', data_ret)

        self.assertEqual(response['sslStatus'], 1)

        ## Check again

        certPath = '/etc/letsencrypt/live/hey.cyberpanel.xyz/fullchain.pem'
        keyPath = '/etc/letsencrypt/live/hey.cyberpanel.xyz/privkey.pem'

        self.assertGreater(open(certPath, 'r').read().find('hello world'), -1)
        self.assertGreater(open(keyPath, 'r').read().find('hello world'), -1)

    def test_changePHP(self):
        data_ret = {'childDomain': 'hey.cyberpanel.xyz', 'phpSelection': 'PHP 7.0',}

        response = self.MakeRequest('websites/changePHP', data_ret)

        self.assertEqual(response['status'], 1)

        phpInfoPath = '/home/hey.cyberpanel.xyz/public_html/info.php'
        content = "<?php phpinfo(); ?>"
        writeToFile = open(phpInfoPath, 'w')
        writeToFile.write(content)
        writeToFile.close()

        time.sleep(2)

        exists = 0

        if self.MakeRequestRaw('http://hey.cyberpanel.xyz/info.php').find('lsphp70') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_changeOpenBasedir(self):

        ## Check enable

        data_ret = {'domainName': 'hey.cyberpanel.xyz', 'openBasedirValue': 'Enable'}
        response = self.MakeRequest('websites/changeOpenBasedir', data_ret)

        self.assertEqual(response['status'], 1)

        time.sleep(3)

        completePathToConfigFile = '/usr/local/lsws/conf/vhosts/%s/vhost.conf' % ('hey.cyberpanel.xyz')

        exists = 0

        if open(completePathToConfigFile, 'r').read().find('open_basedir') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        ## Check disable

        data_ret = {'domainName': 'hey.cyberpanel.xyz', 'openBasedirValue': 'Disable'}
        response = self.MakeRequest('websites/changeOpenBasedir', data_ret)

        self.assertEqual(response['status'], 1)

        time.sleep(3)

        completePathToConfigFile = '/usr/local/lsws/conf/vhosts/%s/vhost.conf' % ('hey.cyberpanel.xyz')

        exists = 0

        if open(completePathToConfigFile, 'r').read().find('open_basedir') > -1:
            exists = 1

        self.assertEqual(exists, 0)

    def test_submitDomainCreation(self):

        ## Check creation

        data_ret = {'masterDomain': 'cyberpanel.xyz', 'domainName': 'child.cyberpanel.xyz' , 'phpSelection': 'PHP 7.1', 'ssl': 0, 'dkimCheck': 0, 'openBasedir': 0, 'path': ''}
        response = self.MakeRequest('websites/submitDomainCreation', data_ret)

        time.sleep(10)

        self.assertEqual(response['status'], 1)

        exists = 0

        if self.MakeRequestRaw('http://child.cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        ## Check deletion

        data_ret = {'websiteName': 'child.cyberpanel.xyz'}
        response = self.MakeRequest('websites/submitDomainDeletion', data_ret)

        time.sleep(10)

        self.assertEqual(response['status'], 1)

        exists = 0

        if self.MakeRequestRaw('http://child.cyberpanel.xyz').find('404') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_addNewCron(self):

        ## Check cron creation

        data_ret = {'domain': 'cyberpanel.xyz', 'cronCommand': 'touch /home/cyberpanel.xyz/cron.txt' , 'hour': '*', 'minute': '*', 'month': '*', 'monthday': '*', 'weekday': '*'}
        response = self.MakeRequest('websites/addNewCron', data_ret)

        time.sleep(65)

        self.assertEqual(response['addNewCron'], 1)

        import os
        self.assertEqual(os.path.exists('/home/cyberpanel.xyz/cron.txt'), True)

        ##

        data_ret = {'domain': 'cyberpanel.xyz', 'line': 1}
        response = self.MakeRequest('websites/remCronbyLine', data_ret)

        self.assertEqual(response['remCronbyLine'], 1)

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
            cronPath = "/var/spool/cron/cyberpa"
        else:
            cronPath = "/var/spool/cron/crontabs/cyberpa"

        exists = 0

        if open(cronPath, 'r').read().find('cron.txt') > -1:
            exists = 1

        self.assertEqual(exists, 0)



