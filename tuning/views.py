# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
import json
import plogical.CyberCPLogFileWriter as logging
from plogical.tuning import tuning
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites,ChildDomains
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
# Create your views here.


def loadTuningHome(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")
        return render(request,'tuning/index.html',{})
    except KeyError:
        return redirect(loadLoginPage)


def liteSpeedTuning(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")
        return render(request,'tuning/liteSpeedTuning.html',{})
    except KeyError:
        return redirect(loadLoginPage)


def phpTuning(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        admin = Administrator.objects.get(pk=request.session['userID'])

        websites = Websites.objects.all()
        websitesName = []

        for items in websites:
            websitesName.append(items.domain)

        childs = ChildDomains.objects.all()

        for items in childs:
            websitesName.append(items.domain)

        return render(request,'tuning/phpTuning.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)


def tuneLitespeed(request):

    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                if request.method == 'POST':
                    data = json.loads(request.body)
                    status = data['status']


                    if status=="fetch":

                        json_data = json.dumps(tuning.fetchTuningDetails())

                        data_ret = {'fetch_status': 1, 'error_message': "None","tuning_data":json_data,'tuneStatus': 0}

                        final_json = json.dumps(data_ret)
                        return HttpResponse(final_json)

                    else:
                        if not data['maxConn']:
                            data_ret = {'fetch_status': 1, 'error_message': "Provide Max Connections", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)

                        if not data['maxSSLConn']:
                            data_ret = {'fetch_status': 1, 'error_message': "Provide Max SSL Connections", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)

                        if not data['keepAlive']:
                            data_ret = {'fetch_status': 1, 'error_message': "Provide Keep Alive", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)

                        if not data['inMemCache']:
                            data_ret = {'fetch_status': 1, 'error_message': "Provide Cache Size in memory", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)


                        if not data['gzipCompression']:
                            data_ret = {'fetch_status': 1, 'error_message': "Provide Enable GZIP Compression", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)


                        maxConn = data['maxConn']
                        maxSSLConn = data['maxSSLConn']
                        connTime = data['connTime']
                        keepAlive = data['keepAlive']
                        inMemCache = data['inMemCache']
                        gzipCompression = data['gzipCompression']

                        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/tuning.py"

                        execPath = execPath + " saveTuningDetails --maxConn " + maxConn + " --maxSSLConn " + maxSSLConn + " --connTime " + connTime + " --keepAlive " + keepAlive + " --inMemCache '" + inMemCache + "' --gzipCompression " + gzipCompression

                        output = subprocess.check_output(shlex.split(execPath))

                        if output.find("1,None") > -1:
                            data_ret = {'fetch_status': 1, 'error_message': "None", 'tuneStatus': 1}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)
                        else:
                            data_ret = {'fetch_status': 1, 'error_message': "None", 'tuneStatus': 0}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)

            else:
                data_ret = {'fetch_status': 0, 'error_message': "You don't have enough privileges.", 'tuneStatus': 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'fetch_status': 0, 'error_message': str(msg),  'tuneStatus': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'fetch_status': 0, 'error_message': "not logged in as admin",'fetch_status': 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def tunePHP(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)
            if admin.type == 1:
                if request.method == 'POST':
                    data = json.loads(request.body)
                    status = data['status']
                    domainSelection = str(data['domainSelection'])

                    if status=="fetch":

                        json_data = json.dumps(tuning.fetchPHPDetails(domainSelection))

                        data_ret = {'fetch_status': 1, 'error_message': "None","tuning_data":json_data,'tuneStatus': 0}

                        final_json = json.dumps(data_ret)

                        return HttpResponse(final_json)

                    else:
                        initTimeout = str(data['initTimeout'])
                        maxConns = str(data['maxConns'])
                        memSoftLimit = data['memSoftLimit']
                        memHardLimit = data['memHardLimit']
                        procSoftLimit = str(data['procSoftLimit'])
                        procHardLimit = str(data['procHardLimit'])
                        persistConn = data['persistConn']

                        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/tuning.py"

                        execPath = execPath + " tunePHP --virtualHost " + domainSelection +" --initTimeout " + initTimeout + " --maxConns " + maxConns + " --memSoftLimit " + memSoftLimit + " --memHardLimit '" + memHardLimit + "' --procSoftLimit " + procSoftLimit + " --procHardLimit " + procHardLimit + " --persistConn " + persistConn



                        output = subprocess.check_output(shlex.split(execPath))

                        if output.find("1,None") > -1:
                            data_ret = {'tuneStatus': 1,'fetch_status': 0, 'error_message': "None"}
                            final_json = json.dumps(data_ret)
                            return HttpResponse(final_json)
                        else:
                            data_ret = {'fetch_status': 0, 'error_message': output, 'tuneStatus': 0}
                            logging.CyberCPLogFileWriter.writeToFile(output + " [tunePHP]]")
                            json_data = json.dumps(data_ret)
                            return HttpResponse(json_data)
            else:
                data_ret = {'fetch_status': 0, 'error_message': "You don't have enough privileges.", 'tuneStatus': 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



        except BaseException,msg:
            data_ret = {'fetch_status': 0, 'error_message': str(msg),'tuneStatus': 0}
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [tunePHP]]")
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'tuneStatus': 0, 'error_message': "not logged in as admin",'fetch_status': 0}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [tunePHP]]")
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
