#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from django.shortcuts import render,redirect
from django.http import HttpResponse
from .models import Users
from loginSystem.models import Administrator
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites
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
        except BaseException as msg:
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
            password = data['passwordByPass']

            domainName = data['ftpDomain']

            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

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


            result = FTPUtilities.submitFTPCreation(domainName, userName, password, path, admin.userName, api)

            if result[0] == 1:
                data_ret = {'status': 1, 'creatFTPStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'creatFTPStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
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
        except BaseException as msg:
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

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

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

        except BaseException as msg:
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

            admin = Administrator.objects.get(pk=userID)
            ftp = Users.objects.get(user=ftpUserName)

            if ACLManager.checkOwnership(ftp.domain.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            FTPUtilities.submitFTPDeletion(ftpUserName)

            final_json = json.dumps({'status': 1, 'deleteStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException as msg:
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
        except BaseException as msg:
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

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(selectedDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

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

        except BaseException as msg:
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
            password = data['passwordByPass']

            admin = Administrator.objects.get(pk=userID)
            ftp = Users.objects.get(user=userName)

            if currentACL['admin'] == 1:
                pass
            elif ftp.domain.admin != admin:
                return ACLManager.loadErrorJson()

            FTPUtilities.changeFTPPassword(userName, password)

            data_ret = {'status': 1, 'changePasswordStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)