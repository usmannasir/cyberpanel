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


class TestFTP(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/%s' % (endPoint)
        result = TestFTP.httpClient.post(path, data=json_data, verify=False)
        return json.loads(result.text)

    def MakeRequestRaw(self, path):
        result = requests.get(path)
        return str(result.text)

    def setUp(self):
        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        response = self.MakeRequest('verifyLogin', data_ret)
        self.assertEqual(response['loginStatus'], 1)

    def test_submitFTPCreation(self):

        ## Create FTP

        data_ret = {'ftpDomain': 'cyberpanel.xyz', 'ftpUserName':'hello', 'passwordByPass':'helloworld'}

        response = self.MakeRequest('ftp/submitFTPCreation', data_ret)

        self.assertEqual(response['status'], 1)

        ## Test ftp

        import ftplib
        try:
            ok = 1
            ftp = ftplib.FTP('cyberpanel.xyz')
            ftp.login(user='admin_hello', passwd='helloworld')
            ftp.mkd('unittest')
        except:
            ok = 0

        import os
        self.assertEqual(ok,1)
        self.assertEqual(os.path.exists('/home/cyberpanel.xyz/unittest'), True)

        # Delete FTP

        data_ret = {'ftpUsername': 'admin_hello'}

        response = self.MakeRequest('ftp/submitFTPDelete', data_ret)

        self.assertEqual(response['status'], 1)

        try:
            ok = 1
            ftp = ftplib.FTP('cyberpanel.xyz')
            ftp.login(user='admin_hello', passwd='helloworld')
            ftp.mkd('unittest')
        except:
            ok = 0

        self.assertEqual(ok, 0)

