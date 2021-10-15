# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator, ACL
import json
from plogical import hashPassword
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.virtualHostUtilities import virtualHostUtilities
from CyberCP.secMiddleware import secMiddleware
from CyberCP.SecurityLevel import SecurityLevel


def loadUserHome(request):

    val = request.session['userID']
    admin = Administrator.objects.get(pk=val)
    currentACL = ACLManager.loadedACL(val)

    if currentACL['admin'] == 1:
        listUsers = 1
    else:
        listUsers = currentACL['listUsers']

    proc = httpProc(request, 'userManagment/index.html',
                    {"type": admin.type, 'listUsers': listUsers}, 'listUsers')
    return proc.render()


def viewProfile(request):
    userID = request.session['userID']
    admin = Administrator.objects.get(pk=userID)

    AdminData = {}

    AdminData['userName'] = admin.userName
    AdminData['firstName'] = admin.firstName
    AdminData['lastName'] = admin.lastName
    AdminData['websitesLimit'] = admin.initWebsitesLimit
    AdminData['email'] = admin.email
    AdminData['accountACL'] = admin.acl.name

    proc = httpProc(request, 'userManagment/userProfile.html',
                    AdminData)
    return proc.render()


def createUser(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] == 1:
        aclNames = ACLManager.unFileteredACLs()
        proc = httpProc(request, 'userManagment/createUser.html',
                        {'aclNames': aclNames, 'securityLevels': SecurityLevel.list()})
        return proc.render()
    elif currentACL['changeUserACL'] == 1:
        aclNames = ACLManager.unFileteredACLs()
        proc = httpProc(request, 'userManagment/createUser.html',
                        {'aclNames': aclNames, 'securityLevels': SecurityLevel.list()})
        return proc.render()
    elif currentACL['createNewUser'] == 1:
        aclNames = ['user']
        proc = httpProc(request, 'userManagment/createUser.html',
                        {'aclNames': aclNames, 'securityLevels': SecurityLevel.list()})
        return proc.render()
    else:
        return ACLManager.loadError()


def apiAccess(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    adminNames = ACLManager.loadDeletionUsers(userID, currentACL)
    adminNames.append("admin")
    proc = httpProc(request, 'userManagment/apiAccess.html',
                    {'acctNames': adminNames}, 'admin')
    return proc.render()


def saveChangesAPIAccess(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        data = json.loads(request.body)

        if currentACL['admin'] != 1:
            finalResponse = {'status': 0, "error_message": "Only administrators are allowed to perform this task."}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)
        else:
            accountUsername = data['accountUsername']
            access = data['access']

            userAcct = Administrator.objects.get(userName=accountUsername)

            if access == "Enable":
                userAcct.api = 1
            else:
                userAcct.api = 0

            userAcct.save()

            finalResponse = {'status': 1}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def submitUserCreation(request):
    try:

        try:
            try:
                userID = request.session['userID']
                currentACL = ACLManager.loadedACL(userID)
                data = json.loads(request.body)
            except:
                userID = request['userID']
                data = request
                currentACL = ACLManager.loadedACL(userID)

            firstName = data['firstName']
            lastName = data['lastName']
            email = data['email']
            userName = data['userName']
            password = data['password']
            websitesLimit = data['websitesLimit']
            selectedACL = data['selectedACL']

            if ACLManager.CheckRegEx("^[\w'\-,.][^0-9_!¡?÷?¿/\\+=@#$%ˆ&*(){}|~<>;:[\]]{2,}$", firstName) == 0:
                data_ret = {'status': 0, 'createStatus': 0, 'error_message': 'First Name can only contain Alphabets and should be more then 2 characters..'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if ACLManager.CheckRegEx("^[\w'\-,.][^0-9_!¡?÷?¿/\\+=@#$%ˆ&*(){}|~<>;:[\]]{2,}$", lastName) == 0:
                data_ret = {'status': 0, 'createStatus': 0, 'error_message': 'First Name can only contain Alphabets and should be more then 2 characters..'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            import validators
            if not validators.email(email):
                data_ret = {'status': 0, 'createStatus': 0,
                            'error_message': 'Invalid email address.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                securityLevel = data['securityLevel']
            except:
                securityLevel = 'HIGH'

            selectedACL = ACL.objects.get(name=selectedACL)

            if selectedACL.adminStatus == 1:
                type = 1
            else:
                type = 3

            if securityLevel == 'LOW':
                securityLevel = secMiddleware.LOW
            else:
                securityLevel = secMiddleware.HIGH

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
                                         token=token,
                                         securityLevel=securityLevel,
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
                                         token=token,
                                         securityLevel=securityLevel,
                                         )
                newAdmin.save()
            elif currentACL['createNewUser'] == 1:

                if selectedACL.name != 'user':
                    data_ret = {'status': 0, 'createStatus': 0,
                                'error_message': "You are not authorized to access this resource."}

                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                newAdmin = Administrator(firstName=firstName,
                                         lastName=lastName,
                                         email=email,
                                         type=type,
                                         userName=userName,
                                         password=password,
                                         initWebsitesLimit=websitesLimit,
                                         owner=currentAdmin.pk,
                                         acl=selectedACL,
                                         token=token,
                                         securityLevel=securityLevel,
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

        except BaseException as msg:
            data_ret = {'status': 0, 'createStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'createStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def modifyUsers(request):
    userID = request.session['userID']
    userNames = ACLManager.loadAllUsers(userID)
    proc = httpProc(request, 'userManagment/modifyUser.html',
                    {"acctNames": userNames, 'securityLevels': SecurityLevel.list()})
    return proc.render()


def fetchUserDetails(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']

                user = Administrator.objects.get(userName=accountUsername)

                currentACL = ACLManager.loadedACL(val)
                loggedUser = Administrator.objects.get(pk=val)

                if currentACL['admin'] == 1:
                    pass
                elif user.owner == loggedUser.pk:
                    pass
                elif user.pk == loggedUser.pk:
                    pass
                else:
                    data_ret = {'fetchStatus': 0, 'error_message': 'Un-authorized access.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                firstName = user.firstName
                lastName = user.lastName
                email = user.email

                websitesLimit = user.initWebsitesLimit

                import pyotp

                if user.secretKey == 'None':
                    user.secretKey = pyotp.random_base32()
                    user.save()

                otpauth = pyotp.totp.TOTP(user.secretKey).provisioning_uri(email, issuer_name="CyberPanel")

                userDetails = {
                    "id": user.id,
                    "firstName": firstName,
                    "lastName": lastName,
                    "email": email,
                    "acl": user.acl.name,
                    "websitesLimit": websitesLimit,
                    "securityLevel": SecurityLevel(user.securityLevel).name,
                    "otpauth": otpauth,
                    'twofa': user.twoFA
                }

                data_ret = {'fetchStatus': 1, 'error_message': 'None', "userDetails": userDetails}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'fetchStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def saveModifications(request):
    try:
        try:
            val = request.session['userID']
        except:
            val = request['userID']
        try:
            try:
                data = json.loads(request.body)
            except:
                data = request

            accountUsername = data['accountUsername']
            firstName = data['firstName']
            lastName = data['lastName']
            email = data['email']
            try:
                securityLevel = data['securityLevel']
            except:
                securityLevel = 'HIGH'

            try:
                twofa = int(data['twofa'])
            except:
                twofa = 0

            user = Administrator.objects.get(userName=accountUsername)

            currentACL = ACLManager.loadedACL(val)
            loggedUser = Administrator.objects.get(pk=val)

            if currentACL['admin'] == 1:
                pass
            elif user.owner == loggedUser.pk:
                pass
            elif user.pk == loggedUser.pk:
                pass
            else:
                data_ret = {'fetchStatus': 0, 'error_message': 'Un-authorized access.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            token = hashPassword.generateToken(accountUsername, data['passwordByPass'])
            password = hashPassword.hash_password(data['passwordByPass'])

            user.firstName = firstName
            user.lastName = lastName
            user.email = email
            user.password = password
            user.token = token
            user.type = 0
            user.twoFA = twofa

            if securityLevel == 'LOW':
                user.securityLevel = secMiddleware.LOW
            else:
                user.securityLevel = secMiddleware.HIGH

            user.save()

            adminEmailPath = '/home/cyberpanel/adminEmail'

            if accountUsername == 'admin':
                writeToFile = open(adminEmailPath, 'w')
                writeToFile.write(email)
                writeToFile.close()

            data_ret = {'status': 1, 'saveStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'saveStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def deleteUser(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] == 1:
        adminNames = ACLManager.loadDeletionUsers(userID, currentACL)
        proc = httpProc(request, 'userManagment/deleteUser.html',
                        {"acctNames": adminNames})
        return proc.render()
    elif currentACL['deleteUser'] == 1:
        adminNames = ACLManager.loadDeletionUsers(userID, currentACL)
        proc = httpProc(request, 'userManagment/deleteUser.html',
                        {"acctNames": adminNames})
        return proc.render()
    else:
        return ACLManager.loadError()


def submitUserDeletion(request):

    try:
        try:
            userID = request.session['userID']
        except:
            userID = request['userID']
        try:

            try:
                data = json.loads(request.body)
            except:
                data = request

            accountUsername = data['accountUsername']

            try:
                force = data['force']
            except:
                force = 0

            currentACL = ACLManager.loadedACL(userID)

            currentUser = Administrator.objects.get(pk=userID)
            userInQuestion = Administrator.objects.get(userName=accountUsername)

            if ACLManager.checkUserOwnerShip(currentACL, currentUser, userInQuestion):

                if force:
                    userACL = ACLManager.loadedACL(userInQuestion.pk)
                    websitesName = ACLManager.findAllSites(userACL, userInQuestion.pk)

                    from websiteFunctions.website import WebsiteManager
                    wm = WebsiteManager()

                    for website in websitesName:
                        wm.submitWebsiteDeletion(userID, {'websiteName': website})

                user = Administrator.objects.get(userName=accountUsername)

                childUsers = Administrator.objects.filter(owner=user.pk)

                for items in childUsers:
                    items.delete()

                user.delete()

                data_ret = {'status': 1, 'deleteStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': 'Not enough privileges.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'deleteStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def createNewACL(request):
    proc = httpProc(request, 'userManagment/createACL.html',
                    None, 'admin')
    return proc.render()


def createACLFunc(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)

            ## Version Management

            if data['makeAdmin']:
                data['adminStatus'] = 1
            else:
                data['adminStatus'] = 0

            newACL = ACL(name=data['aclName'], config=json.dumps(data))
            newACL.save()

            finalResponse = {'status': 1}
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def deleteACL(request):
    aclNames = ACLManager.findAllACLs()
    proc = httpProc(request, 'userManagment/deleteACL.html',
                    {'aclNames': aclNames}, 'admin')
    return proc.render()


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
                finalResponse = {'status': 0, 'errorMesssage': 'This ACL is currently in used by existing users.',
                                 'error_message': 'This ACL is currently in used by existing users.'}
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def modifyACL(request):
    aclNames = ACLManager.findAllACLs()
    proc = httpProc(request, 'userManagment/modifyACL.html',
                    {'aclNames': aclNames}, 'admin')
    return proc.render()


def fetchACLDetails(request):
    try:
        val = request.session['userID']

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            data = json.loads(request.body)

            ## Version Management
            finalResponse = {}
            acl = ACL.objects.get(name=data['aclToModify'])
            finalResponse = json.loads(acl.config)
            finalResponse['status'] = 1
        else:
            return ACLManager.loadErrorJson()

        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException as msg:
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
            acl.config = json.dumps(data)
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
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)

def changeUserACL(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] == 1:
        aclNames = ACLManager.unFileteredACLs()
        userNames = ACLManager.findAllUsers()
        proc = httpProc(request, 'userManagment/changeUserACL.html',
                        {'aclNames': aclNames, 'usersList': userNames}, 'admin')
        return proc.render()
    elif currentACL['changeUserACL'] == 1:
        aclNames = ACLManager.unFileteredACLs()
        userNames = ACLManager.findAllUsers()
        proc = httpProc(request, 'userManagment/changeUserACL.html',
                        {'aclNames': aclNames, 'usersList': userNames})
        return proc.render()
    else:
        return ACLManager.loadError()


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
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def resellerCenter(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] == 1:
        userNames = ACLManager.loadDeletionUsers(userID, currentACL)
        resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
        proc = httpProc(request, 'userManagment/resellerCenter.html',
                        {'userToBeModified': userNames, 'resellerPrivUsers': resellerPrivUsers})
        return proc.render()
    elif currentACL['resellerCenter'] == 1:
        userNames = ACLManager.loadDeletionUsers(userID, currentACL)
        resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
        proc = httpProc(request, 'userManagment/resellerCenter.html',
                        {'userToBeModified': userNames, 'resellerPrivUsers': resellerPrivUsers})
        return proc.render()
    else:
        return ACLManager.loadError()


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

        currentACL = ACLManager.loadedACL(val)

        if currentACL['admin'] == 1:
            pass
        elif currentACL['resellerCenter'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        loggedUser = Administrator.objects.get(pk=val)

        userToBeModified = Administrator.objects.get(userName=data['userToBeModified'])
        newOwner = Administrator.objects.get(userName=data['newOwner'])

        ### Check user owners

        if ACLManager.checkUserOwnerShip(currentACL, loggedUser, userToBeModified) == 0 or ACLManager.checkUserOwnerShip(currentACL, loggedUser, newOwner) == 0:
            return ACLManager.loadErrorJson()

        try:
            if ACLManager.websitesLimitCheck(newOwner, data['websitesLimit'], userToBeModified) == 0:
                finalResponse = {'status': 0,
                                 'errorMessage': "You've reached maximum websites limit as a reseller.",
                                 'error_message': "You've reached maximum websites limit as a reseller."}
                json_data = json.dumps(finalResponse)
                return HttpResponse(json_data)
        except:
            pass

        userToBeModified.owner = newOwner.pk
        try:
            userToBeModified.initWebsitesLimit = data['websitesLimit']
        except:
            pass
        userToBeModified.save()

        finalResponse = {'status': 1}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
    except BaseException as msg:
        finalResponse = {'status': 0, 'errorMessage': str(msg), 'error_message': str(msg)}
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def listUsers(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] == 1:
        aclNames = ACLManager.unFileteredACLs()
    elif currentACL['changeUserACL'] == 1:
        aclNames = ACLManager.unFileteredACLs()
    elif currentACL['createNewUser'] == 1:
        aclNames = ['user']
    else:
        aclNames = []

    if currentACL['admin'] == 1:
        resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
    elif currentACL['resellerCenter'] == 1:
        resellerPrivUsers = ACLManager.userWithResellerPriv(userID)
    else:
        resellerPrivUsers = []

    if currentACL['admin'] == 1:
        proc = httpProc(request, 'userManagment/listUsers.html',
                        {'aclNames': aclNames, 'resellerPrivUsers': resellerPrivUsers})
        return proc.render()
    elif currentACL['listUsers'] == 1:
        proc = httpProc(request, 'userManagment/listUsers.html',
                        {'aclNames': aclNames, 'resellerPrivUsers': resellerPrivUsers})
        return proc.render()
    else:
        return ACLManager.loadError()

def fetchTableUsers(request):
    try:
        try:
            userID = request.session['userID']
        except:
            userID = request['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            users = ACLManager.fetchTableUserObjects(userID)
        elif currentACL['listUsers'] == 1:
            users = ACLManager.fetchTableUserObjects(userID)
        else:
            return ACLManager.loadErrorJson()

        json_data = "["
        checker = 0

        for items in users:

            diskUsageCurrent = 0

            for webs in items.websites_set.all():
                DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(webs)
                diskUsageCurrent = DiskUsage + diskUsageCurrent

            try:
                owner = Administrator.objects.get(pk=items.owner)
            except:
                ### If user owner is deleted then owner is admin
                items.owner = 1
                items.save()
                owner = Administrator.objects.get(pk=1)

            dic = {'id': items.pk,
                   'name': items.userName,
                   'owner': owner.userName,
                   'acl': items.acl.name,
                   'diskUsage': '%sMB' % str(diskUsageCurrent),
                   'websites': items.initWebsitesLimit,
                   'state': items.state
                   }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)

    except KeyError:
        return redirect(loadLoginPage)


def controlUserState(request):
    try:
        try:
            val = request.session['userID']
        except:
            val = request['userID']
        try:
            try:
                data = json.loads(request.body)
            except:
                data = request

            accountUsername = data['accountUsername']
            state = data['state']

            user = Administrator.objects.get(userName=accountUsername)

            currentACL = ACLManager.loadedACL(val)
            loggedUser = Administrator.objects.get(pk=val)

            if currentACL['admin'] == 1:
                pass
            elif user.owner == loggedUser.pk:
                pass
            elif user.pk == loggedUser.pk:
                pass
            else:
                data_ret = {'fetchStatus': 0, 'error_message': 'Un-authorized access.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if state == 'SUSPEND':
                user.state = 'SUSPENDED'
            else:
                user.state = 'ACTIVE'

            user.save()

            extraArgs = {}
            extraArgs['user'] = user
            extraArgs['currentACL'] = ACLManager.loadedACL(user.pk)
            extraArgs['state'] = state

            from userManagment.userManager import UserManager

            um = UserManager('controlUserState', extraArgs)
            um.start()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'saveStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
