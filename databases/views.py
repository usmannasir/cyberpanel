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
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = Websites.objects.filter(admin=admin)
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = Websites.objects.filter(admin=items)

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)


            return render(request, 'databases/createDatabase.html', {'websitesList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def submitDBCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                databaseWebsite = data['databaseWebsite']
                dbName = data['dbName']
                dbUsername = data['dbUsername']
                dbPassword = data['dbPassword']

                webUsername = databaseWebsite.replace("-","")


                webUsername = webUsername.split('.')[0]

                dbName = webUsername+"_"+dbName
                dbUsername = webUsername+"_"+dbUsername

                if len(dbName) > 16 or len(dbUsername) > 16:
                    data_ret = {'createDBStatus': 0,
                                'error_message': "Length of Database name or Database user should be 16 at max."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                website = Websites.objects.get(domain=databaseWebsite)

                if website.package.dataBases == 0:
                    pass
                elif website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    data_ret = {'createDBStatus': 0, 'error_message': "Maximum database limit reached for this website."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(dbUser=dbUsername).exists() :
                    data_ret = {'createDBStatus': 0,
                                'error_message': "This database or user is already taken."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                result = mysqlUtilities.createDatabase(dbName, dbUsername, dbPassword)

                if result == 1:
                    pass
                else:
                    data_ret = {'createDBStatus': 0,
                                'error_message': result}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                db = Databases(website=website,dbName=dbName,dbUser=dbUsername)
                db.save()

                data_ret = {'createDBStatus': 1, 'error_message': "None"}
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
        val = request.session['userID']
        try:

            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)


            return render(request, 'databases/deleteDatabase.html', {'websitesList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def fetchDatabases(request):
    try:
        val = request.session['userID']
        try:

            data = json.loads(request.body)

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
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                dbName = data['dbName']


                databaseToBeDeleted = Databases.objects.get(dbName=dbName)
                result = mysqlUtilities.deleteDatabase(dbName,databaseToBeDeleted.dbUser)

                if  result == 1:
                    data_ret = {'deleteStatus': 1, 'error_message': "None"}
                    databaseToBeDeleted.delete()
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'deleteStatus': 0, 'error_message': result}
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
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'databases/listDataBases.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def changePassword(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':



                data = json.loads(request.body)
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