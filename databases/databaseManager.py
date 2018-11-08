#!/usr/local/CyberCP/bin/python2
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.shortcuts import render, redirect
from django.http import HttpResponse
import json
from plogical.acl import ACLManager
import subprocess, shlex
import plogical.CyberCPLogFileWriter as logging
from plogical.mysqlUtilities import mysqlUtilities
from websiteFunctions.models import Websites
from databases.models import Databases

class DatabaseManager:

    def loadDatabaseHome(self, request = None, userID = None):
        try:
            return render(request, 'databases/index.html')
        except BaseException, msg:
            return HttpResponse(str(msg))

    def createDatabase(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createDatabase') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/createDatabase.html', {'websitesList': websitesName})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def submitDBCreation(self, userID = None, data = None, rAPI = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createDatabase') == 0:
                return ACLManager.loadErrorJson('createDBStatus', 0)

            databaseWebsite = data['databaseWebsite']
            dbName = data['dbName']
            dbUsername = data['dbUsername']
            dbPassword = data['dbPassword']
            webUsername = data['webUserName']

            if rAPI == None:
                dbName = webUsername + "_" + dbName
                dbUsername = webUsername + "_" + dbUsername

            result = mysqlUtilities.submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite)

            if result[0] == 1:
                data_ret = {'status': 1, 'createDBStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        except BaseException, msg:
            data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteDatabase(self, request = None, userID = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteDatabase') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/deleteDatabase.html', {'websitesList': websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    def fetchDatabases(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteDatabase') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            databaseWebsite = data['databaseWebsite']

            website = Websites.objects.get(domain=databaseWebsite)
            databases = Databases.objects.filter(website=website)

            json_data = "["
            checker = 0

            for items in databases:
                dic = {'id': items.pk,
                       'dbName': items.dbName,
                       'dbUser': items.dbUser, }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})

            return HttpResponse(final_json)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def submitDatabaseDeletion(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteDatabase') == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            dbName = data['dbName']

            result = mysqlUtilities.submitDBDeletion(dbName)

            if result[0] == 1:
                data_ret = {'status': 1, 'deleteStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def listDBs(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'listDatabases') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'databases/listDataBases.html', {'websiteList': websitesName})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def changePassword(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listDatabases') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            userName = data['dbUserName']
            dbPassword = data['dbPassword']

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            passwordCMD = "use mysql;SET PASSWORD FOR '" + userName + "'@'localhost' = PASSWORD('" + dbPassword + "');FLUSH PRIVILEGES;"

            command = 'sudo mysql -u root -p' + password + ' -e "' + passwordCMD + '"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                data_ret = {'status': 0, 'changePasswordStatus': 0,'error_message': "Please see CyberPanel main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'status': 1, 'changePasswordStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)