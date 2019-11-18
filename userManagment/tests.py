# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client
from django.urls import reverse
import json
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.models import Administrator

# Create your tests here.


class TestUserManagement(TestCase):

    def setUp(self):
        ## Initiate Client

        self.client = Client()
        self.adminLogin = reverse('adminLogin')
        self.verifyLogin = reverse('verifyLogin')

        ## Create Login User

        response = self.client.get(self.adminLogin)

        #

        self.assertTemplateUsed(response, 'loginSystem/login.html')
        self.submitUserCreation = reverse('submitUserCreation')
        self.submitUserDeletion = reverse('submitUserDeletion')
        self.saveModifications = reverse('saveModifications')
        self.fetchUserDetails = reverse('fetchUserDetails')
        self.saveResellerChanges = reverse('saveResellerChanges')

        ## Verify login

        data_ret = {'username': 'admin', 'password': '1234567'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.verifyLogin, json_data, content_type="application/json")
        json_data = json.loads(response.content)
        self.assertEqual(json_data['loginStatus'], 1)

    def test_submitUserCreation(self):

        ## Login

        data_ret = {'firstName': 'Usman', 'lastName': 'Nasir', 'email': 'usman@cyberpersons.com', 'userName': 'usman',
                    'password': '1234567', 'websitesLimit': 50, 'selectedACL':'user', 'securityLevel': 'HIGH'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.submitUserCreation, json_data, content_type="application/json")
        json_data = json.loads(response.content)


        self.assertEqual(json_data['status'], 1)
        self.assertEqual(json_data['createStatus'], 1)

        self.assertEqual(Administrator.objects.filter(userName='usman').count(), 1)

    def test_submitUserDeletion(self):
        self.test_submitUserCreation()

        data_ret = {'accountUsername': 'usman'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.submitUserDeletion, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)
        self.assertEqual(json_data['deleteStatus'], 1)

        self.assertEqual(Administrator.objects.filter(userName='usman').count(), 0)

    def test_saveModifications(self):
        self.test_submitUserCreation()

        data_ret = {'accountUsername': 'usman','firstName': 'Rehan', 'lastName': 'Nasir', 'email': 'usman@cyberpersons.com',
                    'securityLevel': "LOW", 'password': '1234567'}
        json_data = json.dumps(data_ret)


        ## Modification
        response = self.client.post(self.saveModifications, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)
        self.assertEqual(json_data['saveStatus'], 1)

        ## Check Modification
        # response = self.client.post(self.fetchUserDetails, json_data, content_type="application/json")
        # logging.writeToFile(response.content)
        # json_data = json.loads(response.content)

        self.assertEqual(Administrator.objects.get(userName='usman').firstName, 'Rehan')
        self.assertEqual(Administrator.objects.get(userName='usman').lastName, 'Nasir')
        self.assertEqual(Administrator.objects.get(userName='usman').securityLevel, 1)

    def test_saveResellerChangess(self):
        self.test_submitUserCreation()

        data_ret = {'newOwner': 'admin', 'userToBeModified':'usman', 'websitesLimit': 100}
        json_data = json.dumps(data_ret)


        ## Modification
        response = self.client.post(self.saveResellerChanges, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)

        ## Check Modification
        # response = self.client.post(self.fetchUserDetails, json_data, content_type="application/json")
        # logging.writeToFile(response.content)
        # json_data = json.loads(response.content)

        self.assertEqual(Administrator.objects.get(userName='usman').initWebsitesLimit, 100)




