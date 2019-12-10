# -*- coding: utf-8 -*-


from django.test import TestCase, Client
from django.urls import reverse
import json
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.models import Administrator

# Create your tests here.


class TestLogin(TestCase):

    def setUp(self):
        ## Initiate Client

        self.client = Client()
        self.adminLogin = reverse('adminLogin')
        self.verifyLogin = reverse('verifyLogin')

        ## Create Login User

        response = self.client.get(self.adminLogin)
        self.assertTemplateUsed(response, 'loginSystem/login.html')

    def test_verify_login(self):

        ## Login

        data_ret = {'username': 'admin', 'password': '1234567'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.verifyLogin, json_data, content_type="application/json")
        logging.writeToFile(response.content)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['loginStatus'], 1)


        ## Verify

        response = self.client.get(self.adminLogin)
        self.assertTemplateUsed(response, 'baseTemplate/homePage.html')
        ##logging.writeToFile(result.content)
        self.assertEqual(response.status_code, 200)

