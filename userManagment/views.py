# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator, ACL
import json
from plogical import hashPassword
from plogical import CyberCPLogFileWriter as logging
from plogical.acl import ACLManager


# Create your views here.

def loadUserHome(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)
            return render(request, 'userManagment/index.html', {"type": admin.type})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def viewProfile(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        AdminData = {}

        AdminData['userName'] = admin.userName
        AdminData['firstName'] = admin.firstName
        AdminData['lastName'] = admin.lastName
        AdminData['websitesLimit'] = admin.initWebsitesLimit
        AdminData['email'] = admin.email
        AdminData['accountACL'] = admin.acl.name

        return render(request, 'userManagment/userProfile.html', AdminData)
    except KeyError:
        return redirect(loadLoginPage)


def createUser(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            aclNames = ACLManager.unFileteredACLs()
            return render(request, 'userManagment/createUser.html', {'aclNames': aclNames})
        elif currentACL['changeUserACL'] == 1:
            aclNames = ACLManager.unFileteredACLs()
            return render(request, 'userManagment/createUser.html', {'aclNames': aclNames})
        elif currentACL['createNewUser'] == 1:
            aclNames = ['user']
            return render(request, 'userManagment/createUser.html', {'aclNames': aclNames})
        else:
            return ACLManager.loadError()

    except BaseException, msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        return redirect(loadLoginPage)


def submitUserCreation(request):
    try:

        try:
            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)
            firstName = data['firstName']
            lastName = data['lastName']
            email = data['email']
            userName = data['userName']
            password = data['password']
            websitesLimit = data['websitesLimit']
            selectedACL = data['selectedACL']

            selectedACL = ACL.objects.get(name=selectedACL)

            if selectedACL.adminStatus == 1:
                type = 1
            else:
                type = 3

            token = hashPassword.generateToken(userName, password)
            password = hashPassword.hash_password(password)
            currentAdmin = Administrator.objects.get(pk=userID)


            if ACLManager.websitesLimitCheck(currentAdmin, websitesLimit) == 0:
                data_ret = {'status': 0, 'createStatus': 0,
                            'error_message': "You've reached maximum websites limit as a reseller."}

                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            if currentACL['admin'] == 1:

                newAdmin = Administrator(firstName=firstName,
                                         lastName=lastName,
                                         email=email,
                                         type=type,
                                         userName=userName,
                                         password=password,
                                         initWebsitesLimit=websitesLimit,
                                         owner=currentAdmin.pk,
                                         acl=selectedACL,
                                         token=token
                                         )
                newAdmin.save()

            elif currentACL['changeUserACL'] == 1:

                newAdmin = Administrator(firstName=firstName,
                                         lastName=lastName,
                                         email=email,
                                         type=type,
                                         userName=userName,
                                         password=password,
                                         initWebsitesLimit=websitesLimit,
                                         owner=currentAdmin.pk,
                                         acl=selectedACL,
                                         token=token
                                         )
                newAdmin.save()
            elif currentACL['createNewUser'] == 1:

                newAdmin = Administrator(firstName=firstName,
                                         lastName=lastName,
                                         email=email,
                                         type=type,
                                         userName=userName,
                                         password=password,
                                         initWebsitesLimit=websitesLimit,
                                         owner=currentAdmin.pk,
                                         acl=selectedACL,
                                         token=token
                                         )
                newAdmin.save()
            else:
                data_ret = {'status': 0, 'createStatus': 0,
                            'error_message': "You are not authorized to access this resource."}

                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            data_ret = {'status': 1, 'createStatus': 1,
                        'error_message': "None"}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)

        except BaseException, msg:
            data_ret = {'status': 0, 'createStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'createStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def modifyUsers(request):
    try:
        userID = request.session['userID']
        adminNames = ACLManager.loadAllUsers(userID)
        return render(request, 'userManagment/modifyUser.html', {"acctNames": adminNames})
    except KeyError:
        return redirect(loadLoginPage)


def fetchUserDetails(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']

                user = Administrator.objects.get(userName=accountUsername)

                firstName = user.firstName
                lastName = user.lastName
                email = user.email

                websitesLimit = user.initWebsitesLimit

                userDetails = {
                    "id": user.id,
                    "firstName": firstName,
                    "lastName": lastName,
                    "email": email,
                    "acl": user.acl.name,
                    "websitesLimit": websitesLimit
                }

                data_ret = {'fetchStatus': 1, 'error_message': 'None', "userDetails": userDetails}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'fetchStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def saveModifications(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']
                firstName = data['firstName']
                lastName = data['lastName']
                email = data['email']

                admin = Administrator.objects.get(pk=val)
                user = Administrator.objects.get(userName=accountUsername)

                token = hashPassword.generateToken(accountUsername, data['password'])
                password = hashPassword.hash_password(data['password'])

                user.firstName = firstName
                user.lastName = lastName
                user.email = email
                user.password = password
                user.token = token
                user.type = 0

                user.save()

                data_ret = {'status': 1, 'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'saveStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def deleteUser(request):
    try:
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            adminNames = ACLManager.loadDeletionUsers(userID, currentACL)
            return render(request, 'userManagment/deleteUser.html', {"acctNames": adminNames})
        elif currentACL['deleteUser'] == 1:
            adminNames = ACLManager.loadDeletionUsers(userID, currentACL)
            return render(request, 'userManagment/deleteUser.html', {"acctNames": adminNames})
        else:
            return ACLManager.loadError()


    except KeyError:
        return redirect(loadLoginPage)


def submitUserDeletion(request):
    try:
        userID = request.session['userID']
        try:

            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']

                currentACL = ACLManager.loadedACL(userID)

                if accountUsername == 'admin':
                    data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': 'You can not delete the super user.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if currentACL['admin'] == 1:
                    user = Administrator.objects.get(userName=accountUsername)
                    user.delete()

                    data_ret = {'status': 1, 'deleteStatus': 1, 'error_message': 'None'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'status': 0, 'deleteStatus': 1, 'error_message': 'Not enough privileges'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'deleteStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def createNewACL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            return render(request, 'userManagment/createACL.html')
        else:
            return ACLManager.loadError()
    except KeyError:
        return redirect(loadLoginPage)


def createACLFunc(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)

            ## Version Management

            newACL = ACL(name=data['aclName'],
                         adminStatus=int(data['makeAdmin']),

                         versionManagement=int(data['versionManagement']),

                         ## User Management
                         createNewUser=int(data['createNewUser']),
                         resellerCenter=int(data['resellerCenter']),
                         deleteUser=int(data['deleteUser']),
                         changeUserACL=int(data['changeUserACL']),

                         ## Website Management

                         createWebsite=int(data['createWebsite']),
                         modifyWebsite=int(data['modifyWebsite']),
                         suspendWebsite=int(data['suspendWebsite']),
                         deleteWebsite=int(data['deleteWebsite']),

                         ## Package Management

                         createPackage=int(data['createPackage']),
                         deletePackage=int(data['deletePackage']),
                         modifyPackage=int(data['modifyPackage']),

                         ## Database Management

                         createDatabase=int(data['createDatabase']),
                         deleteDatabase=int(data['deleteDatabase']),
                         listDatabases=int(data['listDatabases']),

                         ## DNS Management

                         createNameServer=int(data['createNameServer']),
                         createDNSZone=int(data['createDNSZone']),
                         deleteZone=int(data['deleteZone']),
                         addDeleteRecords=int(data['addDeleteRecords']),

                         ## Email Management

                         createEmail=int(data['createEmail']),
                         deleteEmail=int(data['deleteEmail']),
                         emailForwarding=int(data['emailForwarding']),
                         changeEmailPassword=int(data['changeEmailPassword']),
                         dkimManager=int(data['dkimManager']),

                         ## FTP Management

                         createFTPAccount=int(data['createFTPAccount']),
                         deleteFTPAccount=int(data['deleteFTPAccount']),
                         listFTPAccounts=int(data['listFTPAccounts']),

                         ## Backup Management

                         createBackup=int(data['createBackup']),
                         restoreBackup=int(data['restoreBackup']),
                         addDeleteDestinations=int(data['addDeleteDestinations']),
                         scheDuleBackups=int(data['scheDuleBackups']),
                         remoteBackups=int(data['remoteBackups']),

                         ## SSL Management

                         manageSSL=int(data['manageSSL']),
                         hostnameSSL=int(data['hostnameSSL']),
                         mailServerSSL=int(data['mailServerSSL']),
                         )
            newACL.save()

            finalResponse = {'status': 1}
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def deleteACL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            aclNames = ACLManager.findAllACLs()
            return render(request, 'userManagment/deleteACL.html', {'aclNames': aclNames})
        else:
            return ACLManager.loadError()
    except KeyError:
        return redirect(loadLoginPage)

def deleteACLFunc(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)
            acl = ACL.objects.get(name=data['aclToBeDeleted'])

            if acl.administrator_set.all().count() == 0:
                acl.delete()
                finalResponse = {'status': 1}
            else:
                finalResponse = {'status': 0, 'errorMesssage': 'This ACL is currently in used by existing users.', 'error_message': 'This ACL is currently in used by existing users.'}
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def modifyACL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            aclNames = ACLManager.findAllACLs()
            return render(request, 'userManagment/modifyACL.html', {'aclNames': aclNames})
        else:
            return ACLManager.loadError()
    except KeyError:
        return redirect(loadLoginPage)


def fetchACLDetails(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)

            ## Version Management
            finalResponse = {}

            acl = ACL.objects.get(name=data['aclToModify'])
            finalResponse['versionManagement'] = acl.versionManagement
            finalResponse['adminStatus'] = acl.adminStatus

            ## User Management

            finalResponse['createNewUser'] = acl.createNewUser
            finalResponse['resellerCenter'] = acl.resellerCenter
            finalResponse['deleteUser'] = acl.deleteUser
            finalResponse['changeUserACL'] = acl.changeUserACL

            ## Website Management

            finalResponse['createWebsite'] = acl.createWebsite
            finalResponse['modifyWebsite'] = acl.modifyWebsite
            finalResponse['suspendWebsite'] = acl.suspendWebsite
            finalResponse['deleteWebsite'] = acl.deleteWebsite

            ## Package Management


            finalResponse['createPackage'] = acl.createPackage
            finalResponse['deletePackage'] = acl.deletePackage
            finalResponse['modifyPackage'] = acl.modifyPackage

            ## Database Management

            finalResponse['createDatabase'] = acl.createDatabase
            finalResponse['deleteDatabase'] = acl.deleteDatabase
            finalResponse['listDatabases'] = acl.listDatabases

            ## DNS Management

            finalResponse['createNameServer'] = acl.createNameServer
            finalResponse['createDNSZone'] = acl.createDNSZone
            finalResponse['deleteZone'] = acl.deleteZone
            finalResponse['addDeleteRecords'] = acl.addDeleteRecords

            ## Email Management

            finalResponse['createEmail'] = acl.createEmail
            finalResponse['deleteEmail'] = acl.deleteEmail
            finalResponse['emailForwarding'] = acl.emailForwarding
            finalResponse['changeEmailPassword'] = acl.changeEmailPassword
            finalResponse['dkimManager'] = acl.dkimManager

            ## FTP Management

            finalResponse['createFTPAccount'] = acl.createFTPAccount
            finalResponse['deleteFTPAccount'] = acl.deleteFTPAccount
            finalResponse['listFTPAccounts'] = acl.listFTPAccounts

            ## Backup Management

            finalResponse['createBackup'] = acl.createBackup
            finalResponse['restoreBackup'] = acl.restoreBackup
            finalResponse['addDeleteDestinations'] = acl.addDeleteDestinations
            finalResponse['scheDuleBackups'] = acl.scheDuleBackups
            finalResponse['remoteBackups'] = acl.remoteBackups

            ## SSL Management

            finalResponse['manageSSL'] = acl.manageSSL
            finalResponse['hostnameSSL'] = acl.hostnameSSL
            finalResponse['mailServerSSL'] = acl.mailServerSSL

            finalResponse['status'] = 1
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def submitACLModifications(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)

            ## Version Management

            acl = ACL.objects.get(name=data['aclToModify'])
            acl.adminStatus = int(data['adminStatus'])
            acl.versionManagement = int(data['versionManagement'])

            ## User Management

            acl.createNewUser = int(data['createNewUser'])
            acl.resellerCenter = int(data['resellerCenter'])
            acl.deleteUser = int(data['deleteUser'])
            acl.changeUserACL = int(data['changeUserACL'])

            ## Website Management

            acl.createWebsite = int(data['createWebsite'])
            acl.modifyWebsite = int(data['modifyWebsite'])
            acl.suspendWebsite = int(data['suspendWebsite'])
            acl.deleteWebsite = int(data['deleteWebsite'])

            ## Package Management

            acl.createPackage = int(data['createPackage'])
            acl.deletePackage = int(data['deletePackage'])
            acl.modifyPackage = int(data['modifyPackage'])

            ## Database Management

            acl.createDatabase = int(data['createDatabase'])
            acl.deleteDatabase = int(data['deleteDatabase'])
            acl.listDatabases = int(data['listDatabases'])

            ## DNS Management

            acl.createNameServer = int(data['createNameServer'])
            acl.createDNSZone = int(data['createDNSZone'])
            acl.deleteZone = int(data['deleteZone'])
            acl.addDeleteRecords = int(data['addDeleteRecords'])

            ## Email Management

            acl.createEmail = int(data['createEmail'])
            acl.deleteEmail = int(data['deleteEmail'])
            acl.emailForwarding = int(data['emailForwarding'])
            acl.changeEmailPassword = int(data['changeEmailPassword'])
            acl.dkimManager = int(data['dkimManager'])

            ## FTP Management

            acl.createFTPAccount = int(data['createFTPAccount'])
            acl.deleteFTPAccount = int(data['deleteFTPAccount'])
            acl.listFTPAccounts = int(data['listFTPAccounts'])

            ## Backup Management

            acl.createBackup = int(data['createBackup'])
            acl.restoreBackup = int(data['restoreBackup'])
            acl.addDeleteDestinations = int(data['addDeleteDestinations'])
            acl.scheDuleBackups = int(data['scheDuleBackups'])
            acl.remoteBackups = int(data['remoteBackups'])

            ## SSL Management

            acl.manageSSL = int(data['manageSSL'])
            acl.hostnameSSL = int(data['hostnameSSL'])
            acl.mailServerSSL = int(data['mailServerSSL'])

            acl.save()

            if int(data['adminStatus']) == 1:
                allUsers = acl.administrator_set.all()

                for items in allUsers:
                    items.type = 1
                    items.save()
            else:
                allUsers = acl.administrator_set.all()

                for items in allUsers:
                    items.type = 3
                    items.save()

            finalResponse = {'status': 1}
        else:
            finalResponse = ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def changeUserACL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            aclNames = ACLManager.unFileteredACLs()
            userNames = ACLManager.findAllUsers()
            return render(request, 'userManagment/changeUserACL.html', {'aclNames': aclNames, 'usersList': userNames})
        elif currentACL['changeUserACL'] == 1:
            aclNames = ACLManager.unFileteredACLs()
            userNames = ACLManager.findAllUsers()

            return render(request, 'userManagment/changeUserACL.html', {'aclNames': aclNames, 'usersList': userNames})
        else:
            return ACLManager.loadError()


    except KeyError:
        return redirect(loadLoginPage)


def changeACLFunc(request):
    try:
        val = request.session['userID']
        data = json.loads(request.body)

        if data['selectedUser'] == 'admin':
            finalResponse = {'status': 0,
                             'errorMessage': "Super user can not be modified.",
                             'error_message': "Super user can not be modified."}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            selectedACL = ACL.objects.get(name=data['selectedACL'])
            selectedUser = Administrator.objects.get(userName=data['selectedUser'])

            selectedUser.acl = selectedACL
            selectedUser.save()

            finalResponse = {'status': 1}
        elif currentACL['changeUserACL'] == 1:
            selectedACL = ACL.objects.get(name=data['selectedACL'])
            selectedUser = Administrator.objects.get(userName=data['selectedUser'])

            selectedUser.acl = selectedACL
            selectedUser.save()

            finalResponse = {'status': 1}
        else:
            finalResponse = ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def resellerCenter(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            userNames = ACLManager.loadDeletionUsers(userID, currentACL)
            resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
            return render(request, 'userManagment/resellerCenter.html',
                          {'userToBeModified': userNames, 'resellerPrivUsers': resellerPrivUsers})
        elif currentACL['resellerCenter'] == 1:
            userNames = ACLManager.loadDeletionUsers(userID, currentACL)
            resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
            return render(request, 'userManagment/resellerCenter.html',
                          {'userToBeModified': userNames, 'resellerPrivUsers': resellerPrivUsers})
        else:
            return ACLManager.loadError()


    except KeyError:
        return redirect(loadLoginPage)


def saveResellerChanges(request):
    try:
        val = request.session['userID']
        data = json.loads(request.body)

        if data['userToBeModified'] == 'admin':
            finalResponse = {'status': 0,
                             'errorMessage': "Super user can not be modified.",
                             'error_message': "Super user can not be modified."}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)

        userToBeModified = Administrator.objects.get(userName=data['userToBeModified'])
        newOwner = Administrator.objects.get(userName=data['newOwner'])

        if ACLManager.websitesLimitCheck(newOwner, data['websitesLimit'], userToBeModified) == 0:
            finalResponse = {'status': 0,
                             'errorMessage': "You've reached maximum websites limit as a reseller.",
                             'error_message': "You've reached maximum websites limit as a reseller."}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)

        userToBeModified.owner = newOwner.pk
        userToBeModified.initWebsitesLimit = data['websitesLimit']
        userToBeModified.save()

        finalResponse = {'status': 1}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException, msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
