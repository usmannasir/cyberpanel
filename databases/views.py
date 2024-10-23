# -*- coding: utf-8 -*-
import time
from random import randint

from django.shortcuts import redirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from cloudAPI.cloudManager import CloudManager
from loginSystem.views import loadLoginPage
from .databaseManager import DatabaseManager
from .mysqlOptimizer import MySQLOptimizer
from .pluginManager import pluginManager
import json
from plogical.processUtilities import ProcessUtilities
from loginSystem.models import Administrator
from plogical.acl import ACLManager
from databases.models import GlobalUserDB
from plogical import randomPassword
from cryptography.fernet import Fernet
from plogical.mysqlUtilities import mysqlUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


# Create your views here.

def loadDatabaseHome(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.loadDatabaseHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def createDatabase(request):
    try:
        result = pluginManager.preCreateDatabase(request)
        if result != 200:
            return result

        userID = request.session['userID']
        dm = DatabaseManager()
        coreResult = dm.createDatabase(request, userID)

        result = pluginManager.postCreateDatabase(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def submitDBCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSubmitDBCreation(request)
        if result != 200:
            return result

        dm = DatabaseManager()
        coreResult = dm.submitDBCreation(userID, json.loads(request.body))

        result = pluginManager.postSubmitDBCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def deleteDatabase(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.deleteDatabase(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def fetchDatabases(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.fetchDatabases(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def submitDatabaseDeletion(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preSubmitDatabaseDeletion(request)
        if result != 200:
            return result

        dm = DatabaseManager()
        coreResult = dm.submitDatabaseDeletion(userID, json.loads(request.body))

        result = pluginManager.postSubmitDatabaseDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def listDBs(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.listDBs(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def changePassword(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preChangePassword(request)
        if result != 200:
            return result

        dm = DatabaseManager()
        coreResult = dm.changePassword(userID, json.loads(request.body))

        result = pluginManager.postChangePassword(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def remoteAccess(request):
    try:
        userID = request.session['userID']

        dm = DatabaseManager()
        coreResult = dm.remoteAccess(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def allowRemoteIP(request):
    try:
        userID = request.session['userID']

        dm = DatabaseManager()
        coreResult = dm.allowRemoteIP(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def phpMyAdmin(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.phpMyAdmin(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def generateAccess(request):
    try:

        userID = request.session['userID']
        admin = Administrator.objects.get(id=userID)
        currentACL = ACLManager.loadedACL(userID)

        ## if user ACL is admin login as root

        command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
        ProcessUtilities.executioner(command)

        if currentACL['admin'] == 1:

            try:
                GlobalUserDB.objects.get(username=admin.userName).delete()
            except:
                try:
                    gbobs = GlobalUserDB.objects.filter(username=admin.userName)
                    for gbobs in gbobs:
                        gbobs.delete()
                except:
                    pass

            password = randomPassword.generate_pass()
            token = randomPassword.generate_pass()
            GlobalUserDB(username=admin.userName, password=password, token=token).save()

            data_ret = {'status': 1, 'token': token, 'username': admin.userName}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        keySavePath = '/home/cyberpanel/phpmyadmin_%s' % (admin.userName)
        try:
            GlobalUserDB.objects.get(username=admin.userName).delete()
        except:
            pass

        command = 'rm -f %s' % (keySavePath)
        ProcessUtilities.executioner(command)

        ## Create and save new key

        key = Fernet.generate_key()

        writeToFile = open(keySavePath, 'w')
        writeToFile.write(key.decode())
        writeToFile.close()

        command = 'chown root:root %s' % (keySavePath)
        ProcessUtilities.executioner(command)

        command = 'chmod 600 %s' % (keySavePath)
        ProcessUtilities.executioner(command)

        ##

        password = randomPassword.generate_pass()
        token = randomPassword.generate_pass()
        f = Fernet(key)
        GlobalUserDB(username=admin.userName, password=f.encrypt(password.encode('utf-8')).decode(),
                     token=token).save()

        sites = ACLManager.findWebsiteObjects(currentACL, userID)
        mysqlUtilities.addUserToDB(None, admin.userName, password, 1)

        for site in sites:
            for db in site.databases_set.all():
                mysqlUtilities.addUserToDB(db.dbName, admin.userName, password, 0)

        data_ret = {'status': 1, 'token': token, 'username': admin.userName}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


    except BaseException as msg:
        logging.writeToFile(str(msg))
        data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


@csrf_exempt
def fetchDetailsPHPMYAdmin(request):
    try:

        userID = request.session['userID']
        admin = Administrator.objects.get(id=userID)
        currentACL = ACLManager.loadedACL(userID)

        token = request.POST.get('token')
        username = request.POST.get('username')

        from plogical.httpProc import httpProc
        proc = httpProc(request, None,
                        )
        # return proc.ajax(0, str(request.POST.get('token')))

        if username != admin.userName:
            return redirect(loadLoginPage)

        ## Key generation

        gdb = GlobalUserDB.objects.get(username=admin.userName)

        if gdb.token == token:

            if currentACL['admin'] == 1:
                passFile = "/etc/cyberpanel/mysqlPassword"

                try:
                    jsonData = json.loads(open(passFile, 'r').read())

                    mysqluser = jsonData['mysqluser']
                    password = jsonData['mysqlpassword']

                    # returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (
                    #     mysqluser, password)
                    # return redirect(returnURL)
                    data = {}
                    data['userName'] = mysqluser
                    data['password'] = password

                    proc = httpProc(request, 'databases/AutoLogin.html',
                                    data, 'admin')
                    return proc.render()

                except BaseException as msg:

                    f = open(passFile)
                    data = f.read()
                    password = data.split('\n', 1)[0]
                    password = password.strip('\n').strip('\r')

                    data = {}
                    data['userName'] = 'root'
                    data['password'] = password
                    # return redirect(returnURL)

                    proc = httpProc(request, 'databases/AutoLogin.html',
                                    data, 'admin')
                    return proc.render()

                    # returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (
                    #     'root', password)
                    # return redirect(returnURL)

            keySavePath = '/home/cyberpanel/phpmyadmin_%s' % (admin.userName)
            key = ProcessUtilities.outputExecutioner('cat %s' % (keySavePath)).strip('\n').encode()
            f = Fernet(key)
            password = f.decrypt(gdb.password.encode('utf-8'))

            sites = ACLManager.findWebsiteObjects(currentACL, userID)

            for site in sites:
                for db in site.databases_set.all():
                    mysqlUtilities.addUserToDB(db.dbName, admin.userName, password.decode(), 0)

            data = {}
            data['userName'] = admin.userName
            data['password'] = password.decode()
            # return redirect(returnURL)

            proc = httpProc(request, 'databases/AutoLogin.html',
                            data, 'listDatabases')
            return proc.render()

            # returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (admin.userName, password.decode())
            # return redirect(returnURL)
        else:
            return redirect(loadLoginPage)


    except BaseException as msg:
        data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def MySQLManager(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.MySQLManager(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def OptimizeMySQL(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.OptimizeMySQL(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def UpgradeMySQL(request):
    try:
        userID = request.session['userID']
        dm = DatabaseManager()
        return dm.Upgardemysql(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def getMysqlstatus(request):
    try:
        userID = request.session['userID']
        finalData = mysqlUtilities.showStatus()

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        finalData = json.dumps(finalData)
        return HttpResponse(finalData)

    except KeyError:
        return redirect(loadLoginPage)


def restartMySQL(request):
    try:
        userID = request.session['userID']
        finalData = mysqlUtilities.restartMySQL()
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = {}

        data['status'] = finalData[0]
        data['error_message'] = finalData[1]
        json_data = json.dumps(data)
        return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)


def generateRecommendations(request):
    try:
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        detectedRam = data['detectedRam']

        data = {}
        data['status'] = 1
        data['generatedConf'] = MySQLOptimizer.generateRecommendations(detectedRam)

        final_json = json.dumps(data)
        return HttpResponse(final_json)

    except KeyError:
        return redirect(loadLoginPage)


def applyMySQLChanges(request):
    try:

        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        finalData = mysqlUtilities.applyMySQLChanges(data)

        data = {}

        data['status'] = finalData[0]
        data['error_message'] = finalData[1]

        final_json = json.dumps(data)
        return HttpResponse(final_json)

    except KeyError:
        return redirect(loadLoginPage)


def upgrademysqlnow(request):
    try:
        from plogical.virtualHostUtilities import virtualHostUtilities
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        version =data['mysqlversion']
        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))



        execPath = f"/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mysqlUtilities.py UpgradeMariaDB --version {version} --tempStatusPath {tempStatusPath}"
        ProcessUtilities.popenExecutioner(execPath)
        time.sleep(2)

        data_ret = {'status': 1, 'error_message': "None",
                    'tempStatusPath': tempStatusPath}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)


def upgrademysqlstatus(request):
    try:

        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        statusfile = data['statusfile']
        installStatus = ProcessUtilities.outputExecutioner("sudo cat " + statusfile)

        if installStatus.find("[200]") > -1:

            command = 'sudo rm -f ' + statusfile
            ProcessUtilities.executioner(command)

            final_json = json.dumps({
                'error_message': "None",
                'requestStatus': installStatus,
                'abort': 1,
                'installed': 1,
            })
            return HttpResponse(final_json)
        elif installStatus.find("[404]") > -1:
            command = 'sudo rm -f ' + statusfile
            ProcessUtilities.executioner(command)
            final_json = json.dumps({
                'abort': 1,
                'installed': 0,
                'error_message': "None",
                'requestStatus': installStatus,
            })
            return HttpResponse(final_json)

        else:
            final_json = json.dumps({
                'abort': 0,
                'error_message': "None",
                'requestStatus': installStatus,
            })
            return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)
