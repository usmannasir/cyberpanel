# -*- coding: utf-8 -*-


from django.shortcuts import redirect, HttpResponse
from loginSystem.views import loadLoginPage
from .databaseManager import DatabaseManager
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
        admin = Administrator.objects.get(id = userID)
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
            GlobalUserDB(username=admin.userName, password=password,token=token).save()

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

def fetchDetailsPHPMYAdmin(request):
    try:


        userID = request.session['userID']
        admin = Administrator.objects.get(id = userID)
        currentACL = ACLManager.loadedACL(userID)

        token = request.GET.get('token')
        username = request.GET.get('username')


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

                    returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (
                    mysqluser, password)
                    return redirect(returnURL)

                except BaseException:

                    f = open(passFile)
                    data = f.read()
                    password = data.split('\n', 1)[0]
                    password = password.strip('\n').strip('\r')

                    returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (
                        'root', password)
                    return redirect(returnURL)

            keySavePath = '/home/cyberpanel/phpmyadmin_%s' % (admin.userName)
            key = ProcessUtilities.outputExecutioner('cat %s' % (keySavePath)).strip('\n').encode()
            f = Fernet(key)
            password = f.decrypt(gdb.password.encode('utf-8'))

            sites = ACLManager.findWebsiteObjects(currentACL, userID)

            for site in sites:
                for db in site.databases_set.all():
                    mysqlUtilities.addUserToDB(db.dbName, admin.userName, password.decode(), 0)

            returnURL = '/phpmyadmin/phpmyadminsignin.php?username=%s&password=%s' % (admin.userName, password.decode())
            return redirect(returnURL)
        else:
            return redirect(loadLoginPage)


    except BaseException as msg:
        data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)