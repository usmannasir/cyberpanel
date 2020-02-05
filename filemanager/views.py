# -*- coding: utf-8 -*-


from django.shortcuts import render,redirect
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
from django.http import HttpResponse,Http404
import json
from websiteFunctions.models import Websites
import subprocess
import shlex
import os
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.acl import ACLManager
from .filemanager import FileManager as FM
from plogical.processUtilities import ProcessUtilities
# Create your views here.


def loadFileManagerHome(request,domain):
    try:
        userID = request.session['userID']
        if Websites.objects.filter(domain=domain).exists():
            admin = Administrator.objects.get(pk=userID)
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                return render(request, 'filemanager/index.html', {'domainName': domain})
            else:
                return ACLManager.loadError()
        else:
            return HttpResponse("Domain does not exists.")

    except KeyError:
        return redirect(loadLoginPage)

def changePermissions(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            data = json.loads(request.body)
            domainName = data['domainName']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('permissionsChanged', 0)

            website = Websites.objects.get(domain=domainName)
            externalApp = website.externalApp

            command = "sudo chown -R " + externalApp + ":" + externalApp +" /home/"+domainName
            ProcessUtilities.popenExecutioner(command)

            command = "sudo chown -R lscpd:lscpd /home/" + domainName+"/logs"
            ProcessUtilities.popenExecutioner(command)

            command = "find %s -type d -exec chmod 0755 {} \;" % ("/home/" + domainName + "/public_html")
            ProcessUtilities.popenExecutioner(command)

            command = "find %s -type f -exec chmod 0644 {} \;" % ("/home/" + domainName + "/public_html")
            ProcessUtilities.popenExecutioner(command)

            data_ret = {'permissionsChanged': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            data_ret = {'permissionsChanged': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def downloadFile(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)

        fileToDownload = request.GET.get('fileToDownload')
        domainName = request.GET.get('domainName')

        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('permissionsChanged', 0)

        homePath = '/home/%s' % (domainName)

        if fileToDownload.find('..') > -1 or fileToDownload.find(homePath) == -1:
            return HttpResponse("Unauthorized access.")

        response = HttpResponse(content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=%s' % (fileToDownload.split('/')[-1])
        response['X-LiteSpeed-Location'] = '%s' % (fileToDownload)

        return response

    except KeyError:
        return redirect(loadLoginPage)

def controller(request):
    try:
        data = json.loads(request.body)
        domainName = data['domainName']
        method = data['method']

        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        fm = FM(request, data)

        if method == 'listForTable':
            return fm.listForTable()
        elif method == 'list':
            return fm.list()
        elif method == 'createNewFile':
            return fm.createNewFile()
        elif method == 'createNewFolder':
            return fm.createNewFolder()
        elif method == 'deleteFolderOrFile':
            return fm.deleteFolderOrFile()
        elif method == 'copy':
            return fm.copy()
        elif method == 'move':
            return fm.move()
        elif method == 'rename':
            return fm.rename()
        elif method == 'readFileContents':
            return fm.readFileContents()
        elif method == 'writeFileContents':
            return fm.writeFileContents()
        elif method == 'upload':
            return fm.writeFileContents()
        elif method == 'extract':
            return fm.extract()
        elif method == 'compress':
            return fm.compress()
        elif method == 'changePermissions':
            return fm.changePermissions()


    except BaseException as msg:
        fm = FM(request, None)
        return fm.ajaxPre(0, str(msg))

def upload(request):
    try:

        data = request.POST

        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.checkOwnership(data['domainName'], admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        fm = FM(request, data)
        return fm.upload()

    except KeyError:
        return redirect(loadLoginPage)
