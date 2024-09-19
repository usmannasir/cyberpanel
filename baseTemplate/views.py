# -*- coding: utf-8 -*-
from random import randint

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
BUILD = 7


@ensure_csrf_cookie
def renderBase(request):
    template = 'baseTemplate/homePage.html'
    cpuRamDisk = SystemInformation.cpuRamDisk()
    finaData = {'ramUsage': cpuRamDisk['ramUsage'], 'cpuUsage': cpuRamDisk['cpuUsage'],
                'diskUsage': cpuRamDisk['diskUsage']}
    proc = httpProc(request, template, finaData)
    return proc.render()


@ensure_csrf_cookie
def versionManagement(request):
    getVersion = requests.get('https://cyberpanel.net/version.txt')
    latest = getVersion.json()
    latestVersion = latest['version']
    latestBuild = latest['build']

    currentVersion = VERSION
    currentBuild = str(BUILD)

    u = "https://api.github.com/repos/usmannasir/cyberpanel/commits?sha=v%s.%s" % (latestVersion, latestBuild)
    logging.writeToFile(u)
    r = requests.get(u)
    latestcomit = r.json()[0]['sha']

    command = "git -C /usr/local/CyberCP/ rev-parse HEAD"
    output = ProcessUtilities.outputExecutioner(command)

    Currentcomt = output.rstrip("\n")
    notechk = True

    if Currentcomt == latestcomit:
        notechk = False

    template = 'baseTemplate/versionManagment.html'
    finalData = {'build': currentBuild, 'currentVersion': currentVersion, 'latestVersion': latestVersion,
                 'latestBuild': latestBuild, 'latestcomit': latestcomit, "Currentcomt": Currentcomt,
                 "Notecheck": notechk}

    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


@ensure_csrf_cookie
def upgrade_cyberpanel(request):
    if request.method == 'POST':
        try:
            upgrade_command = 'sh <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh || wget -O - https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh)'
            result = subprocess.run(upgrade_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True)

            if result.returncode == 0:
                response_data = {'success': True, 'message': 'CyberPanel upgrade completed successfully.'}
            else:
                response_data = {'success': False,
                                 'message': 'CyberPanel upgrade failed. Error output: ' + result.stderr}
        except Exception as e:
            response_data = {'success': False, 'message': 'An error occurred during the upgrade: ' + str(e)}


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

    command = "git -C /usr/local/CyberCP/ rev-parse HEAD"
    output = ProcessUtilities.outputExecutioner(command)

    Currentcomt = output.rstrip("\n")
    notechk = True

    if (Currentcomt == latestcomit):
        notechk = False

    template = 'baseTemplate/versionManagment.html'
    finalData = {'build': currentBuild, 'currentVersion': currentVersion, 'latestVersion': latestVersion,
                 'latestBuild': latestBuild, 'latestcomit': latestcomit, "Currentcomt": Currentcomt,
                 "Notecheck": notechk}

    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


def upgrade(request):
    try:
        admin = request.session['userID']
        currentACL = ACLManager.loadedACL(admin)

        data = json.loads(request.body)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        from plogical.applicationInstaller import ApplicationInstaller

        extraArgs = {}
        extraArgs['branchSelect'] = data["branchSelect"]
        background = ApplicationInstaller('UpgradeCP', extraArgs)
        background.start()

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
        currentACL = ACLManager.loadedACL(val)
        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        try:
            if request.method == 'POST':
                from plogical.upgrade import Upgrade

                path = Upgrade.LogPathNew

                try:
                    upgradeLog = ProcessUtilities.outputExecutioner(f'cat {path}')
                except:
                    final_json = json.dumps({'finished': 0, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': "Upgrade Just started.."})
                    return HttpResponse(final_json)

                if upgradeLog.find("Upgrade Completed") > -1:

                    command = f'rm -rf {path}'
                    ProcessUtilities.executioner(command)

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

        # logging.CyberCPLogFileWriter.writeToFile(str(data) + "  [themedata]")

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


def onboarding(request):
    template = 'baseTemplate/onboarding.html'

    proc = httpProc(request, template, None, 'admin')
    return proc.render()


def runonboarding(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)
        hostname = data['hostname']

        try:
            rDNSCheck = str(int(data['rDNSCheck']))
        except:
            rDNSCheck = 0

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        WriteToFile = open(tempStatusPath, 'w')
        WriteToFile.write('Starting')
        WriteToFile.close()

        command = f'/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/virtualHostUtilities.py OnBoardingHostName --virtualHostName {hostname} --path {tempStatusPath} --rdns {rDNSCheck}'
        ProcessUtilities.popenExecutioner(command)

        dic = {'status': 1, 'tempStatusPath': tempStatusPath}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def RestartCyberPanel(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()


        command = 'systemctl restart lscpd'
        ProcessUtilities.popenExecutioner(command)

        dic = {'status': 1}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)
