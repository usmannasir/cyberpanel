#!/usr/local/CyberCP/bin/python2
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from django.shortcuts import render,redirect
from django.http import HttpResponse
from models import Users
from loginSystem.models import Administrator
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites
import subprocess
from plogical.virtualHostUtilities import virtualHostUtilities
import shlex
from plogical.ftpUtilities import FTPUtilities
import os
from plogical.acl import ACLManager

class FTPManager:
    def __init__(self, request):
        self.request = request

    def loadFTPHome(self):
        try:
            val = self.request.session['userID']
            return render(self.request, 'ftp/index.html')
        except KeyError:
            return redirect(loadLoginPage)

    def createFTPAccount(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createFTPAccount') == 0:
                return ACLManager.loadError()

            admin = Administrator.objects.get(pk=userID)

            if not os.path.exists('/home/cyberpanel/pureftpd'):
                return render(self.request, "ftp/createFTPAccount.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(self.request, 'ftp/createFTPAccount.html',
                          {'websiteList': websitesName, 'admin': admin.userName, "status": 1})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    def submitFTPCreation(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createFTPAccount') == 0:
                return ACLManager.loadErrorJson('creatFTPStatus', 0)

            data = json.loads(self.request.body)
            userName = data['ftpUserName']
            password = data['ftpPassword']

            domainName = data['ftpDomain']

            try:
                api = data['api']
            except:
                api = '0'

            admin = Administrator.objects.get(id=userID)

            try:
                path = data['path']
                if len(path) > 0:
                    pass
                else:
                    path = 'None'
            except:
                path = 'None'

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/ftpUtilities.py"
            execPath = execPath + " submitFTPCreation --domainName " + domainName + " --userName " + userName \
                       + " --password " + password + " --path " + path + " --owner " + admin.userName  + ' --api ' + api
            output = subprocess.check_output(shlex.split(execPath))
            if output.find("1,None") > -1:
                data_ret = {'status': 1, 'creatFTPStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'creatFTPStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'creatFTPStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteFTPAccount(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteFTPAccount') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/pureftpd'):
                return render(self.request, "ftp/deleteFTPAccount.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(self.request, 'ftp/deleteFTPAccount.html', {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    def fetchFTPAccounts(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteFTPAccount') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            domain = data['ftpDomain']

            website = Websites.objects.get(domain=domain)

            ftpAccounts = website.users_set.all()

            json_data = "["
            checker = 0

            for items in ftpAccounts:
                dic = {"userName": items.user}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException, msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitFTPDelete(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteFTPAccount') == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            data = json.loads(self.request.body)
            ftpUserName = data['ftpUsername']

            FTPUtilities.submitFTPDeletion(ftpUserName)

            final_json = json.dumps({'status': 1, 'deleteStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def listFTPAccounts(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listFTPAccounts') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/pureftpd'):
                return render(self.request, "ftp/listFTPAccounts.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(self.request, 'ftp/listFTPAccounts.html', {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    def getAllFTPAccounts(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listFTPAccounts') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            selectedDomain = data['selectedDomain']

            domain = Websites.objects.get(domain=selectedDomain)

            records = Users.objects.filter(domain=domain)

            json_data = "["
            checker = 0

            for items in records:
                dic = {'id': items.id,
                       'user': items.user,
                       'dir': items.dir,
                       'quotasize': str(items.quotasize) + "MB",
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def changePassword(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listFTPAccounts') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            data = json.loads(self.request.body)
            userName = data['ftpUserName']
            password = data['ftpPassword']

            FTPUtilities.changeFTPPassword(userName, password)

            data_ret = {'status': 1, 'changePasswordStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException, msg:
            data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)