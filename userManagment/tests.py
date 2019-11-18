# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

        self.submitUserCreation = reverse('submitUserCreation')

        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.verifyLogin, json_data, content_type="application/json")
        logging.writeToFile(response.content)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['loginStatus'], 1)

    def test_submitUserCreation(self):

        ## Login

        data_ret = {'firstName': 'Usman', 'lastName': 'Nasir', 'email': 'usman@cyberpersons.com', 'userName': 'usman',
                    'password': '1234567', 'websitesLimit': 50, 'selectedACL':'user', 'securityLevel': 'HIGH'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.submitUserCreation, json_data, content_type="application/json")
        logging.writeToFile(response.content)
        json_data = json.loads(response.content)


        self.assertEqual(json_data['status'], 1)
        self.assertEqual(json_data['createStatus'], 1)

        self.assertEqual(Administrator.objects.filter(userName='usman').count(), 1)



