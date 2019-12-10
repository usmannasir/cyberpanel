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


class TestAPI(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/api/%s' % (endPoint)
        result = TestAPI.httpClient.post(path, data=json_data, verify=False)
        return json.loads(result.text)

    def MakeRequestRaw(self, path):
        result = requests.get(path)
        return str(result.text)

    def test_verifyConn(self):
        ## Verify login

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567'}
        response = self.MakeRequest('verifyConn', data_ret)
        self.assertEqual(response['verifyConn'], 1)

    def test_submitWebsiteCreation(self):

        ## Login

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'domainName': 'api.cyberpanel.xyz', 'ownerEmail': 'usman@cyberpersons.com' , 'phpSelection': 'PHP 7.1',
                    'packageName': 'Default', 'websiteOwner': 'apiuser','ownerPassword':'helloworld'}

        response = self.MakeRequest('createWebsite', data_ret)

        time.sleep(10)

        self.assertEqual(response['status'], 1)

        exists = 0

        if self.MakeRequestRaw('http://api.cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        ## Check deletion

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'domainName': 'api.cyberpanel.xyz'}

        response = self.MakeRequest('deleteWebsite', data_ret)

        time.sleep(10)

        self.assertEqual(response['status'], 1)

        exists = 0

        if self.MakeRequestRaw('http://api.cyberpanel.xyz').find('404') > -1:
            exists = 1

        self.assertEqual(exists, 1)

    def test_getUserInfo(self):

        ## Login

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'username': 'admin'}
        response = self.MakeRequest('getUserInfo', data_ret)

        self.assertEqual(response['status'], 1)

    def test_changeUserPassAPI(self):

        ## Login

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'websiteOwner': 'admin', 'ownerPassword': '1234567'}
        response = self.MakeRequest('changeUserPassAPI', data_ret)

        self.assertEqual(response['changeStatus'], 1)

    def test_changePackageAPI(self):

        ## Login

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'websiteName': 'cyberpanel.xyz', 'packageName': 'Default'}
        response = self.MakeRequest('changePackageAPI', data_ret)

        self.assertEqual(response['changePackage'], 1)

    def test_submitWebsiteStatus(self):

        ## Suspend  check
        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'websiteName': 'cyberpanel.xyz', 'state': 'Suspend'}

        response = self.MakeRequest('submitWebsiteStatus', data_ret)

        time.sleep(5)

        self.assertEqual(response['websiteStatus'], 1)

        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('404') > -1 or self.MakeRequestRaw(
                'http://cyberpanel.xyz').find('Access to this resource on the server is denied!') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        suspend = 0
        import os
        if os.path.exists('/usr/local/lsws/conf/vhosts/cyberpanel.xyz-suspended'):
            suspend = 1

        self.assertEqual(suspend, 1)

        ## Unsuspend  check

        data_ret = {'adminUser': 'admin', 'adminPass': '1234567', 'websiteName': 'cyberpanel.xyz', 'state': 'Unsuspend'}

        response = self.MakeRequest('submitWebsiteStatus', data_ret)

        time.sleep(5)

        self.assertEqual(response['websiteStatus'], 1)

        exists = 0

        if self.MakeRequestRaw('http://cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)

        suspend = 0
        import os
        if os.path.exists('/usr/local/lsws/conf/vhosts/cyberpanel.xyz'):
            suspend = 1

        self.assertEqual(suspend, 1)

    def test_submitUserCreation(self):

        ## Login

        data_ret = {
            "adminUser": "admin",
            "adminPass": "1234567",
            "firstName": "Usman",
            "lastName": "Nasir",
            "email": "usman@cyberpersons.com",
            "userName": "usman",
            "password": "helloworld123",
            "websitesLimit": 50,
            "selectedACL": "user",
            "securityLevel": "HIGH",
        }
        response = self.MakeRequest('submitUserCreation', data_ret)

        self.assertEqual(response['status'], 1)


