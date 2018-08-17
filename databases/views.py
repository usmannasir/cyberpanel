# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
import plogical.CyberCPLogFileWriter as logging
from plogical.mysqlUtilities import mysqlUtilities
from loginSystem.views import loadLoginPage
from models import Databases
import json
import shlex
import subprocess
from plogical.acl import ACLManager
# Create your views here.


def loadDatabaseHome(request):
    try:
        val = request.session['userID']
        try:
            return render(request, 'databases/index.html')
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def createDatabase(request):
    try:
        userID = request.session['userID']
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['createDatabase'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/createDatabase.html', {'websitesList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def submitDBCreation(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                databaseWebsite = data['databaseWebsite']
                dbName = data['dbName']
                dbUsername = data['dbUsername']
                dbPassword = data['dbPassword']
                webUsername = data['webUserName']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['createDatabase'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('createDBStatus', 0)

                dbName = webUsername+"_"+dbName
                dbUsername = webUsername+"_"+dbUsername

                result = mysqlUtilities.submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite)

                if result[0] == 1:
                    data_ret = {'createDBStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'createDBStatus': 0, 'error_message': result[1]}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'createDBStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'createDBStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def deleteDatabase(request):
    try:
        userID = request.session['userID']
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['deleteDatabase'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/deleteDatabase.html', {'websitesList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def fetchDatabases(request):
    try:
        userID = request.session['userID']
        try:
            data = json.loads(request.body)
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['deleteDatabase'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            databaseWebsite = data['databaseWebsite']

            website = Websites.objects.get(domain=databaseWebsite)
            databases = Databases.objects.filter(website=website)

            json_data = "["
            checker = 0

            for items in databases:
                dic = { 'id':items.pk,
                        'dbName': items.dbName,
                       'dbUser': items.dbUser,}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})

            return HttpResponse(final_json)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            final_json = json.dumps({'fetchStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    except KeyError:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        final_json = json.dumps({'fetchStatus': 0, 'error_message': "Not logged in."})
        return HttpResponse(final_json)

def submitDatabaseDeletion(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                dbName = data['dbName']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['deleteDatabase'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('deleteStatus', 0)

                result = mysqlUtilities.submitDBDeletion(dbName)

                if  result[0] == 1:
                    data_ret = {'deleteStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'deleteStatus': 0, 'error_message': result[1]}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


        except BaseException,msg:
            data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def listDBs(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['listDatabases'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/listDataBases.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def changePassword(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                userName = data['dbUserName']
                dbPassword = data['dbPassword']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['listDatabases'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('changePasswordStatus', 0)

                passFile = "/etc/cyberpanel/mysqlPassword"

                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]


                passwordCMD = "use mysql;SET PASSWORD FOR '" + userName + "'@'localhost' = PASSWORD('" + dbPassword + "');FLUSH PRIVILEGES;"

                command = 'sudo mysql -u root -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    data_ret = {'changePasswordStatus': 0, 'error_message': "Please see CyberPanel main log file."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


                data_ret = {'changePasswordStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'changePasswordStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
