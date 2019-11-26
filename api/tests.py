# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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