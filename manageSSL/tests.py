# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
import json
import requests
import urllib3
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities

urllib3.disable_warnings()


# Create your tests here.


class TestManageSSL(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/%s' % (endPoint)
        result = TestManageSSL.httpClient.post(path, data=json_data, verify=False)
        return json.loads(result.text)

    def MakeRequestRaw(self, path):
        result = requests.get(path)
        return str(result.text)

    def setupConnection(self):
        try:
            import MySQLdb as mysql
            import MySQLdb.cursors as cursors
            conn = mysql.connect(user='admin_hello', passwd='helloworld', cursorclass=cursors.SSCursor)
            cursor = conn.cursor()
            return conn, cursor
        except:
            return 0, 0

    def setUp(self):
        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        response = self.MakeRequest('verifyLogin', data_ret)
        self.assertEqual(response['loginStatus'], 1)

    def test_issueSSL(self):
        ## Issue SSL

        data_ret = {'virtualHost': 'cyberpanel.xyz'}

        response = self.MakeRequest('manageSSL/issueSSL', data_ret)

        self.assertEqual(response['status'], 1)

        ## Verify SSL

        command = 'rm -rf /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'mkdir /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        command = 'chown cyberpa:cyberpa /home/%s/public_html/' % ('cyberpanel.xyz')
        ProcessUtilities.normalExecutioner(command)

        path = '/home/%s/public_html/index.html' % ('cyberpanel.xyz')

        writeToFile = open(path, 'w')
        writeToFile.write('CyberPanel')
        writeToFile.close()

        exists = 0
        if self.MakeRequestRaw('https://cyberpanel.xyz').find('CyberPanel') > -1:
            exists = 1

        self.assertEqual(exists, 1)




