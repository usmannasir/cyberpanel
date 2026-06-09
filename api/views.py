# -*- coding: utf-8 -*-

import json
from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical import hashPassword
from packages.models import Package
from baseTemplate.views import renderBase
from random import randint
from websiteFunctions.models import Websites
import os
from baseTemplate.models import version
from plogical.mailUtilities import mailUtilities
from websiteFunctions.website import WebsiteManager
from packages.packagesManager import PackagesManager
from s3Backups.s3Backups import S3Backups
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from plogical.errorSanitizer import secure_error_response, secure_log_error
from django.views.decorators.csrf import csrf_exempt
from userManagment.views import submitUserCreation as suc
from userManagment.views import submitUserDeletion as duc
from plogical.securityUtils import (
    api_token_matches,
    is_safe_numeric_id,
    is_safe_port,
    is_safe_remote_host,
)
from plogical.acl import ACLManager
# Create your views here.

def validate_api_input(input_value, field_name="field"):
    """
    Validate API input for security threats while allowing legitimate data
    Returns tuple: (is_valid, error_message)
    """
    if not isinstance(input_value, str):
        return True, None
    
    # Check for command injection patterns
    dangerous_patterns = [
        ';', '&&', '||', '|', '`', '$', 
        '../', '../../', '\n', '\r',
        '<script', '</script>', 'javascript:',
        'eval(', 'exec(', 'system(', 'shell_exec('
    ]
    
    for pattern in dangerous_patterns:
        if pattern in input_value:
            return False, f"{field_name} contains invalid characters or patterns."
    
    return True, None


def api_error(status_key, message, http_status=200):
    return HttpResponse(json.dumps({status_key: 0, 'error_message': message}), status=http_status)


def get_api_admin(request, data, username_key='adminUser', password_key='adminPass', allow_token=True):
    """
    Resolve and authenticate the admin behind an API call.

    Accepts either a (token via HTTP_AUTHORIZATION) or username/password pair.
    Returns (admin, None) on success, or (None, HttpResponse) on failure.
    """
    admin_user = data.get(username_key)
    if not admin_user:
        return None, api_error('status', 'Missing API username.', 400)

    try:
        admin = Administrator.objects.get(userName=admin_user)
    except Administrator.DoesNotExist:
        return None, api_error('status', 'Could not authorize access to API.', 401)

    if admin.api == 0:
        return None, api_error('status', 'API Access Disabled.', 403)

    authorization = request.META.get('HTTP_AUTHORIZATION')
    if allow_token and authorization and api_token_matches(authorization, admin.token):
        return admin, None

    admin_pass = data.get(password_key)
    if admin_pass and hashPassword.check_password(admin.password, admin_pass):
        return admin, None

    return None, api_error('status', 'Could not authorize access to API.', 401)


def api_auth_response(auth_error, status_key='status', extra=None):
    error_message = json.loads(auth_error.content.decode()).get('error_message')
    data = {status_key: 0, 'error_message': error_message}
    if extra:
        data.update(extra)
    return HttpResponse(json.dumps(data))


def can_change_api_account_password(admin, target_user):
    """
    True when `admin` is allowed to set the password of `target_user` over the
    API. Super admin can change anyone. Otherwise, the admin can only change
    accounts they own (created themselves) or their own account.
    """
    if admin.userName == target_user.userName:
        return True
    if getattr(admin, 'admin_id', None) is None:
        # Top-level admin: allow ownership-restricted changes.
        try:
            return target_user.owner_id == admin.pk
        except Exception:
            return False
    # Reseller/sub-admin: only their own account.
    return False


def can_change_api_website_package(admin, website):
    """
    True when `admin` may change the package of `website` via the API.
    """
    if admin.userName == website.admin.userName:
        return True
    if getattr(admin, 'admin_id', None) is None:
        try:
            return website.admin.owner_id == admin.pk
        except Exception:
            return False
    return False


@csrf_exempt
def verifyConn(request):
    try:
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                adminUser = data['adminUser']
                adminPass = data['adminPass']
                
                # Additional security: validate input for dangerous characters
                is_valid, error_msg = validate_api_input(adminUser, "adminUser")
                if not is_valid:
                    data_ret = {"verifyConn": 0, 'error_message': error_msg}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data, status=400)
                    
            except (json.JSONDecodeError, KeyError) as e:
                data_ret = {"verifyConn": 0, 'error_message': "Invalid JSON or missing adminUser/adminPass fields."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=400)

            try:
                admin = Administrator.objects.get(userName=adminUser)
            except Administrator.DoesNotExist:
                data_ret = {"verifyConn": 0, 'error_message': "Administrator not found."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=404)

            if admin.api == 0:
                data_ret = {"verifyConn": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=403)

            if hashPassword.check_password(admin.password, adminPass):
                data_ret = {"verifyConn": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"verifyConn": 0, 'error_message': "Invalid password."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=401)
        else:
            data_ret = {"verifyConn": 0, 'error_message': "Only POST method allowed."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=405)
    except Exception as msg:
        data_ret = {'verifyConn': 0, 'error_message': f"Internal server error: {str(msg)}"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, status=500)


@csrf_exempt
def createWebsite(request):
    try:
        if request.method != 'POST':
            data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                        'error_message': "Only POST method allowed."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=405)

        try:
            data = json.loads(request.body)
            adminUser = data['adminUser']
            
            # Additional security: validate critical fields for dangerous characters
            is_valid, error_msg = validate_api_input(adminUser, "adminUser")
            if not is_valid:
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0, 'error_message': error_msg}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=400)
                
            # Validate domain name if provided
            if 'domainName' in data:
                is_valid, error_msg = validate_api_input(data['domainName'], "domainName")
                if not is_valid:
                    data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0, 'error_message': error_msg}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data, status=400)
                    
        except (json.JSONDecodeError, KeyError):
            data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                        'error_message': "Invalid JSON or missing adminUser field."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=400)

        try:
            admin = Administrator.objects.get(userName=adminUser)
        except Administrator.DoesNotExist:
            data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                        'error_message': "Administrator not found."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=404)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Create website payload in API {str(data)}')

        if admin.api == 0:
            data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                        'error_message': "API Access Disabled."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=403)

        wm = WebsiteManager()
        return wm.createWebsiteAPI(data)
    except Exception as msg:
        data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                    'error_message': f"Internal server error: {str(msg)}"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, status=500)


@csrf_exempt
def createDockersite(request):
    try:
        if request.method != 'POST':
            data_ret = {"status": 0, 'error_message': "Only POST method allowed."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=405)

        try:
            data = json.loads(request.body)
            adminUser = data['adminUser']
            
            # Additional security: validate critical fields for dangerous characters
            is_valid, error_msg = validate_api_input(adminUser, "adminUser")
            if not is_valid:
                data_ret = {"status": 0, 'error_message': error_msg}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=400)
                
            # Validate site name if provided
            if 'sitename' in data:
                is_valid, error_msg = validate_api_input(data['sitename'], "sitename")
                if not is_valid:
                    data_ret = {"status": 0, 'error_message': error_msg}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data, status=400)
                    
        except (json.JSONDecodeError, KeyError):
            data_ret = {"status": 0, 'error_message': "Invalid JSON or missing adminUser field."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=400)

        try:
            admin = Administrator.objects.get(userName=adminUser)
        except Administrator.DoesNotExist:
            data_ret = {"status": 0, 'error_message': "Administrator not found."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=404)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Create dockersite payload in API {str(data)}')

        if admin.api == 0:
            data_ret = {"status": 0, 'error_message': "API Access Disabled."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=403)

        wm = WebsiteManager()
        return wm.submitDockerSiteCreation(admin.pk, data)
    except Exception as msg:
        data_ret = {"status": 0, 'error_message': f"Internal server error: {str(msg)}"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, status=500)


@csrf_exempt
def getPackagesListAPI(request):
    data = json.loads(request.body)
    adminUser = data['adminUser']
    adminPass = data['adminPass']
    admin = Administrator.objects.get(userName=adminUser)
    if admin.api == 0:
        data_ret = {"existsStatus": 0, 'listPackages': [],
                    'error_message': "API Access Disabled."}
        return HttpResponse(json.dumps(data_ret))
    if hashPassword.check_password(admin.password, adminPass):
        pm = PackagesManager()
        return pm.listPackagesAPI(data)
    else:
        data_ret = {"status": 0, 'error_message': "Could not authorize access to API"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def getUserInfo(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            username = data['username']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                user = Administrator.objects.get(userName=username)
                data_ret = {'status': 1,
                            'firstName': user.firstName,
                            'lastName': user.lastName,
                            'email': user.email,
                            'adminStatus': user.acl.adminStatus,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'status': 0, 'error_message': "User does not exists."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'submitWebsiteCreation')
        data_ret = secure_error_response(e, 'Failed to create website')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def changeUserPassAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"changeStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"changeStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                websiteOwn = Administrator.objects.get(userName=websiteOwner)
            except Administrator.DoesNotExist:
                data_ret = {"changeStatus": 0,
                            'error_message': "Target account not found."}
                return HttpResponse(json.dumps(data_ret))

            if not can_change_api_account_password(admin, websiteOwn):
                data_ret = {"changeStatus": 0,
                            'error_message': "Not authorized to modify this account."}
                return HttpResponse(json.dumps(data_ret))

            websiteOwn.password = hashPassword.hash_password(ownerPassword)
            websiteOwn.save()

            data_ret = {'changeStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'changeUserPassAPI')
        data_ret = secure_error_response(e, 'Failed to change user password')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def submitUserDeletion(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                request.session['userID'] = admin.pk
                return duc(request)
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'submitUserDeletion')
        data_ret = secure_error_response(e, 'Failed to submitUserDeletion')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def changePackageAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteName = data['websiteName']
            packageName = data['packageName']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"changePackage": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"changePackage": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                website = Websites.objects.get(domain=websiteName)
            except Websites.DoesNotExist:
                data_ret = {"changePackage": 0,
                            'error_message': "Website not found."}
                return HttpResponse(json.dumps(data_ret))

            if not can_change_api_website_package(admin, website):
                data_ret = {"changePackage": 0,
                            'error_message': "Not authorized to modify this website."}
                return HttpResponse(json.dumps(data_ret))

            try:
                pack = Package.objects.get(packageName=packageName)
            except Package.DoesNotExist:
                data_ret = {"changePackage": 0,
                            'error_message': "Package not found."}
                return HttpResponse(json.dumps(data_ret))

            website.package = pack
            website.save()

            data_ret = {'changePackage': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'changePackage')
        data_ret = secure_error_response(e, 'Failed to changePackage')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def deleteWebsite(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"websiteDeleteStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data['websiteName'] = data['domainName']

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteDeleteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            website = Websites.objects.get(domain=data['websiteName'])
            websiteOwner = website.admin

            try:
                if admin.websites_set.all().count() == 0:
                    websiteOwner.delete()
            except:
                pass

            ## Deleting master domain

            wm = WebsiteManager()
            return wm.submitWebsiteDeletion(admin.pk, data)

    except Exception as e:
        secure_log_error(e, 'websiteDeleteStatus')
        data_ret = secure_error_response(e, 'Failed to websiteDeleteStatus')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def submitWebsiteStatus(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"websiteStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            wm = WebsiteManager()
            return wm.submitWebsiteStatus(admin.pk, json.loads(request.body))

    except Exception as e:
        secure_log_error(e, 'websiteStatus')
        data_ret = secure_error_response(e, 'Failed to websiteStatus')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def loginAPI(request):
    try:
        username = request.POST['username']
        password = request.POST['password']

        admin = Administrator.objects.get(userName=username)

        if admin.api == 0:
            data_ret = {"userID": 0, 'error_message': "API Access Disabled."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        if hashPassword.check_password(admin.password, password):
            request.session['userID'] = admin.pk
            return redirect(renderBase)
        else:
            return HttpResponse("Invalid Credentials.")

    except Exception as e:
        secure_log_error(e, 'loginAPI')
        data = secure_error_response(e, 'Login failed')
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def fetchSSHkey(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, password):

                pubKey = os.path.join("/root", ".ssh", 'cyberpanel.pub')
                execPath = "cat " + pubKey
                data = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {
                            'status': 1,
                            'pubKeyStatus': 1,
                            'error_message': "None",
                            'pubKey': data
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {
                            'status': 0,
                            'pubKeyStatus': 0,
                            'error_message': "Could not authorize access to API."
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data = {'status': 0, 'pubKeyStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def remoteTransfer(request):
    try:
        if request.method == "POST":

            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"transferStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ipAddress = data['ipAddress']
            accountsToTransfer = data['accountsToTransfer']
            port = data['port']

            if not is_safe_remote_host(ipAddress) or not is_safe_port(port):
                return HttpResponse(json.dumps({
                    'transferStatus': 0,
                    'error_message': 'Invalid remote host or port.'
                }))

            if hashPassword.check_password(admin.password, password):
                dir = str(randint(1000, 9999))

                ##save this port into file
                portpath = "/home/cyberpanel/remote_port"
                writeToFile = open(portpath, 'w')
                writeToFile.writelines(str(port))
                writeToFile.close()


                mailUtilities.checkHome()
                path = "/home/cyberpanel/accounts-" + str(randint(1000, 9999))
                writeToFile = open(path, 'w')

                for items in accountsToTransfer:
                    writeToFile.writelines(items + "\n")
                writeToFile.close()

                ## Accounts to transfer is a path to file, containing accounts.


                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
                execPath = execPath + " remoteTransfer --ipAddress " + ipAddress.rstrip('\n') + " --dir " + dir + " --accountsToTransfer " + path
                ProcessUtilities.popenExecutioner(execPath)

                if os.path.exists('/usr/local/CyberCP/debug'):
                    logging.writeToFile('Repor of %s' % repr(execPath))

                return HttpResponse(json.dumps({"transferStatus": 1, "dir": dir}))

                ##
            else:
                data_ret = {'transferStatus': 0, 'error_message': "Could not authorize access to API."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'transferStatus')
        data = secure_error_response(e, 'Failed to transferStatus')
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def fetchAccountsFromRemoteServer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"fetchStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, password):

                records = Websites.objects.all()

                json_data = "["
                checker = 0

                for items in records:
                    dic = {
                           'website': items.domain,
                           'php': items.phpSelection,
                           'package': items.package.packageName,
                           'email': items.adminEmail,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})

                return HttpResponse(final_json)
            else:
                data_ret = {'fetchStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'fetchStatus')
        data = secure_error_response(e, 'Failed to fetchStatus')
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def FetchRemoteTransferStatus(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"fetchStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not is_safe_numeric_id(data.get('dir', '')):
                return HttpResponse(json.dumps({
                    'fetchStatus': 0,
                    'error_message': 'Invalid transfer directory.'
                }))

            log_path = "/home/backup/transfer-" + str(data['dir']) + "/backup_log"

            try:

                if hashPassword.check_password(admin.password, password):
                    try:
                        with open(log_path, 'r') as fh:
                            status = fh.read()
                    except (OSError, IOError):
                        status = "Just started.."

                    final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "status": status})
                    return HttpResponse(final_json)
                else:
                    data_ret = {'fetchStatus': 0, 'error_message': "Invalid Credentials"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            except:
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "status": "Just started.."})
                return HttpResponse(final_json)

    except Exception as e:
        secure_log_error(e, 'fetchStatus')
        data = secure_error_response(e, 'Failed to fetchStatus')
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def cancelRemoteTransfer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"cancelStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not is_safe_numeric_id(data.get('dir', '')):
                return HttpResponse(json.dumps({
                    'cancelStatus': 0,
                    'error_message': 'Invalid transfer directory.'
                }))

            transfer_dir = "/home/backup/transfer-" + str(data['dir'])

            if hashPassword.check_password(admin.password, password):

                pid_path = transfer_dir + "/pid"

                pid_value = None
                try:
                    with open(pid_path, 'r') as fh:
                        pid_value = fh.read().strip()
                except (OSError, IOError):
                    pid_value = None

                if pid_value and is_safe_numeric_id(pid_value):
                    try:
                        import signal as _signal
                        os.kill(int(pid_value), _signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass

                try:
                    import shutil as _shutil
                    _shutil.rmtree(transfer_dir, ignore_errors=True)
                except Exception:
                    pass

                data = {'cancelStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            else:
                data_ret = {'cancelStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data = {'cancelStatus': 1, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def cyberPanelVersion(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['username']
            adminPass = data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"getVersion": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):

                Version = version.objects.get(pk=1)

                data_ret = {
                            "getVersion": 1,
                            'error_message': "none",
                            'currentVersion': Version.currentVersion,
                            'build': Version.build
                            }

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {
                            "getVersion": 0,
                            'error_message': "Could not authorize access to API."
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'getVersion')
        data_ret = secure_error_response(e, 'Failed to getVersion')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def runAWSBackups(request):
    try:
        if request.method != 'POST':
            return HttpResponse(json.dumps({'status': 0, 'error_message': 'POST required'}))

        data = json.loads(request.body)

        admin, auth_error = get_api_admin(request, data, allow_token=False)
        if auth_error:
            return api_auth_response(auth_error, 'status')

        randomFile = data.get('randomFile', '')
        if randomFile and os.path.exists(randomFile):
            s3 = S3Backups(request, None, 'runAWSBackups')
            s3.start()

        return HttpResponse(json.dumps({'status': 1}))
    except Exception as e:
        secure_log_error(e, 'API.runAWSBackups')
        logging.writeToFile('Failed to API.runAWSBackups [API.runAWSBackups]')
        return HttpResponse(json.dumps({'status': 0, 'error_message': 'Request failed'}))


@csrf_exempt
def submitUserCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                request.session['userID'] = admin.pk
                return suc(request)
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'changeStatus')
        data_ret = secure_error_response(e, 'Failed to changeStatus')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def listChildDomainsJson(request):
    try:
        if request.method != 'POST':
            data_ret = {"status": 0, 'error_message': "Only POST method allowed."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=405)

        try:
            data = json.loads(request.body)
            adminUser = data['adminUser']
            adminPass = data['adminPass']
            
            # Additional security: validate critical fields for dangerous characters
            is_valid, error_msg = validate_api_input(adminUser, "adminUser")
            if not is_valid:
                data_ret = {"status": 0, 'error_message': error_msg}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data, status=400)
                
        except (json.JSONDecodeError, KeyError):
            data_ret = {"status": 0, 'error_message': "Invalid JSON or missing adminUser/adminPass fields."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=400)

        try:
            admin = Administrator.objects.get(userName=adminUser)
        except Administrator.DoesNotExist:
            data_ret = {"status": 0, 'error_message': "Administrator not found."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=404)

        if admin.api == 0:
            data_ret = {"status": 0, 'error_message': "API Access Disabled."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=403)

        if not hashPassword.check_password(admin.password, adminPass):
            data_ret = {"status": 0, 'error_message': "Invalid password."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data, status=401)

        # Get child domains
        from websiteFunctions.models import ChildDomains
        
        child_domains = ChildDomains.objects.all()
        
        # Get machine IP
        try:
            ipFile = "/etc/cyberpanel/machineIP"
            with open(ipFile, 'r') as f:
                ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.writeToFile(f"Failed to read machine IP, error: {str(msg)}")
            ipAddress = "192.168.100.1"

        json_data = []
        for items in child_domains:
            dic = {
                'parent_site': items.master.domain,
                'domain': items.domain,
                'path': items.path,
                'ssl': items.ssl,
                'php_version': items.phpSelection,
                'ip_address': ipAddress
            }
            json_data.append(dic)

        final_json = json.dumps(json_data, indent=2)
        return HttpResponse(final_json, content_type='application/json')

    except Exception as msg:
        data_ret = {'status': 0, 'error_message': f"Internal server error: {str(msg)}"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, status=500)


@csrf_exempt
def addFirewallRule(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                from firewall.firewallManager import FirewallManager

                fm = FirewallManager()
                return fm.addRule(admin.pk, json.loads(request.body))
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'submitUserDeletion')
        data_ret = secure_error_response(e, 'Failed to submitUserDeletion')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def deleteFirewallRule(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                from firewall.firewallManager import FirewallManager

                fm = FirewallManager()
                return fm.deleteRule(admin.pk, json.loads(request.body))
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except Exception as e:
        secure_log_error(e, 'submitUserDeletion')
        data_ret = secure_error_response(e, 'Failed to submitUserDeletion')
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


# AI Scanner API endpoints for external workers
@csrf_exempt
def aiScannerAuthenticate(request):
    """AI Scanner worker authentication endpoint"""
    try:
        from aiScanner.api import authenticate_worker
        return authenticate_worker(request)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner authenticate error: {str(e)}')
        data_ret = {'error': 'Authentication service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def aiScannerListFiles(request):
    """AI Scanner file listing endpoint"""
    try:
        from aiScanner.api import list_files
        return list_files(request)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner list files error: {str(e)}')
        data_ret = {'error': 'File listing service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def aiScannerGetFileContent(request):
    """AI Scanner file content endpoint"""
    try:
        from aiScanner.api import get_file_content
        return get_file_content(request)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner get file content error: {str(e)}')
        data_ret = {'error': 'File content service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def aiScannerCallback(request):
    """AI Scanner scan completion callback endpoint"""
    try:
        from aiScanner.api import scan_callback
        return scan_callback(request)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner callback error: {str(e)}')
        data_ret = {'error': 'Callback service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


# Real-time monitoring API endpoints
@csrf_exempt
def aiScannerStatusWebhook(request):
    """AI Scanner real-time status webhook endpoint"""
    try:
        from aiScanner.status_api import receive_status_update
        return receive_status_update(request)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner status webhook error: {str(e)}')
        data_ret = {'error': 'Status webhook service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


def aiScannerLiveProgress(request, scan_id):
    """AI Scanner live progress endpoint"""
    try:
        from aiScanner.status_api import get_live_scan_progress
        return get_live_scan_progress(request, scan_id)
    except Exception as e:
        logging.writeToFile(f'[API] AI Scanner live progress error: {str(e)}')
        data_ret = {'error': 'Live progress service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


# AI Scanner File Operation endpoints
@csrf_exempt
def scannerBackupFile(request):
    """Scanner backup file endpoint"""
    try:
        from aiScanner.api import scanner_backup_file
        return scanner_backup_file(request)
    except Exception as e:
        logging.writeToFile(f'[API] Scanner backup file error: {str(e)}')
        data_ret = {'error': 'Backup file service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def scannerGetFile(request):
    """Scanner get file endpoint"""
    try:
        from aiScanner.api import scanner_get_file
        return scanner_get_file(request)
    except Exception as e:
        logging.writeToFile(f'[API] Scanner get file error: {str(e)}')
        data_ret = {'error': 'Get file service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def scannerReplaceFile(request):
    """Scanner replace file endpoint"""
    try:
        from aiScanner.api import scanner_replace_file
        return scanner_replace_file(request)
    except Exception as e:
        logging.writeToFile(f'[API] Scanner replace file error: {str(e)}')
        data_ret = {'error': 'Replace file service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def scannerRenameFile(request):
    """Scanner rename file endpoint"""
    try:
        from aiScanner.api import scanner_rename_file
        return scanner_rename_file(request)
    except Exception as e:
        logging.writeToFile(f'[API] Scanner rename file error: {str(e)}')
        data_ret = {'error': 'Rename file service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)


@csrf_exempt
def scannerDeleteFile(request):
    """Scanner delete file endpoint"""
    try:
        from aiScanner.api import scanner_delete_file
        return scanner_delete_file(request)
    except Exception as e:
        logging.writeToFile(f'[API] Scanner delete file error: {str(e)}')
        data_ret = {'error': 'Delete file service unavailable'}
        return HttpResponse(json.dumps(data_ret), status=500)

