# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpResponse
from plogical.getSystemInformation import SystemInformation
import json
from loginSystem.views import loadLoginPage
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
from plogical.httpProc import httpProc

# Create your views here.

VERSION = '2.3'
BUILD = 2


@ensure_csrf_cookie
def renderBase(request):
    template = 'baseTemplate/homePage.html'
    cpuRamDisk = SystemInformation.cpuRamDisk()
    finaData = {'ramUsage': cpuRamDisk['ramUsage'], 'cpuUsage': cpuRamDisk['cpuUsage'],
                'diskUsage': cpuRamDisk['diskUsage']}
    proc = httpProc(request, template, finaData)
    return proc.render()


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
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
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
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        HTTPData = SystemInformation.getSystemInformation()
        json_data = json.dumps(HTTPData)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Can not get admin Status")


def getLoadAverage(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        loadAverage = SystemInformation.cpuLoad()
        loadAverage = list(loadAverage)
        one = loadAverage[0]
        two = loadAverage[1]
        three = loadAverage[2]
        loadAvg = {"one": one, "two": two, "three": three}
        json_data = json.dumps(loadAvg)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Not allowed.")


@ensure_csrf_cookie
def versionManagment(request):
    ## Get latest version

    getVersion = requests.get('https://cyberpanel.net/version.txt')
    latest = getVersion.json()
    latestVersion = latest['version']
    latestBuild = latest['build']

    ## Get local version

    currentVersion = VERSION
    currentBuild = str(BUILD)

    u = "https://api.github.com/repos/usmannasir/cyberpanel/commits?sha=v%s.%s" % (latestVersion, latestBuild)
    logging.CyberCPLogFileWriter.writeToFile(u)
    r = requests.get(u)
    latestcomit = r.json()[0]['sha']

    command ="git -C /usr/local/CyberCP/ rev-parse HEAD"
    output = ProcessUtilities.outputExecutioner(command)

    Currentcomt = output.rstrip("\n")
    notechk = True
    
    # command ="git fetch -C /usr/local/CyberCP/"
    # output = ProcessUtilities.outputExecutioner(command)
    #
    # command ="git -C /usr/local/CyberCP/ log %s..%s --pretty=oneline | wc -l" % ( Currentcomt, latestcomit)
    # output = ProcessUtilities.outputExecutioner(command)
    #
    # numCommits = output.rstrip("\n")

    if(Currentcomt == latestcomit):
        notechk = False


    template = 'baseTemplate/versionManagment.html'
    finalData = {'build': currentBuild, 'currentVersion': currentVersion, 'latestVersion': latestVersion,
                 'latestBuild': latestBuild, 'latestcomit': latestcomit, "Currentcomt": Currentcomt, "Notecheck" : notechk }


    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


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

        Upgrade.initiateUpgrade(vers.currentVersion, vers.build)

        adminData = {"upgrade": 1}

        json_data = json.dumps(adminData)

        return HttpResponse(json_data)


    except KeyError:
        adminData = {"upgrade": 1, "error_message": "Please login or refresh this page."}
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

                if upgradeLog.find("Upgrade Completed") > -1:

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


@ensure_csrf_cookie
def design(request):
    ### Load Custom CSS
    try:
        from baseTemplate.models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic.objects.get(pk=1)
    except:
        from baseTemplate.models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic()
        cosmetic.save()

    val = request.session['userID']
    currentACL = ACLManager.loadedACL(val)
    if currentACL['admin'] == 1:
        pass
    else:
        return ACLManager.loadErrorJson('reboot', 0)

    finalData = {}

    if request.method == 'POST':
        MainDashboardCSS = request.POST.get('MainDashboardCSS', '')
        cosmetic.MainDashboardCSS = MainDashboardCSS
        cosmetic.save()
        finalData['saved'] = 1

    ####### Fetch sha...

    sha_url = "https://api.github.com/repos/usmannasir/CyberPanel-Themes/commits"

    sha_res = requests.get(sha_url)

    sha = sha_res.json()[0]['sha']

    l = "https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/trees/%s" % sha
    fres = requests.get(l)
    tott = len(fres.json()['tree'])
    finalData['tree'] = []
    for i in range(tott):
        if (fres.json()['tree'][i]['type'] == "tree"):
            finalData['tree'].append(fres.json()['tree'][i]['path'])

    template = 'baseTemplate/design.html'
    finalData['cosmetic'] = cosmetic

    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


def getthemedata(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        data = json.loads(request.body)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('reboot', 0)

        #logging.CyberCPLogFileWriter.writeToFile(str(data) + "  [themedata]")

        url = "https://raw.githubusercontent.com/usmannasir/CyberPanel-Themes/main/%s/design.css" % data['Themename']

        res = requests.get(url)

        rsult = res.text
        final_dic = {'status': 1, 'csscontent': rsult}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

