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


# Create your views here.


def loadFileManagerHome(request,domain):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if Websites.objects.filter(domain=domain).exists():
            if admin.type == 1:
                viewStatus = 1
                if admin.type == 3:
                    viewStatus = 0

                return render(request, 'filemanager/index.html', {"viewStatus": viewStatus})
            else:
                website = Websites.objects.get(domain=domain)
                if website.admin == admin:
                    viewStatus = 1

                    if admin.type == 3:
                        viewStatus = 0

                    return render(request, 'filemanager/index.html', {"viewStatus": viewStatus})
                else:
                    return HttpResponse("Domain ownership error.")
        else:
            return HttpResponse("Domain does not exists.")


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
        val = request.session['userID']

        data = json.loads(request.body)
        domainName = data['domainName']

        admin = Administrator.objects.get(pk=val)

        ## Create file manager entry

        if Websites.objects.filter(domain=domainName).exists():
            if admin.type == 1:

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/filemanager.py"

                execPath = execPath + " createTemporaryFile --domainName " + domainName

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("0,") > -1:
                    data_ret = {'createTemporaryFile': 0, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                else:
                    domainRandomSeed = output.rstrip('\n')
                    data_ret = {'createTemporaryFile': 1, 'error_message': "None", 'domainRandomSeed':domainRandomSeed}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            else:
                website = Websites.objects.get(domain=domainName)
                if website.admin == admin:
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
                else:
                    data_ret = {'createTemporaryFile': 0, 'error_message': "Domain ownership error."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)
