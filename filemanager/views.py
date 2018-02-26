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

# Create your views here.


def loadFileManagerHome(request,domain):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        viewStatus = 1

        if admin.type == 3:
            viewStatus = 0

        return render(request,'filemanager/index.html',{"viewStatus":viewStatus})
    except KeyError:
        return redirect(loadLoginPage)


def changePermissions(request):
    try:
        val = request.session['userID']
        try:
            data = json.loads(request.body)
            domainName = data['domainName']

            website = Websites.objects.get(domain=domainName)
            externalApp = website.externalApp

            command = "sudo chown -R " + externalApp + ":" + externalApp +" /home/"+domainName
            subprocess.call(shlex.split(command))

            command = "sudo chown -R nobody:nobody /home/" + domainName+"/logs"
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