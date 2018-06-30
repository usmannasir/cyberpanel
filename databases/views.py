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
            admin = Administrator.objects.get(pk=val)

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
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                databaseWebsite = data['databaseWebsite']
                dbName = data['dbName']
                dbUsername = data['dbUsername']
                dbPassword = data['dbPassword']
                webUsername = data['webUserName']

                if admin.type != 1:
                    website = Websites.objects.get(domain=databaseWebsite)
                    if website.admin != admin:
                        dic = {'createDBStatus': 0, 'error_message': "Only administrator can view this page."}
                        json_data = json.dumps(dic)
                        return HttpResponse(json_data)

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
        val = request.session['userID']
        try:

            admin = Administrator.objects.get(pk=val)

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
        admin = Administrator.objects.get(pk=val)
        try:

            data = json.loads(request.body)

            databaseWebsite = data['databaseWebsite']

            if admin.type != 1:
                website = Websites.objects.get(domain=databaseWebsite)
                if website.admin != admin:
                    dic = {'fetchStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

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
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                dbName = data['dbName']

                if admin.type != 1:
                    db = Databases.objects.get(dbName=dbName)
                    if db.website.admin != admin:
                        dic = {'deleteStatus': 0, 'error_message': "Only administrator can view this page."}
                        json_data = json.dumps(dic)
                        return HttpResponse(json_data)

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
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

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
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                userName = data['dbUserName']
                dbPassword = data['dbPassword']

                if admin.type != 1:
                    db = Databases.objects.get(dbName=userName)
                    if db.website.admin != admin:
                        dic = {'changePasswordStatus': 0, 'error_message': "Only administrator can view this page."}
                        json_data = json.dumps(dic)
                        return HttpResponse(json_data)

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