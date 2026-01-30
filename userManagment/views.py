# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator, ACL
import json
from plogical import hashPassword
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.virtualHostUtilities import virtualHostUtilities
from CyberCP.secMiddleware import secMiddleware
from CyberCP.SecurityLevel import SecurityLevel
from plogical.errorSanitizer import secure_error_response, secure_log_error, handle_secure_exception


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
                # When enabling API access, ensure the user has a proper token
                # The token should be generated based on username:password format
                # If no token exists, we'll need the user to reset their password
                if not userAcct.token or userAcct.token == 'None' or userAcct.token == '':
                    # Token will be generated when user changes their password
                    # For now, set a placeholder that indicates API access is enabled but token needs generation
                    userAcct.token = 'TOKEN_NEEDS_GENERATION'
            else:
                userAcct.api = 0

            userAcct.save()

            finalResponse = {'status': 1}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)
    except Exception as e:
        secure_log_error(e, 'saveChangesAPIAccess', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to update API access settings')
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)


def fetchAPIUsers(request):
    """
    Fetch all users with API access enabled, with optional search functionality
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            finalResponse = {'status': 0, "error_message": "Only administrators are allowed to perform this task."}
            json_data = json.dumps(finalResponse)
            return HttpResponse(json_data)
        
        # Get search query if provided
        search_query = request.GET.get('search', '').strip()
        
        # Fetch all users with API access enabled
        api_users = Administrator.objects.filter(api=1).select_related('acl')
        
        # Apply search filter if provided
        if search_query:
            api_users = api_users.filter(
                models.Q(userName__icontains=search_query) |
                models.Q(firstName__icontains=search_query) |
                models.Q(lastName__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )
        
        # Prepare user data
        users_data = []
        for user in api_users:
            # Determine token status
            token_status = "Valid"
            if not user.token or user.token == 'None' or user.token == '':
                token_status = "Not Generated"
            elif user.token == 'TOKEN_NEEDS_GENERATION':
                token_status = "Needs Generation"
            
            # Get ACL name
            acl_name = user.acl.name if user.acl else "Default"
            
            users_data.append({
                'id': user.pk,
                'userName': user.userName,
                'firstName': user.firstName,
                'lastName': user.lastName,
                'email': user.email,
                'aclName': acl_name,
                'tokenStatus': token_status,
                'state': user.state,
                'createdDate': user.pk,  # Using pk as a proxy for creation order
                'lastLogin': 'N/A'  # This would need to be tracked separately
            })
        
        # Sort by username
        users_data.sort(key=lambda x: x['userName'].lower())
        
        finalResponse = {
            'status': 1,
            'users': users_data,
            'totalCount': len(users_data)
        }
        json_data = json.dumps(finalResponse)
        return HttpResponse(json_data)
        
    except Exception as e:
        secure_log_error(e, 'fetchAPIUsers', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to fetch API users')
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
            selectedHomeDirectory = data.get('selectedHomeDirectory', '')

            if ACLManager.CheckRegEx("^[\w'\-,.][^0-9_!¡?÷?¿/\\+=@#$%ˆ&*(){}|~<>;:[\]]{2,}$", firstName) == 0:
                data_ret = {'status': 0, 'createStatus': 0, 'error_message': 'First Name can only contain alphabetic characters, and should be more than 2 characters long...'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, content_type='application/json')

            if ACLManager.CheckRegEx("^[\w'\-,.][^0-9_!¡?÷?¿/\\+=@#$%ˆ&*(){}|~<>;:[\]]{2,}$", lastName) == 0:
                data_ret = {'status': 0, 'createStatus': 0, 'error_message': 'Last Name can only contain alphabetic characters, and should be more than 2 characters long...'}
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

            # Handle home directory assignment
            from .homeDirectoryManager import HomeDirectoryManager
            from .models import HomeDirectory, UserHomeMapping
            
            if selectedHomeDirectory:
                # Use selected home directory
                try:
                    home_dir = HomeDirectory.objects.get(id=selectedHomeDirectory)
                    home_path = home_dir.path
                except HomeDirectory.DoesNotExist:
                    home_path = HomeDirectoryManager.getBestHomeDirectory()
            else:
                # Auto-select best home directory
                home_path = HomeDirectoryManager.getBestHomeDirectory()
                try:
                    home_dir = HomeDirectory.objects.get(path=home_path)
                except HomeDirectory.DoesNotExist:
                    # Create home directory entry if it doesn't exist
                    home_dir = HomeDirectory.objects.create(
                        name=home_path.split('/')[-1],
                        path=home_path,
                        is_active=True,
                        is_default=(home_path == '/home')
                    )
            
            # Create user directory
            if HomeDirectoryManager.createUserDirectory(userName, home_path):
                # Create user-home mapping
                UserHomeMapping.objects.create(
                    user=newAdmin,
                    home_directory=home_dir
                )
            else:
                # Log error but don't fail user creation
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f"Failed to create user directory for {userName} in {home_path}")

            data_ret = {'status': 1, 'createStatus': 1,
                        'error_message': "None"}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json, content_type='application/json')

        except Exception as e:
            secure_log_error(e, 'submitUserCreation', request.session.get('userID', 'Unknown'))
            data_ret = secure_error_response(e, 'Failed to create user account')
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
                    'twofa': user.twoFA,
                    'secretKey': user.secretKey
                }

                data_ret = {'fetchStatus': 1, 'error_message': 'None', "userDetails": userDetails}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except Exception as e:
            secure_log_error(e, 'fetchUserDetails', request.session.get('userID', 'Unknown'))
            data_ret = secure_error_response(e, 'Failed to fetch user details')
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

            # Only update password if a new one is provided
            if 'passwordByPass' in data and data['passwordByPass'] and data['passwordByPass'].strip():
                token = hashPassword.generateToken(accountUsername, data['passwordByPass'])
                password = hashPassword.hash_password(data['passwordByPass'])
                user.password = password
                user.token = token

            user.firstName = firstName
            user.lastName = lastName
            user.email = email
            user.type = 0
            
            # Check if 2FA is being enabled (transition from 0 to 1)
            was_2fa_disabled = user.twoFA == 0
            user.twoFA = twofa

            # If 2FA is being disabled, clear the secret key
            if twofa == 0:
                user.secretKey = 'None'
            # If 2FA is being enabled (transition from disabled to enabled), always generate a new secret
            elif twofa == 1 and was_2fa_disabled:
                import pyotp
                user.secretKey = pyotp.random_base32()
                
                # Log the secret regeneration for security audit
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'2FA secret auto-regenerated for user: {accountUsername} by admin: {val}')

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

        except Exception as e:
            secure_log_error(e, 'saveModifications', request.session.get('userID', 'Unknown'))
            data_ret = secure_error_response(e, 'Failed to save user modifications')
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

        except Exception as e:
            secure_log_error(e, 'submitUserDeletion', request.session.get('userID', 'Unknown'))
            data_ret = secure_error_response(e, 'Failed to delete user account')
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
    except Exception as e:
        secure_log_error(e, 'createACLFunc', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to create ACL')
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
    except Exception as e:
        secure_log_error(e, 'deleteACLFunc', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to delete ACL')
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
    except Exception as e:
        secure_log_error(e, 'fetchACLDetails', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to fetch ACL details')
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
    except Exception as e:
        secure_log_error(e, 'submitACLModifications', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to submit ACL modifications')
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
    except Exception as e:
        secure_log_error(e, 'changeACLFunc', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to change user ACL')
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
    except Exception as e:
        secure_log_error(e, 'saveResellerChanges', request.session.get('userID', 'Unknown'))
        finalResponse = secure_error_response(e, 'Failed to save reseller changes')
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

        except Exception as e:
            secure_log_error(e, 'controlUserState', request.session.get('userID', 'Unknown'))
            data_ret = secure_error_response(e, 'Failed to control user state')
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'status': 0, 'saveStatus': 0, 'error_message': "Not logged in as admin", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def userMigration(request):
    """Load user migration interface"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return ACLManager.loadError()
        
        proc = httpProc(request, 'userManagment/userMigration.html', {}, 'admin')
        return proc.render()
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error loading user migration: {str(e)}")
        return ACLManager.loadError()


def disable2FA(request):
    """
    Disable 2FA for a specific user (admin function)
    """
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        
        if currentACL['admin'] != 1:
            data_ret = {'status': 0, 'error_message': 'Unauthorized access. Admin privileges required.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        
        if request.method == 'POST':
            data = json.loads(request.body)
            accountUsername = data.get('accountUsername')
            
            if not accountUsername:
                data_ret = {'status': 0, 'error_message': 'Username is required.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            try:
                user = Administrator.objects.get(userName=accountUsername)
                
                # Disable 2FA and clear secret key
                user.twoFA = 0
                user.secretKey = 'None'
                user.save()
                
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'2FA disabled for user: {accountUsername} by admin: {val}')
                
                data_ret = {
                    'status': 1, 
                    'error_message': '2FA successfully disabled for user.',
                    'message': f'Two-factor authentication has been disabled for user {accountUsername}.'
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
                
            except Administrator.DoesNotExist:
                data_ret = {'status': 0, 'error_message': 'User not found.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        
        data_ret = {'status': 0, 'error_message': 'Invalid request method.'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
        
    except Exception as e:
        secure_log_error(e, 'disable2FA', request.session.get('userID', 'Unknown'))
        data_ret = secure_error_response(e, 'Failed to disable 2FA')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def regenerateTwoFASecret(request):
    """
    Manually regenerate 2FA secret for a specific user
    """
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        
        if currentACL['admin'] != 1:
            data_ret = {'status': 0, 'error_message': 'Unauthorized access. Admin privileges required.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        
        if request.method == 'POST':
            data = json.loads(request.body)
            accountUsername = data.get('accountUsername')
            
            if not accountUsername:
                data_ret = {'status': 0, 'error_message': 'Username is required.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            try:
                user = Administrator.objects.get(userName=accountUsername)
                
                # Check if user has 2FA enabled
                if not user.twoFA:
                    data_ret = {'status': 0, 'error_message': '2FA is not enabled for this user.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                
                # Generate new secret key
                import pyotp
                new_secret = pyotp.random_base32()
                user.secretKey = new_secret
                user.save()
                
                # Generate new QR code provisioning URI
                otpauth = pyotp.totp.TOTP(new_secret).provisioning_uri(user.email, issuer_name="CyberPanel")
                
                # Log the secret regeneration for security audit
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'2FA secret manually regenerated for user: {accountUsername} by admin: {val}')
                
                data_ret = {
                    'status': 1, 
                    'error_message': '2FA secret successfully regenerated.',
                    'message': f'Two-factor authentication secret has been regenerated for user {accountUsername}.',
                    'secretKey': new_secret,
                    'otpauth': otpauth
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
                
            except Administrator.DoesNotExist:
                data_ret = {'status': 0, 'error_message': 'User not found.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        
        data_ret = {'status': 0, 'error_message': 'Invalid request method.'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
        
    except Exception as e:
        secure_log_error(e, 'regenerateTwoFASecret', request.session.get('userID', 'Unknown'))
        data_ret = secure_error_response(e, 'Failed to regenerate 2FA secret')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
