# -*- coding: utf-8 -*-

import json
import shlex
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
from django.views.decorators.csrf import csrf_exempt
from userManagment.views import submitUserCreation as suc
from userManagment.views import submitUserDeletion as duc
from plogical.acl import ACLManager
from plogical.securityUtils import (
    api_token_matches,
    get_remote_transfer_dir_path,
    get_remote_transfer_log_path,
    get_remote_transfer_pid_path,
    is_safe_numeric_id,
    is_safe_port,
    is_safe_remote_host,
)
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


def can_change_api_account_password(admin, target_admin):
    if admin.pk == target_admin.pk:
        return True

    try:
        current_acl = ACLManager.loadedACL(admin.pk)
        return current_acl.get('admin', 0) == 1
    except:
        return False


def can_change_api_website_package(admin, website, package):
    try:
        current_acl = ACLManager.loadedACL(admin.pk)
        if ACLManager.currentContextPermission(current_acl, 'modifyWebsite') != 1:
            return False
        if ACLManager.checkOwnership(website.domain, admin, current_acl) != 1:
            return False
        if ACLManager.CheckPackageOwnership(package, admin, current_acl) != 1:
            return False
        return True
    except:
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

        admin, auth_error = get_api_admin(request, data, allow_token=False)
        if auth_error:
            error_message = json.loads(auth_error.content.decode()).get('error_message')
            data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                        'error_message': error_message}
            status_code = 403 if auth_error.status_code == 403 else 200
            return HttpResponse(json.dumps(data_ret), status=status_code)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Create website payload in API {str(data)}')

        wm = WebsiteManager()
        return wm.createWebsiteAPI(data)
    except Exception as msg:
        data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                    'error_message': f"Internal server error: {str(msg)}"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, status=500)


@csrf_exempt
def getPackagesListAPI(request):
    data = json.loads(request.body)
    admin, auth_error = get_api_admin(request, data)
    if auth_error:
        return api_auth_response(auth_error, 'existsStatus', {'status': 0, 'listPackages': []})

    pm = PackagesManager()
    return pm.listPackagesAPI(data)

@csrf_exempt
def getUserInfo(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            username = data['username']

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

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

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def changeUserPassAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'changeStatus')

            websiteOwn = Administrator.objects.get(userName=websiteOwner)
            if not can_change_api_account_password(admin, websiteOwn):
                data_ret = {'changeStatus': 0,
                            'error_message': 'Not authorized to modify this account.'}
                return HttpResponse(json.dumps(data_ret))

            websiteOwn.password = hashPassword.hash_password(ownerPassword)
            websiteOwn.save()

            data_ret = {'changeStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'changeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def submitUserDeletion(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

            request.session['userID'] = admin.pk
            return duc(request)

    except BaseException as msg:
        data_ret = {'submitUserDeletion': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def changePackageAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteName = data['websiteName']
            packageName = data['packageName']
            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'changePackage')

            website = Websites.objects.get(domain=websiteName)
            pack = Package.objects.get(packageName=packageName)

            if not can_change_api_website_package(admin, website, pack):
                return ACLManager.loadErrorJson('changePackage', 0)

            website.package = pack
            website.save()

            data_ret = {'changePackage': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'changePackage': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def deleteWebsite(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)

            data['websiteName'] = data['domainName']

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'websiteDeleteStatus')

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

    except BaseException as msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def submitWebsiteStatus(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'websiteStatus')

            wm = WebsiteManager()
            return wm.submitWebsiteStatus(admin.pk, json.loads(request.body))

    except BaseException as msg:
        data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
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

    except BaseException as msg:
        data = {'userID': 0, 'loginStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def fetchSSHkey(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'status', {'pubKeyStatus': 0})

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

    except BaseException as msg:
        data = {'status': 0, 'pubKeyStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def remoteTransfer(request):
    try:
        if request.method == "POST":

            data = json.loads(request.body)
            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'transferStatus')

            ipAddress = data['ipAddress']
            accountsToTransfer = data['accountsToTransfer']
            port = data['port']

            if not is_safe_remote_host(ipAddress) or not is_safe_port(port):
                return HttpResponse(json.dumps({'transferStatus': 0, 'error_message': 'Invalid remote host or port.'}))

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

    except BaseException as msg:
        data = {'transferStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def fetchAccountsFromRemoteServer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'fetchStatus')

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

    except BaseException as msg:
        data = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def FetchRemoteTransferStatus(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'fetchStatus')

            log_path = get_remote_transfer_log_path(data.get('dir'))
            if not log_path:
                return HttpResponse(json.dumps({'fetchStatus': 0, 'error_message': 'Invalid transfer directory.'}))

            # The transfer directory is created chmod 600 and owned by root by the
            # backup process, so a non-root web process cannot open() the log
            # directly (PermissionError) -- doing so leaves the UI stuck on
            # "Just started.." forever. Read it through the privileged executioner
            # instead. log_path is already validated (numeric dir under /home/backup)
            # and quoted for defence in depth.
            status = ProcessUtilities.outputExecutioner("cat " + shlex.quote(log_path))

            if not status or "No such file or directory" in status:
                status = "Just started.."

            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "status": status})
            return HttpResponse(final_json)

    except BaseException as msg:
        data = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


@csrf_exempt
def cancelRemoteTransfer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'cancelStatus')

            transfer_path = get_remote_transfer_dir_path(data.get('dir'))
            pid_path = get_remote_transfer_pid_path(data.get('dir'))
            if not transfer_path or not pid_path:
                return HttpResponse(json.dumps({'cancelStatus': 0, 'error_message': 'Invalid transfer directory.'}))

            # pid file and transfer directory are root-owned, so read/kill/remove
            # through the privileged executioner rather than acting as the (possibly
            # non-root) web process. Both paths are already validated; pid is
            # re-checked as numeric before being placed on a command line.
            pid = ProcessUtilities.outputExecutioner("cat " + shlex.quote(pid_path))
            pid = pid.strip() if pid else ""

            if not is_safe_numeric_id(pid):
                return HttpResponse(json.dumps({'cancelStatus': 0, 'error_message': 'Invalid transfer process.'}))

            ProcessUtilities.executioner("kill -KILL " + pid)
            ProcessUtilities.executioner("rm -rf " + shlex.quote(transfer_path))

            data = {'cancelStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data)
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

            admin, auth_error = get_api_admin(request, data, 'username', 'password')
            if auth_error:
                return api_auth_response(auth_error, 'getVersion')

            Version = version.objects.get(pk=1)

            data_ret = {
                        "getVersion": 1,
                        'error_message': "none",
                        'currentVersion': Version.currentVersion,
                        'build': Version.build
                        }

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {
                    "getVersion": 0,
                    'error_message': str(msg)
                    }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def runAWSBackups(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

            randomFile = data['randomFile']

            if os.path.exists(randomFile):
                s3 = S3Backups(request, None, 'runAWSBackups')
                s3.start()

            return HttpResponse(json.dumps({'status': 1}))
    except BaseException as msg:
        logging.writeToFile(str(msg) + ' [API.runAWSBackups]')
        return HttpResponse(json.dumps({'status': 0, 'error_message': str(msg)}))


@csrf_exempt
def submitUserCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

            request.session['userID'] = admin.pk
            return suc(request)

    except BaseException as msg:
        data_ret = {'changeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def addFirewallRule(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

            from firewall.firewallManager import FirewallManager

            fm = FirewallManager()
            return fm.addRule(admin.pk, json.loads(request.body))

    except BaseException as msg:
        data_ret = {'submitUserDeletion': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def deleteFirewallRule(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            admin, auth_error = get_api_admin(request, data, allow_token=False)
            if auth_error:
                return api_auth_response(auth_error, 'status')

            from firewall.firewallManager import FirewallManager

            fm = FirewallManager()
            return fm.deleteRule(admin.pk, json.loads(request.body))

    except BaseException as msg:
        data_ret = {'submitUserDeletion': 0, 'error_message': str(msg)}
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
