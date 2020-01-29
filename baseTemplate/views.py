# -*- coding: utf-8 -*-


from django.shortcuts import render,redirect
from django.http import HttpResponse
from plogical.getSystemInformation import SystemInformation
from loginSystem.models import Administrator, ACL
import json
from loginSystem.views import loadLoginPage
import re
from .models import version
import requests
import subprocess
import shlex
import os
import plogical.CyberCPLogFileWriter as logging
from plogical.acl import ACLManager
from manageServices.models import PDNSStatus
from django.views.decorators.csrf import ensure_csrf_cookie
from plogical.processUtilities import ProcessUtilities
# Create your views here.


@ensure_csrf_cookie
def renderBase(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            admin = 1
        else:
            admin = 0

        cpuRamDisk = SystemInformation.cpuRamDisk()

        finaData = {"admin": admin,'ramUsage':cpuRamDisk['ramUsage'],'cpuUsage':cpuRamDisk['cpuUsage'],'diskUsage':cpuRamDisk['diskUsage'] }

        return render(request, 'baseTemplate/homePage.html', finaData)
    except KeyError:
        return redirect(loadLoginPage)

def getAdminStatus(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)

        if os.path.exists('/home/cyberpanel/postfix'):
            currentACL['emailAsWhole'] = 1
        else:
            currentACL['emailAsWhole'] = 0

        if os.path.exists('/home/cyberpanel/pureftpd'):
            currentACL['ftpAsWhole'] = 1
        else:
            currentACL['ftpAsWhole'] = 0

        try:
            pdns = PDNSStatus.objects.get(pk=1)
            currentACL['dnsAsWhole'] = pdns.serverStatus
        except:
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                pdnsPath = '/etc/powerdns'
            else:
                pdnsPath = '/etc/pdns'

            if os.path.exists(pdnsPath):
                PDNSStatus(serverStatus=1).save()
                currentACL['dnsAsWhole'] = 1
            else:
                currentACL['dnsAsWhole'] = 0

        json_data = json.dumps(currentACL)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Can not get admin Status")

def getSystemStatus(request):
    try:

        HTTPData = SystemInformation.getSystemInformation()
        json_data = json.dumps(HTTPData)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Can not get admin Status")

def getLoadAverage(request):
    loadAverage = SystemInformation.cpuLoad()
    loadAverage = list(loadAverage)
    one = loadAverage[0]
    two = loadAverage[1]
    three = loadAverage[2]

    loadAvg = {"one": one, "two": two,"three": three}

    json_data = json.dumps(loadAvg)

    return HttpResponse(json_data)

@ensure_csrf_cookie
def versionManagment(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        elif currentACL['versionManagement'] == 1:
            pass
        else:
            return ACLManager.loadError()

        ## Get latest version

        getVersion = requests.get('https://cyberpanel.net/version.txt')

        latest = getVersion.json()

        latestVersion = latest['version']
        latestBuild = latest['build']

        ## Get local version


        versionFile = '/usr/local/CyberCP/version.txt'

        try:
            data = open(versionFile, 'r').read().split('\n')
            currentVersion = data[0]
            currentBuild = data[1]
        except:
            currentVersion = latestVersion
            currentBuild = str(latestBuild) + 'E'

        return render(request, 'baseTemplate/versionManagment.html', {'build': currentBuild,
                                                                      'currentVersion': currentVersion,
                                                                      'latestVersion': latestVersion,
                                                                      'latestBuild': latestBuild})

    except KeyError:
        return redirect(loadLoginPage)

def upgrade(request):
    try:
        admin = request.session['userID']

        try:
            os.remove('upgrade.py')
        except:
            pass

        command = 'wget http://cyberpanel.net/upgrade.py'

        cmd = shlex.split(command)

        res = subprocess.call(cmd)

        vers = version.objects.get(pk=1)

        from upgrade import Upgrade

        Upgrade.initiateUpgrade(vers.currentVersion,vers.build)

        adminData = {"upgrade":1}

        json_data = json.dumps(adminData)

        return HttpResponse(json_data)


    except KeyError:
        adminData = {"upgrade": 1,"error_message":"Please login or refresh this page."}
        json_data = json.dumps(adminData)
        return HttpResponse(json_data)

def upgradeStatus(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                path = "/usr/local/lscp/logs/upgradeLog"

                try:
                    upgradeLog = open(path, "r").read()
                except:
                    final_json = json.dumps({'finished': 0, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': "Upgrade Just started.."})
                    return HttpResponse(final_json)


                if upgradeLog.find("Upgrade Completed")>-1:

                    vers = version.objects.get(pk=1)
                    getVersion = requests.get('https://cyberpanel.net/version.txt')
                    latest = getVersion.json()
                    vers.currentVersion = latest['version']
                    vers.build = latest['build']
                    vers.save()

                    os.remove(path)

                    final_json = json.dumps({'finished': 1, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': upgradeLog})
                    return HttpResponse(final_json)
                else:
                    final_json = json.dumps({'finished': 0, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': upgradeLog})
                    return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'upgradeStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'upgradeStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def upgradeVersion(request):
    try:
        vers = version.objects.get(pk=1)
        getVersion = requests.get('https://cyberpanel.net/version.txt')
        latest = getVersion.json()
        vers.currentVersion = latest['version']
        vers.build = latest['build']
        vers.save()
        return HttpResponse("Version upgrade OK.")
    except BaseException as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        return HttpResponse(str(msg))