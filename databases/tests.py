# -*- coding: utf-8 -*-


from django.test import TestCase
import json
import requests
import urllib3
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

urllib3.disable_warnings()


# Create your tests here.


class TestDatabases(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/%s' % (endPoint)
        result = TestDatabases.httpClient.post(path, data=json_data, verify=False)
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

    def test_submitDBCreation(self):
        ## Create DB

        data_ret = {'databaseWebsite': 'cyberpanel.xyz', 'dbName': 'hello', 'dbUsername': 'hello',
                    'dbPassword': 'helloworld', 'webUserName': 'admin'}

        response = self.MakeRequest('dataBases/submitDBCreation', data_ret)

        self.assertEqual(response['status'], 1)

        ## Check connection to database

        connection, cursor = self.setupConnection()

        self.assertNotEqual(connection, 0)

        ## Delete db

        data_ret = {'dbName': 'admin_hello'}
        response = self.MakeRequest('dataBases/submitDatabaseDeletion', data_ret)
        self.assertEqual(response['status'], 1)

        ## Check connection to database

        connection, cursor = self.setupConnection()

        self.assertEqual(connection, 0)


