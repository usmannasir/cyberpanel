# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from plogical.acl import ACLManager
from django.shortcuts import HttpResponse
from plogical.processUtilities import ProcessUtilities
from plogical.virtualHostUtilities import virtualHostUtilities
import json
import os
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
from .models import IncJob, JobSnapshots
from .IncBackups import IncJobs
from random import randint
import time
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
# Create your views here.


def defRenderer(request, templateName, args):
    return render(request, templateName, args)

def createBackup(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'createBackup') == 0:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        destinations = []
        destinations.append('local')

        path = '/home/cyberpanel/sftp'

        for items in os.listdir(path):
            destinations.append('sftp:%s' % (items))

        for items in os.listdir(path):
            destinations.append('s3:s3.amazonaws.com/%s' % (items))

        return defRenderer(request, 'IncBackups/createBackup.html', {'websiteList': websitesName, 'destinations': destinations})
    except BaseException, msg:
        return HttpResponse(str(msg))

def backupDestinations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadError()

        return defRenderer(request, 'IncBackups/incrementalDestinations.html', {})
    except BaseException, msg:
        return HttpResponse(str(msg))

def addDestination(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('destStatus', 0)

        data = json.loads(request.body)



        if data['type'] == 'SFTP':

            ipAddress = data['IPAddress']
            password = data['password']

            ipFile = '/home/cyberpanel/sftp/%s' % (ipAddress)

            try:
                port = data['backupSSHPort']
            except:
                port = "22"

            if os.path.exists(ipFile):
                final_dic = {'status': 0, 'error_message': 'This destination already exists.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


            try:
                os.mkdir('/home/cyberpanel/sftp')
            except:
                pass


            execPath = "/usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " submitDestinationCreation --ipAddress " + ipAddress + " --password " \
                       + password + " --port " + port

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find('1,') > -1:

                content = '%s\n%s' % (ipAddress, port)
                writeToFile = open(ipFile, 'w')
                writeToFile.write(content)
                writeToFile.close()

                command = 'cat /root/.ssh/config'
                currentConfig = ProcessUtilities.outputExecutioner(command)

                tmpFile = '/home/cyberpanel/sshconfig'

                writeToFile = open(tmpFile, 'w')
                writeToFile.write(currentConfig)

                content = """Host %s
        IdentityFile ~/.ssh/cyberpanel
        Port %s
    """ % (ipAddress, port)
                writeToFile.write(content)
                writeToFile.close()


                command = 'mv %s /root/.ssh/config' % (tmpFile)
                ProcessUtilities.executioner(command)

                command = 'chown root:root /root/.ssh/config'
                ProcessUtilities.executioner(command)

                final_dic = {'status': 1, 'error_message': 'None'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


            else:
                final_dic = {'status': 0, 'error_message': output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        else:
            aws = '/home/cyberpanel/aws'

            try:
                os.mkdir(aws)
            except:
                pass

            AWS_ACCESS_KEY_ID = data['AWS_ACCESS_KEY_ID']
            AWS_SECRET_ACCESS_KEY = data['AWS_SECRET_ACCESS_KEY']

            awsFile = '/home/cyberpanel/aws/%s' % (AWS_ACCESS_KEY_ID)

            writeToFile = open(awsFile, 'w')
            writeToFile.write(AWS_SECRET_ACCESS_KEY)
            writeToFile.close()

            final_dic = {'status': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)




    except BaseException, msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def populateCurrentRecords(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        data = json.loads(request.body)

        if data['type'] == 'SFTP':

            path = '/home/cyberpanel/sftp'

            if os.path.exists(path):

                json_data = "["
                checker = 0

                for items in os.listdir(path):
                    fullPath = '/home/cyberpanel/sftp/%s' % (items)

                    data = open(fullPath, 'r').readlines()
                    dic = {
                        'ip': data[0].strip('\n'),
                           'port': data[1],
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
            else:
                final_json = json.dumps({'status': 1, 'error_message': "None", "data": ''})
                return HttpResponse(final_json)
        else:
            path = '/home/cyberpanel/aws'

            if os.path.exists(path):

                json_data = "["
                checker = 0

                for items in os.listdir(path):
                    dic = {
                        'AWS_ACCESS_KEY_ID': items
                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
            else:
                final_json = json.dumps({'status': 1, 'error_message': "None", "data": ''})
                return HttpResponse(final_json)

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def removeDestination(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('destStatus', 0)

        data = json.loads(request.body)

        ipAddress = data['IPAddress']

        if data['type'] == 'SFTP':
            ipFile = '/home/cyberpanel/sftp/%s' % (ipAddress)
        else:
            ipFile = '/home/cyberpanel/aws/%s' % (ipAddress)


        os.remove(ipFile)

        final_dic = {'status': 1, 'error_message': 'None'}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetchCurrentBackups(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        data = json.loads(request.body)
        backupDomain = data['websiteToBeBacked']

        if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        website = Websites.objects.get(domain=backupDomain)

        backups = website.incjob_set.all()

        json_data = "["
        checker = 0

        for items in backups:

            includes = ""

            jobs = items.jobsnapshots_set.all()

            for job in jobs:
                includes = '%s,%s:%s' % (includes, job.type, job.snapshotid)

            dic = {'id': items.id,
                   'date': str(items.date),
                   'includes': includes
                   }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)
    except BaseException, msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def submitBackupCreation(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        data = json.loads(request.body)
        backupDomain = data['websiteToBeBacked']
        backupDestinations = data['backupDestinations']

        if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('metaStatus', 0)

        tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        try:
            websiteData = data['websiteData']
        except:
            websiteData = False

        try:
            websiteEmails = data['websiteEmails']
        except:
            websiteEmails = False

        try:
            websiteSSLs = data['websiteSSLs']
        except:
            websiteSSLs = False

        extraArgs = {}
        extraArgs['website'] = backupDomain
        extraArgs['tempPath'] = tempPath
        extraArgs['backupDestinations'] = backupDestinations
        extraArgs['websiteData'] = websiteData
        extraArgs['websiteEmails'] = websiteEmails
        extraArgs['websiteSSLs'] = websiteSSLs

        startJob = IncJobs('createBackup', extraArgs)
        startJob.start()


        time.sleep(2)

        final_json = json.dumps({'status': 1,  'error_message': "None", 'tempPath': tempPath})
        return HttpResponse(final_json)

    except BaseException, msg:
        logging.writeToFile(str(msg))
        final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def getBackupStatus(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)

        status = data['tempPath']
        backupDomain = data['websiteToBeBacked']

        domain = Websites.objects.get(domain=backupDomain)

        ## file name read ends

        if os.path.exists(status):
            command = "sudo cat " + status
            status = ProcessUtilities.outputExecutioner(command, 'cyberpanel')

            if status.find("Completed") > -1:

                ### Removing Files

                command = 'sudo rm -f ' + status
                ProcessUtilities.executioner(command, 'cyberpanel')

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": status, "abort": 1})
                return HttpResponse(final_json)

            elif status.find("[5009]") > -1:
                ## removing status file, so that backup can re-run
                try:
                    command = 'sudo rm -f ' + status
                    ProcessUtilities.executioner(command, 'cyberpanel')

                except:
                    pass

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": status,
                     "abort": 1})
                return HttpResponse(final_json)
            else:
                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": status,
                     "abort": 0})
                return HttpResponse(final_json)
        else:
            final_json = json.dumps({'backupStatus': 1, 'error_message': "None", "status": 1, "abort": 0})
            return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'backupStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        logging.writeToFile(str(msg) + " [backupStatus]")
        return HttpResponse(final_json)


def deleteBackup(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadErrorJson('destStatus', 0)

        data = json.loads(request.body)

        id = data['backupID']

        IncJob.objects.get(id=id).delete()

        final_dic = {'status': 1, 'error_message': 'None'}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)