# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
            subprocess.call(shlex.split(command))

            command = "sudo chown -R lscpd:lscpd /home/" + domainName+"/logs"
            subprocess.call(shlex.split(command))

            data_ret = {'permissionsChanged': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            data_ret = {'permissionsChanged': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def downloadFile(request):
    try:

        data = json.loads(request.body)
        fileToDownload = data['fileToDownload']

        response = ''
        if os.path.isfile(fileToDownload):
            try:
                with open(fileToDownload, 'rb') as f:
                    response = HttpResponse(f.read(), content_type="application/octet-stream")
                    response['Content-Disposition'] = 'inline; filename=' + os.path.basename(fileToDownload)
            except Exception as e:
                raise Http404
        return response

    except KeyError:
        return redirect(loadLoginPage)

def createTemporaryFile(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        domainName = data['domainName']

        admin = Administrator.objects.get(pk=userID)

        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('createTemporaryFile', 0)

        ## Create file manager entry

        if Websites.objects.filter(domain=domainName).exists():
            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/filemanager.py"

            execPath = execPath + " createTemporaryFile --domainName " + domainName

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("0,") > -1:
                data_ret = {'createTemporaryFile': 0, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            else:
                domainRandomSeed = output.rstrip('\n')
                data_ret = {'createTemporaryFile': 1, 'error_message': "None", 'domainRandomSeed': domainRandomSeed}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)
