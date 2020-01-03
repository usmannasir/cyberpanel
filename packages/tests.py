# -*- coding: utf-8 -*-


from django.test import TestCase
import json
import requests
import urllib3
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
urllib3.disable_warnings()
# Create your tests here.


class TestPackages(TestCase):
    httpClient = requests.Session()

    def MakeRequest(self, endPoint, data):
        json_data = json.dumps(data)
        path = 'https://cyberpanel.xyz:8090/%s' % (endPoint)
        result = TestPackages.httpClient.post(path, data=json_data, verify=False)
        return json.loads(result.text)

    def MakeRequestRaw(self, path):
        result = requests.get(path)
        return str(result.text)

    def setUp(self):
        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        response = self.MakeRequest('verifyLogin', data_ret)
        self.assertEqual(response['loginStatus'], 1)

    def test_CheckPackage(self):

        ## Create Package

        data_ret = {'packageName': 'HelloWorld', 'diskSpace': 50 , 'bandwidth': 50,
                    'dataBases': 50, 'ftpAccounts': 50, 'emails': 50, 'allowedDomains': 50, 'allowFullDomain': 1}

        response = self.MakeRequest('packages/submitPackage', data_ret)
        logging.writeToFile(str(response))

        self.assertEqual(response['status'], 1)

        ## Modify Package

        data_ret = {'packageName': 'admin_HelloWorld', 'diskSpace': 500, 'bandwidth': 50,
                    'dataBases': 500, 'ftpAccounts': 50, 'emails': 50, 'allowedDomains': 50, 'allowFullDomain': 1}

        response = self.MakeRequest('packages/saveChanges', data_ret)
        logging.writeToFile(str(response))

        self.assertEqual(response['status'], 1)

        ## Modify Confirm

        data_ret = {'packageName': 'admin_HelloWorld'}

        response = self.MakeRequest('packages/submitModify', data_ret)
        logging.writeToFile(str(response))

        self.assertEqual(response['modifyStatus'], 1)
        self.assertEqual(response['dataBases'], 500)
        self.assertEqual(response['diskSpace'], 500)

        ## Delete Package

        data_ret = {'packageName': 'admin_HelloWorld'}

        response = self.MakeRequest('packages/submitDelete', data_ret)
        logging.writeToFile(str(response))

        self.assertEqual(response['status'], 1)


