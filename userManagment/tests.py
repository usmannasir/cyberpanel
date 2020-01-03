# -*- coding: utf-8 -*-


from django.test import TestCase, Client
from django.urls import reverse
import json
from loginSystem.models import Administrator, ACL
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
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
        self.createACLFunc = reverse('createACLFunc')
        self.deleteACLFunc = reverse('deleteACLFunc')
        self.submitACLModifications = reverse('submitACLModifications')
        self.saveChangesAPIAccess = reverse('saveChangesAPIAccess')

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

    def test_createACLFunc(self):

        data_ret = {'aclName': 'hello', 'makeAdmin':1,
                    'createNewUser': 1,
                    'versionManagement': 1,
                    'listUsers': 1,
                    'resellerCenter': 1,
                    'deleteUser': 1,
                    'changeUserACL': 1,
                    'createWebsite': 1,
                    'modifyWebsite': 1,
                    'suspendWebsite': 1,
                    'deleteWebsite': 1,
                    'createPackage': 1,
                    'listPackages': 1,
                    'deletePackage': 1,
                    'modifyPackage': 1,
                    'createDatabase': 1,
                    'deleteDatabase': 1,
                    'listDatabases': 1,
                    'createNameServer': 1,
                    'createDNSZone': 1,
                    'deleteZone': 1,
                    'addDeleteRecords': 1,
                    'createEmail': 1,
                    'listEmails': 1,
                    'deleteEmail': 1,
                    'emailForwarding': 1,
                    'changeEmailPassword': 1,
                    'dkimManager': 1,
                    'createFTPAccount': 1,
                    'deleteFTPAccount': 1,
                    'listFTPAccounts': 1,
                    'createBackup': 1,
                    'restoreBackup': 1,
                    'addDeleteDestinations': 1,
                    'scheDuleBackups': 1,
                    'remoteBackups': 1,
                    'manageSSL': 1,
                    'hostnameSSL': 1,
                    'mailServerSSL': 1}
        json_data = json.dumps(data_ret)


        ## Modification
        response = self.client.post(self.createACLFunc, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)

        self.assertEqual(ACL.objects.filter(name='hello').count(), 1)

    def test_deleteACLFunc(self):
        self.test_createACLFunc()

        data_ret = {'aclToBeDeleted': 'hello'}
        json_data = json.dumps(data_ret)

        response = self.client.post(self.deleteACLFunc, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)

        self.assertEqual(ACL.objects.filter(name='hello').count(), 0)

    def test_submitACLModifications(self):
        self.test_createACLFunc()
        data_ret = {'aclToModify': 'hello',
                    'adminStatus':1,
                    'createNewUser': 1,
                    'versionManagement': 1,
                    'listUsers': 1,
                    'resellerCenter': 1,
                    'deleteUser': 1,
                    'changeUserACL': 1,
                    'createWebsite': 1,
                    'modifyWebsite': 1,
                    'suspendWebsite': 1,
                    'deleteWebsite': 1,
                    'createPackage': 1,
                    'listPackages': 1,
                    'deletePackage': 1,
                    'modifyPackage': 1,
                    'createDatabase': 1,
                    'deleteDatabase': 1,
                    'listDatabases': 1,
                    'createNameServer': 1,
                    'createDNSZone': 1,
                    'deleteZone': 1,
                    'addDeleteRecords': 1,
                    'createEmail': 1,
                    'listEmails': 1,
                    'deleteEmail': 1,
                    'emailForwarding': 1,
                    'changeEmailPassword': 1,
                    'dkimManager': 1,
                    'createFTPAccount': 1,
                    'deleteFTPAccount': 1,
                    'listFTPAccounts': 1,
                    'createBackup': 1,
                    'restoreBackup': 1,
                    'addDeleteDestinations': 1,
                    'scheDuleBackups': 1,
                    'remoteBackups': 1,
                    'manageSSL': 1,
                    'hostnameSSL': 1,
                    'mailServerSSL': 0}
        json_data = json.dumps(data_ret)


        ## Modification
        response = self.client.post(self.submitACLModifications, json_data, content_type="application/json")
        logging.writeToFile(response.content)
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)

        self.assertEqual(ACL.objects.get(name='hello').mailServerSSL, 0)
        self.assertEqual(ACL.objects.get(name='hello').hostnameSSL, 1)

    def test_saveChangesAPIAccess(self):
        self.test_submitUserCreation()

        data_ret = {'accountUsername': 'usman', 'access': 'Enable'}
        json_data = json.dumps(data_ret)

        ## Modification
        response = self.client.post(self.saveChangesAPIAccess, json_data, content_type="application/json")
        json_data = json.loads(response.content)

        self.assertEqual(json_data['status'], 1)

        ## Check Modification
        # response = self.client.post(self.fetchUserDetails, json_data, content_type="application/json")
        # logging.writeToFile(response.content)
        # json_data = json.loads(response.content)

        self.assertEqual(Administrator.objects.get(userName='usman').api, 1)




