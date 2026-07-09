#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import re
from io import StringIO

import django
import paramiko

from plogical.applicationInstaller import ApplicationInstaller
from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, Backups, dest, backupSchedules, BackupJob, GDrive, GDriveSites
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
from django.shortcuts import HttpResponse, render
from loginSystem.models import Administrator
from plogical.mailUtilities import mailUtilities
from random import randint
import time
import plogical.backupUtilities as backupUtil
from plogical.processUtilities import ProcessUtilities
from multiprocessing import Process
import requests
import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.discovery import build
from websiteFunctions.models import NormalBackupDests, NormalBackupJobs, NormalBackupSites
from plogical.IncScheduler import IncScheduler
from django.http import JsonResponse

class BackupManager:
    localBackupPath = '/home/cyberpanel/localBackupPath'

    def __init__(self, domain=None, childDomain=None):
        self.domain = domain
        self.childDomain = childDomain

    def loadBackupHome(self, request=None, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            proc = httpProc(request, 'backup/index.html', currentACL)
            return proc.render()
        except BaseException as msg:
            return HttpResponse(str(msg))

    def backupSite(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)

        command = 'chmod 755 /home/backup'
        ProcessUtilities.executioner(command)

        proc = httpProc(request, 'backup/backup.html', {'websiteList': websitesName}, 'createBackup')
        return proc.render()

    def RestoreV2backupSite(self, request=None, userID=None, data=None):
        if ACLManager.CheckForPremFeature('all'):
            BackupStat = 1
        else:
            BackupStat = 0
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'IncBackups/RestoreV2Backup.html', {'websiteList': websitesName, 'BackupStat': BackupStat}, 'createBackup')
        return proc.render()

    def CreateV2backupSite(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'IncBackups/CreateV2Backup.html', {'websiteList': websitesName}, 'createBackup')
        return proc.render()
    def DeleteRepoV2(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'IncBackups/DeleteV2repo.html', {'websiteList': websitesName}, 'createBackup')
        return proc.render()

    def schedulev2Backups(self, request=None, userID=None, data=None):

        if ACLManager.CheckForPremFeature('all'):
            BackupStat = 1
        else:
            BackupStat = 0

        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'IncBackups/ScheduleV2Backup.html', {'websiteList': websitesName, "BackupStat": BackupStat}, 'createBackup')
        return proc.render()

    def gDrive(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        gDriveAcctsList = []
        gDriveAccts = admin.gdrive_set.all()
        for items in gDriveAccts:
            gDriveAcctsList.append(items.name)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'backup/googleDrive.html', {'accounts': gDriveAcctsList, 'websites': websitesName},
                        'createBackup')
        return proc.render()

    def gDriveSetup(self, userID=None, request=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.currentContextPermission(currentACL, 'createBackup') == 0:
                return ACLManager.loadError()

            gDriveData = {}
            gDriveData['token'] = request.GET.get('t')
            gDriveData['refresh_token'] = request.GET.get('r')
            gDriveData['token_uri'] = request.GET.get('to')
            gDriveData['scopes'] = request.GET.get('s')

            gD = GDrive(owner=admin, name=request.GET.get('n'), auth=json.dumps(gDriveData))
            gD.save()

            return self.gDrive(request, userID)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchDriveLogs(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            recordsToShow = int(data['recordsToShow'])
            page = int(str(data['page']).strip('\n'))

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            logs = gD.gdrivejoblogs_set.all().order_by('-id')

            from s3Backups.s3Backups import S3Backups

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            logs = logs[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 0

            from plogical.backupSchedule import backupSchedule

            for log in logs:

                if log.status == backupSchedule.INFO:
                    status = 'INFO'
                else:
                    status = 'ERROR'

                dic = {
                    'type': status,
                    'message': log.message
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'

            data_ret = {'status': 1, 'logs': json_data, 'pagination': pagination}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchgDriveSites(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            recordsToShow = int(data['recordsToShow'])
            page = int(str(data['page']).strip('\n'))

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            websites = gD.gdrivesites_set.all()

            from s3Backups.s3Backups import S3Backups

            pagination = S3Backups.getPagination(len(websites), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            finalWebsites = websites[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 0

            from plogical.backupSchedule import backupSchedule

            for website in finalWebsites:

                dic = {
                    'name': website.domain
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'

            currently = gD.runTime

            data_ret = {'status': 1, 'websites': json_data, 'pagination': pagination, 'currently': currently}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def addSitegDrive(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            selectedWebsite = data['selectedWebsite']

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL) == 1 and ACLManager.checkOwnership(
                    selectedWebsite, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            gdSite = GDriveSites(owner=gD, domain=selectedWebsite)
            gdSite.save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteAccountgDrive(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL):
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            gD.delete()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeAccountFrequencygDrive(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            backupFrequency = data['backupFrequency']

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL):
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            gD.runTime = backupFrequency

            gD.save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


    def changeFileRetention(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            Retentiontime = data['Retentiontime']
            # logging.CyberCPLogFileWriter.writeToFile("...... FileRetentiontime...%s "%Retentiontime)

            gD = GDrive.objects.get(name=selectedAccount)
            # logging.CyberCPLogFileWriter.writeToFile("...... GDrive obj...%s " % GDrive)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL):
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)



            conf = gD.auth
            # logging.CyberCPLogFileWriter.writeToFile("...... conf...%s " % conf)
            config = json.loads(conf)
            # logging.CyberCPLogFileWriter.writeToFile("...... config...%s " % config)
            config['FileRetentiontime'] = Retentiontime

            gD.auth=json.dumps(config)
            gD.save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteSitegDrive(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            website = data['website']

            gD = GDrive.objects.get(name=selectedAccount)

            if ACLManager.checkGDriveOwnership(gD, admin, currentACL) == 1 and ACLManager.checkOwnership(website, admin,
                                                                                                         currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            sites = GDriveSites.objects.filter(owner=gD, domain=website)

            for items in sites:
                items.delete()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def restoreSite(self, request=None, userID=None, data=None):
        path = os.path.join("/home", "backup")
        if not os.path.exists(path):
            proc = httpProc(request, 'backup/restore.html', None, 'restoreBackup')
            return proc.render()
        else:
            all_files = []
            ext = ".tar.gz"

            command = 'sudo chown -R  cyberpanel:cyberpanel ' + path
            ACLManager.executeCall(command)

            files = os.listdir(path)
            for filename in files:
                if filename.endswith(ext):
                    all_files.append(filename)
            proc = httpProc(request, 'backup/restore.html', {'backups': all_files}, 'restoreBackup')
            return proc.render()

    def getCurrentBackups(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
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

            backups = website.backups_set.all()

            json_data = "["
            checker = 0

            for items in backups:
                if items.status == 0:
                    status = "Pending"
                else:
                    status = "Completed"
                dic = {'id': items.id,
                       'file': items.fileName,
                       'date': items.date,
                       'size': items.size,
                       'status': status
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

    def submitBackupCreation(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            backupDomain = data['websiteToBeBacked']
            website = Websites.objects.get(domain=backupDomain)

            if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('metaStatus', 0)

            ## defining paths

            ## /home/example.com/backup
            backupPath = os.path.join("/home", backupDomain, "backup/")
            backupDomainName = data['websiteToBeBacked']
            backupName = 'backup-' + backupDomainName + "-" + time.strftime("%m.%d.%Y_%H-%M-%S")

            ## /home/example.com/backup/backup-example.com-02.13.2018_10-24-52
            tempStoragePath = os.path.join(backupPath, backupName)

            p = Process(target=backupUtil.submitBackupCreation,
                        args=(tempStoragePath, backupName, backupPath, backupDomain))
            p.start()

            time.sleep(2)

            final_json = json.dumps(
                {'status': 1, 'metaStatus': 1, 'error_message': "None", 'tempStorage': tempStoragePath})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def backupStatus(self, userID=None, data=None):
        try:

            backupDomain = data['websiteToBeBacked']
            status = os.path.join("/home", backupDomain, "backup/status")
            backupFileNamePath = os.path.join("/home", backupDomain, "backup/backupFileName")
            pid = os.path.join("/home", backupDomain, "backup/pid")

            domain = Websites.objects.get(domain=backupDomain)

            ## read file name

            try:
                command = "sudo cat " + backupFileNamePath
                fileName = ProcessUtilities.outputExecutioner(command, domain.externalApp)
                if fileName.find('No such file or directory') > -1:
                    final_json = json.dumps({'backupStatus': 0, 'error_message': "None", "status": 0, "abort": 0})
                    return HttpResponse(final_json)
            except:
                fileName = "Fetching.."

            ## file name read ends

            if os.path.exists(status):
                command = "sudo cat " + status
                status = ProcessUtilities.outputExecutioner(command, domain.externalApp)

                if status.find("Completed") > -1:

                    ### Removing Files

                    command = 'sudo rm -f ' + status
                    ProcessUtilities.executioner(command, domain.externalApp)

                    command = 'sudo rm -f ' + backupFileNamePath
                    ProcessUtilities.executioner(command, domain.externalApp)

                    command = 'sudo rm -f ' + pid
                    ProcessUtilities.executioner(command, domain.externalApp)

                    final_json = json.dumps(
                        {'backupStatus': 1, 'error_message': "None", "status": status, "abort": 1,
                         'fileName': fileName, })
                    return HttpResponse(final_json)

                elif status.find("[5009]") > -1:
                    ## removing status file, so that backup can re-run
                    try:
                        command = 'sudo rm -f ' + status
                        ProcessUtilities.executioner(command, domain.externalApp)

                        command = 'sudo rm -f ' + backupFileNamePath
                        ProcessUtilities.executioner(command, domain.externalApp)

                        command = 'sudo rm -f ' + pid
                        ProcessUtilities.executioner(command, domain.externalApp)

                        backupObs = Backups.objects.filter(fileName=fileName)
                        for items in backupObs:
                            items.delete()

                    except:
                        pass

                    final_json = json.dumps(
                        {'backupStatus': 1, 'fileName': fileName, 'error_message': "None", "status": status,
                         "abort": 1})
                    return HttpResponse(final_json)
                else:
                    final_json = json.dumps(
                        {'backupStatus': 1, 'error_message': "None", 'fileName': fileName, "status": status,
                         "abort": 0})
                    return HttpResponse(final_json)
            else:
                final_json = json.dumps({'backupStatus': 0, 'error_message': "None", "status": 0, "abort": 0})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'backupStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupStatus]")
            return HttpResponse(final_json)

    def cancelBackupCreation(self, userID=None, data=None):
        try:

            backupCancellationDomain = data['backupCancellationDomain']
            fileName = data['fileName']

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " cancelBackupCreation --backupCancellationDomain " + backupCancellationDomain + " --fileName " + fileName
            subprocess.call(shlex.split(execPath))

            try:
                backupOb = Backups.objects.get(fileName=fileName)
                backupOb.delete()
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

            final_json = json.dumps({'abortStatus': 1, 'error_message': "None", "status": 0})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'abortStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteBackup(self, userID=None, data=None):
        try:
            backupID = data['backupID']
            backup = Backups.objects.get(id=backupID)

            domainName = backup.website.domain
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            path = "/home/" + domainName + "/backup/" + backup.fileName + ".tar.gz"
            command = 'sudo rm -f ' + path
            ProcessUtilities.executioner(command)

            backup.delete()

            final_json = json.dumps({'status': 1, 'deleteStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)

    def submitRestore(self, data=None, userID=None):
        try:
            backupFile = data['backupFile']
            originalFile = "/home/backup/" + backupFile

            if not os.path.exists(originalFile):
                dir = data['dir']
            else:
                dir = "CyberPanelRestore"

            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if '..' in str(backupFile) or '..' in str(dir):
                return ACLManager.loadErrorJson()

            execPath = "sudo nice -n 10 /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " submitRestore --backupFile " + shlex.quote(backupFile) + " --dir " + shlex.quote(str(dir))
            ProcessUtilities.popenExecutioner(execPath)
            time.sleep(4)

            final_dic = {'restoreStatus': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'restoreStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def restoreStatus(self, data=None):
        try:
            if '..' in str(data['backupFile']) or '..' in str(data.get('dir', '')):
                return ACLManager.loadErrorJson()

            backupFile = data['backupFile'].strip(".tar.gz")

            path = os.path.join("/home", "backup", data['backupFile'])

            if os.path.exists(path):
                path = os.path.join("/home", "backup", backupFile)
            elif os.path.exists(data['backupFile']):
                path = data['backupFile'].strip(".tar.gz")
            else:
                dir = data['dir']
                path = "/home/backup/transfer-" + str(dir) + "/" + backupFile

            if os.path.exists(path):
                try:
                    execPath = "sudo cat " + shlex.quote(path + "/status")
                    status = ProcessUtilities.outputExecutioner(execPath)

                    if status.find("Done") > -1:

                        command = "sudo rm -rf " + shlex.quote(path)
                        ProcessUtilities.executioner(command)

                        final_json = json.dumps(
                            {'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 1,
                             'running': 'Completed'})
                        return HttpResponse(final_json)
                    elif status.find("[5009]") > -1:
                        ## removing temporarily generated files while restoring
                        command = "sudo rm -rf " + shlex.quote(path)
                        ProcessUtilities.executioner(command)
                        final_json = json.dumps({'restoreStatus': 1, 'error_message': "None",
                                                 "status": status, 'abort': 1, 'alreadyRunning': 0,
                                                 'running': 'Error'})
                        return HttpResponse(final_json)
                    else:
                        final_json = json.dumps(
                            {'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 0,
                             'running': 'Running..'})
                        return HttpResponse(final_json)

                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg))
                    status = "Just Started"
                    final_json = json.dumps(
                        {'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 0,
                         'running': 'Running..'})
                    return HttpResponse(final_json)
            else:
                final_json = json.dumps(
                    {'restoreStatus': 1, 'error_message': "None", "status": "OK To Run", 'running': 'Halted',
                     'abort': 1})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'restoreStatus': 0, 'error_message': str(msg), 'abort': 0, 'running': 'Running..', 'status': ''}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def backupDestinations(self, request=None, userID=None, data=None):
        proc = httpProc(request, 'backup/backupDestinations.html', {}, 'addDeleteDestinations')
        return proc.render()

    def submitDestinationCreation(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('destStatus', 0)

            finalDic = {}

            if data['type'] == 'SFTP':

                finalDic['ipAddress'] = data['IPAddress']
                finalDic['password'] = data['password']

                try:
                    finalDic['port'] = data['backupSSHPort']
                except:
                    finalDic['port'] = "22"

                try:
                    finalDic['user'] = data['userName']
                except:
                    finalDic['user'] = "root"

                # SECURITY: Validate all inputs to prevent command injection
                if ACLManager.commandInjectionCheck(finalDic['ipAddress']) == 1:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': 'Invalid characters in IP address'}
                    return HttpResponse(json.dumps(final_dic))

                if ACLManager.commandInjectionCheck(finalDic['password']) == 1:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': 'Invalid characters in password'}
                    return HttpResponse(json.dumps(final_dic))

                if ACLManager.commandInjectionCheck(finalDic['port']) == 1:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': 'Invalid characters in port'}
                    return HttpResponse(json.dumps(final_dic))

                if ACLManager.commandInjectionCheck(finalDic['user']) == 1:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': 'Invalid characters in username'}
                    return HttpResponse(json.dumps(final_dic))

                # SECURITY: Validate port is numeric
                try:
                    port_int = int(finalDic['port'])
                    if port_int < 1 or port_int > 65535:
                        raise ValueError("Port out of range")
                except ValueError:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': 'Port must be a valid number (1-65535)'}
                    return HttpResponse(json.dumps(final_dic))

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
                execPath = execPath + " submitDestinationCreation --ipAddress " + shlex.quote(finalDic['ipAddress']) + " --password " \
                           + shlex.quote(finalDic['password']) + " --port " + shlex.quote(finalDic['port']) + ' --user %s' % (shlex.quote(finalDic['user']))

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(execPath)

                output = ProcessUtilities.outputExecutioner(execPath)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(output)

                if output.find('1,') > -1:

                    config = {'type': data['type'], 'ip': data['IPAddress'], 'username': data['userName'],
                              'port': data['backupSSHPort'], 'path': data['path']}
                    nd = NormalBackupDests(name=data['name'], config=json.dumps(config))
                    nd.save()

                    final_dic = {'status': 1, 'destStatus': 1, 'error_message': "None"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'status': 0, 'destStatus': 0, 'error_message': output}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                config = {'type': data['type'], 'path': data['path']}
                nd = NormalBackupDests(name=data['name'], config=json.dumps(config))
                nd.save()

                final_dic = {'status': 1, 'destStatus': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'status': 0, 'destStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getCurrentBackupDestinations(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            destinations = NormalBackupDests.objects.all()

            json_data = "["
            checker = 0

            for items in destinations:

                config = json.loads(items.config)

                if config['type'] == data['type']:
                    if config['type'] == 'SFTP':
                        dic = {
                            'name': items.name,
                            'ip': config['ip'],
                            'username': config['username'],
                            'path': config['path'],
                            'port': config['port'],
                        }
                    else:
                        dic = {
                            'name': items.name,
                            'path': config['path'],
                        }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getConnectionStatus(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('connStatus', 0)

            ipAddress = data['IPAddress']

            # SECURITY: Validate IP address to prevent command injection
            if ACLManager.commandInjectionCheck(ipAddress) == 1:
                final_dic = {'connStatus': 0, 'error_message': 'Invalid characters in IP address'}
                return HttpResponse(json.dumps(final_dic))

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " getConnectionStatus --ipAddress " + shlex.quote(ipAddress)

            output = ProcessUtilities.executioner(execPath)

            if output.find('1,') > -1:
                final_dic = {'connStatus': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'connStatus': 0, 'error_message': output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'connStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteDestination(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('delStatus', 0)

            nameOrPath = data['nameOrPath']
            type = data['type']

            NormalBackupDests.objects.get(name=nameOrPath).delete()

            final_dic = {'status': 1, 'delStatus': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def scheduleBackup(self, request, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            
            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadError()
            
            destinations = NormalBackupDests.objects.all()
            dests = []
            for dest in destinations:
                dests.append(dest.name)
            websitesName = ACLManager.findAllSites(currentACL, userID)
            proc = httpProc(request, 'backup/backupSchedule.html', {'destinations': dests, 'websites': websitesName},
                            'scheduleBackups')
            return proc.render()
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [scheduleBackup]')
            return HttpResponse("Error: " + str(msg))

    def getCurrentBackupSchedules(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            records = backupSchedules.objects.all()

            json_data = "["
            checker = 0

            for items in records:
                dic = {'id': items.id,
                       'destLoc': items.dest.destLoc,
                       'frequency': items.frequency,
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def submitBackupSchedule(self, userID=None, data=None):
        try:
            selectedAccount = data['selectedAccount']
            name = data['name']
            backupFrequency = data['backupFrequency']
            backupRetention = data['backupRetention']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            nbd = NormalBackupDests.objects.get(name=selectedAccount)

            config = {'frequency': backupFrequency,
                      'retention': backupRetention}

            # Check if a job with this name already exists
            existing_job = NormalBackupJobs.objects.filter(name=name).first()
            if existing_job:
                # Update existing job instead of creating a new one
                existing_job.owner = nbd
                existing_job.config = json.dumps(config)
                existing_job.save()
            else:
                # Create new job
                nbj = NormalBackupJobs(owner=nbd, name=name, config=json.dumps(config))
                nbj.save()

            final_json = json.dumps({'status': 1, 'scheduleStatus': 0})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'scheduleStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def scheduleDelete(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            backupDest = data['destLoc']
            backupFreq = data['frequency']
            findTxt = ""

            if backupDest == "Home" and backupFreq == "Daily":
                findTxt = "0 3"
            elif backupDest == "Home" and backupFreq == "Weekly":
                findTxt = "0 0"
            elif backupDest != "Home" and backupFreq == "Daily":
                findTxt = "0 3"
            elif backupDest != "Home" and backupFreq == "Weekly":
                findTxt = "0 0"

            ###

            logging.CyberCPLogFileWriter.writeToFile(findTxt)
            logging.CyberCPLogFileWriter.writeToFile(backupFreq)

            path = "/etc/crontab"

            command = "cat " + path
            output = ProcessUtilities.outputExecutioner(command).split('\n')
            tempCronPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempCronPath, 'w')

            for items in output:
                if (items.find(findTxt) > -1 and items.find("backupScheduleLocal.py") > -1) or (
                        items.find(findTxt) > -1 and items.find('backupSchedule.py')):
                    continue
                else:
                    writeToFile.writelines(items + '\n')

            writeToFile.close()

            command = "sudo mv " + tempCronPath + " " + path
            ProcessUtilities.executioner(command)

            command = 'chown root:root %s' % (path)
            ProcessUtilities.executioner(command)

            command = "sudo systemctl restart crond"
            ProcessUtilities.executioner(command)

            destination = dest.objects.get(destLoc=backupDest)
            newSchedule = backupSchedules.objects.get(dest=destination, frequency=backupFreq)
            newSchedule.delete()

            final_json = json.dumps({'delStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_json = json.dumps({'delStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def remoteBackups(self, request, userID=None, data=None):
        proc = httpProc(request, 'backup/remoteBackups.html', None, 'remoteBackups')
        return proc.render()

    def submitRemoteBackups(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson()

            ipAddress = data['ipAddress']
            password = data['password']

            ## Ask for Remote version of CyberPanel

            try:
                finalData = json.dumps({'username': "admin", "password": password})

                url = "https://" + ipAddress + ":8090/api/cyberPanelVersion"

                r = requests.post(url, data=finalData, verify=False)

                data = json.loads(r.text)

                if data['getVersion'] == 1:

                    if float(data['currentVersion']) >= 1.6 and data['build'] >= 0:
                        pass
                    else:
                        data_ret = {'status': 0,
                                    'error_message': "Your version does not match with version of remote server.",
                                    "dir": "Null"}
                        data_ret = json.dumps(data_ret)
                        return HttpResponse(data_ret)
                else:
                    data_ret = {'status': 0,
                                'error_message': "Not able to fetch version of remote server. Error Message: " +
                                                 data[
                                                     'error_message'], "dir": "Null"}
                    data_ret = json.dumps(data_ret)
                    return HttpResponse(data_ret)


            except BaseException as msg:
                data_ret = {'status': 0,
                            'error_message': "Not able to fetch version of remote server. Error Message: " + str(
                                msg),
                            "dir": "Null"}
                data_ret = json.dumps(data_ret)
                return HttpResponse(data_ret)

            ## Fetch public key of remote server!

            finalData = json.dumps({'username': "admin", "password": password})

            url = "https://" + ipAddress + ":8090/api/fetchSSHkey"
            r = requests.post(url, data=finalData, verify=False)
            data = json.loads(r.text)

            if data['pubKeyStatus'] == 1:
                pubKey = data["pubKey"].strip("\n")
            else:
                final_json = json.dumps({'status': 0,
                                         'error_message': "I am sorry, I could not fetch key from remote server. Error Message: " +
                                                          data['error_message']
                                         })
                return HttpResponse(final_json)

            ## write key

            ## Writing key to a temporary location, to be read later by backup process.

            mailUtilities.checkHome()

            pathToKey = "/home/cyberpanel/" + str(randint(1000, 9999))

            vhost = open(pathToKey, "w")
            vhost.write(pubKey)
            vhost.close()

            ##

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
            execPath = execPath + " writeAuthKey --pathToKey " + pathToKey
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                pass
            else:
                final_json = json.dumps({'status': 0, 'error_message': output})
                return HttpResponse(final_json)

            ##

            try:
                finalData = json.dumps({'username': "admin", "password": password})

                url = "https://" + ipAddress + ":8090/api/fetchAccountsFromRemoteServer"

                r = requests.post(url, data=finalData, verify=False)

                data = json.loads(r.text)

                if data['fetchStatus'] == 1:
                    json_data = data['data']
                    data_ret = {'status': 1, 'error_message': "None",
                                "dir": "Null", 'data': json_data}
                    data_ret = json.dumps(data_ret)
                    return HttpResponse(data_ret)
                else:
                    data_ret = {'status': 0,
                                'error_message': "Not able to fetch accounts from remote server. Error Message: " +
                                                 data['error_message'], "dir": "Null"}
                    data_ret = json.dumps(data_ret)
                    return HttpResponse(data_ret)
            except BaseException as msg:
                data_ret = {'status': 0,
                            'error_message': "Not able to fetch accounts from remote server. Error Message: " + str(
                                msg), "dir": "Null"}
                data_ret = json.dumps(data_ret)
                return HttpResponse(data_ret)

        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def starRemoteTransfer(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('remoteTransferStatus', 0)

            ipAddress = data['ipAddress']
            password = data['password']
            accountsToTransfer = data['accountsToTransfer']

            try:

                #this command is for enable permit root login over SSH:
                command = "sudo sed -i 's/^PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config && sudo service ssh restart"
                ProcessUtilities.executioner(command, None, True)


                # this command is for enable permit root login over SSH:
                command = "sudo sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && sudo systemctl restart sshd"
                ProcessUtilities.executioner(command, None, True)

                # this command is for get port of SSH:
                command = """grep -oP '^Port \K\d+' /etc/ssh/sshd_config | head -n 1"""
                output = ProcessUtilities.outputExecutioner(command)
                port = output.strip('\n')


                ### if value of port return empty then int function fails which means port is not set so defaults to 22
                try:
                    portT = int(port)
                except:
                    port = '22'


                ipFile = os.path.join("/etc", "cyberpanel", "machineIP")
                f = open(ipFile)
                ownIP = f.read()

                finalData = json.dumps({'username': "admin", "password": password, "ipAddress": ownIP,
                                        "accountsToTransfer": accountsToTransfer, 'port': port})

                url = "https://" + ipAddress + ":8090/api/remoteTransfer"

                r = requests.post(url, data=finalData, verify=False)

                if os.path.exists('/usr/local/CyberCP/debug'):
                    message = 'Remote transfer initiation status: %s' % (r.text)
                    logging.CyberCPLogFileWriter.writeToFile(message)

                data = json.loads(r.text)

                if data['transferStatus'] == 1:

                    ## Create local backup dir

                    localBackupDir = os.path.join("/home", "backup")

                    if not os.path.exists(localBackupDir):
                        command = "sudo mkdir " + localBackupDir
                        ProcessUtilities.executioner(command)

                    ## create local directory that will host backups

                    localStoragePath = "/home/backup/transfer-" + str(data['dir'])

                    ## making local storage directory for backups

                    command = "sudo mkdir " + localStoragePath
                    ProcessUtilities.executioner(command)

                    command = 'chmod 600 %s' % (localStoragePath)
                    ProcessUtilities.executioner(command)

                    final_json = json.dumps(
                        {'remoteTransferStatus': 1, 'error_message': "None", "dir": data['dir']})
                    return HttpResponse(final_json)
                else:
                    final_json = json.dumps({'remoteTransferStatus': 0,
                                             'error_message': "Can not initiate remote transfer. Error message: " +
                                                              data['error_message']})
                    return HttpResponse(final_json)

            except BaseException as msg:
                final_json = json.dumps({'remoteTransferStatus': 0,
                                         'error_message': "Can not initiate remote transfer. Error message: " +
                                                          str(msg)})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_json = json.dumps({'remoteTransferStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def getRemoteTransferStatus(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('remoteTransferStatus', 0)

            ipAddress = data['ipAddress']
            password = data['password']
            dir = data['dir']
            username = "admin"

            finalData = json.dumps({'dir': dir, "username": username, "password": password})
            r = requests.post("https://" + ipAddress + ":8090/api/FetchRemoteTransferStatus", data=finalData,
                              verify=False)

            data = json.loads(r.text)

            if data['fetchStatus'] == 1:
                if data['status'].find("Backups are successfully generated and received on") > -1:

                    data = {'remoteTransferStatus': 1, 'error_message': "None", "status": data['status'],
                            'backupsSent': 1}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)
                elif data['status'].find("[5010]") > -1:
                    data = {'remoteTransferStatus': 0, 'error_message': data['status'],
                            'backupsSent': 0}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)
                else:
                    data = {'remoteTransferStatus': 1, 'error_message': "None", "status": data['status'],
                            'backupsSent': 0}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)
            else:
                data = {'remoteTransferStatus': 0, 'error_message': data['error_message'],
                        'backupsSent': 0}
                json_data = json.dumps(data)
                return HttpResponse(json_data)
        except BaseException as msg:
            data = {'remoteTransferStatus': 0, 'error_message': str(msg), 'backupsSent': 0}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def remoteBackupRestore(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('remoteTransferStatus', 0)

            backupDir = str(data['backupDir'])

            # SECURITY: Validate backupDir to prevent command injection and path traversal
            if ACLManager.commandInjectionCheck(backupDir) == 1:
                data = {'remoteRestoreStatus': 0, 'error_message': 'Invalid characters in backup directory name'}
                return HttpResponse(json.dumps(data))

            # SECURITY: Ensure backupDir is alphanumeric only (backup dirs are typically numeric IDs)
            if not re.match(r'^[a-zA-Z0-9_-]+$', backupDir):
                data = {'remoteRestoreStatus': 0, 'error_message': 'Backup directory name must be alphanumeric'}
                return HttpResponse(json.dumps(data))

            # SECURITY: Prevent path traversal
            if '..' in backupDir or '/' in backupDir:
                data = {'remoteRestoreStatus': 0, 'error_message': 'Invalid backup directory path'}
                return HttpResponse(json.dumps(data))

            backupDirComplete = "/home/backup/transfer-" + backupDir

            # SECURITY: Verify the backup directory exists
            if not os.path.exists(backupDirComplete):
                data = {'remoteRestoreStatus': 0, 'error_message': 'Backup directory does not exist'}
                return HttpResponse(json.dumps(data))

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
            execPath = execPath + " remoteBackupRestore --backupDirComplete " + shlex.quote(backupDirComplete) + " --backupDir " + shlex.quote(backupDir)

            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(3)

            data = {'remoteRestoreStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

        except BaseException as msg:
            data = {'remoteRestoreStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def localRestoreStatus(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('remoteTransferStatus', 0)

            backupDir = str(data['backupDir'])

            # SECURITY: Validate backupDir to prevent command injection and path traversal
            if ACLManager.commandInjectionCheck(backupDir) == 1:
                data = {'remoteTransferStatus': 0, 'error_message': 'Invalid characters in backup directory name', "status": "None", "complete": 0}
                return HttpResponse(json.dumps(data))

            # SECURITY: Ensure backupDir is alphanumeric only
            if not re.match(r'^[a-zA-Z0-9_-]+$', backupDir):
                data = {'remoteTransferStatus': 0, 'error_message': 'Backup directory name must be alphanumeric', "status": "None", "complete": 0}
                return HttpResponse(json.dumps(data))

            # SECURITY: Prevent path traversal
            if '..' in backupDir or '/' in backupDir:
                data = {'remoteTransferStatus': 0, 'error_message': 'Invalid backup directory path', "status": "None", "complete": 0}
                return HttpResponse(json.dumps(data))

            # admin = Administrator.objects.get(userName=username)
            backupLogPath = "/home/backup/transfer-" + backupDir + "/" + "backup_log"
            removalPath = "/home/backup/transfer-" + backupDir

            # SECURITY: Verify the backup directory exists before operating on it
            if not os.path.exists(removalPath):
                data = {'remoteTransferStatus': 0, 'error_message': 'Backup directory does not exist', "status": "None", "complete": 0}
                return HttpResponse(json.dumps(data))

            time.sleep(3)

            command = "sudo cat " + shlex.quote(backupLogPath)
            status = ProcessUtilities.outputExecutioner(command)


            if status.find("Error") > -1:
                Error_find = "There was an error during the backup process. Please review the log for more information."
                status = status + Error_find



            if status.find("completed[success]") > -1:
                command = "rm -rf " + shlex.quote(removalPath)
                ProcessUtilities.executioner(command)
                data_ret = {'remoteTransferStatus': 1, 'error_message': "None", "status": status, "complete": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            elif status.find("[5010]") > -1:
                command = "sudo rm -rf " + shlex.quote(removalPath)
                ProcessUtilities.executioner(command)
                data = {'remoteTransferStatus': 0, 'error_message': status,
                        "status": "None", "complete": 0}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            else:
                data_ret = {'remoteTransferStatus': 1, 'error_message': "None", "status": status, "complete": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data = {'remoteTransferStatus': 0, 'error_message': str(msg), "status": "None", "complete": 0}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def cancelRemoteBackup(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('cancelStatus', 0)

            ipAddress = data['ipAddress']
            password = data['password']
            dir = data['dir']
            username = "admin"

            finalData = json.dumps({'dir': dir, "username": username, "password": password})
            r = requests.post("https://" + ipAddress + ":8090/api/cancelRemoteTransfer", data=finalData,
                              verify=False)

            data = json.loads(r.text)

            if data['cancelStatus'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.writeToFile(
                    "Some error cancelling at remote server, see the log file for remote server.")

            path = "/home/backup/transfer-" + str(dir)
            pathpid = path + "/pid"

            command = "sudo cat " + pathpid
            pid = ProcessUtilities.outputExecutioner(command)

            command = "sudo kill -KILL " + pid
            ProcessUtilities.executioner(command)

            command = "sudo rm -rf " + path
            ProcessUtilities.executioner(command)

            data = {'cancelStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

        except BaseException as msg:
            data = {'cancelStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def backupLogs(self, request=None, userID=None, data=None):
        all_files = []
        logFiles = BackupJob.objects.all().order_by('-id')
        for logFile in logFiles:
            all_files.append(logFile.logFile)
        proc = httpProc(request, 'backup/backupLogs.html', {'backups': all_files}, 'admin')
        return proc.render()

    def fetchLogs(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            page = int(str(data['page']).rstrip('\n'))
            recordsToShow = int(data['recordsToShow'])
            logFile = data['logFile']

            logJob = BackupJob.objects.get(logFile=logFile)

            logs = logJob.backupjoblogs_set.all()

            from s3Backups.s3Backups import S3Backups
            from plogical.backupSchedule import backupSchedule

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            finalLogs = logs[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 0

            for log in finalLogs:

                if log.status == backupSchedule.INFO:
                    status = 'INFO'
                else:
                    status = 'ERROR'

                dic = {
                    'LEVEL': status, "Message": log.message
                }
                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)
                counter = counter + 1

            json_data = json_data + ']'

            if logJob.location == backupSchedule.LOCAL:
                location = 'local'
            else:
                location = 'remote'

            data = {
                'status': 1,
                'error_message': 'None',
                'logs': json_data,
                'pagination': pagination,
                'jobSuccessSites': logJob.jobSuccessSites,
                'jobFailedSites': logJob.jobFailedSites,
                'location': location
            }

            json_data = json.dumps(data)
            return HttpResponse(json_data)

        except BaseException as msg:
            data = {'remoteRestoreStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def fetchgNormalSites(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']
            recordsToShow = int(data['recordsToShow'])
            page = int(str(data['page']).strip('\n'))


            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            try:
                nbd = NormalBackupJobs.objects.get(name=selectedAccount)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbd = NormalBackupJobs.objects.filter(name=selectedAccount).first()

            websites = nbd.normalbackupsites_set.all()

            from s3Backups.s3Backups import S3Backups

            pagination = S3Backups.getPagination(len(websites), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            finalWebsites = websites[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 0

            from plogical.backupSchedule import backupSchedule

            for website in finalWebsites:

                dic = {
                    'name': website.domain.domain
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'

            config = json.loads(nbd.config)

            try:
                lastRun = config[IncScheduler.lastRun]
            except:
                lastRun = 'Never'

            try:
                allSites = config[IncScheduler.allSites]
            except:
                allSites = 'Selected Only'

            try:
                frequency = config[IncScheduler.frequency]
            except:
                frequency = 'Never'

            try:
                retention = config[IncScheduler.retention]
            except:
                retention = 'Never'

            try:
                currentStatus = config[IncScheduler.currentStatus]
            except:
                currentStatus = 'Not running'

            data_ret = {
                'status': 1,
                'websites': json_data,
                'pagination': pagination,
                'lastRun': lastRun,
                'allSites': allSites,
                'currently': frequency,
                'currentStatus': currentStatus
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchNormalJobs(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)

            selectedAccount = data['selectedAccount']

            nbd = NormalBackupDests.objects.get(name=selectedAccount)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            allJobs = nbd.normalbackupjobs_set.all()

            alljbs = []

            for items in allJobs:
                alljbs.append(items.name)

            data_ret = {'status': 1, 'jobs': alljbs}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def addSiteNormal(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            selectedJob = data['selectedJob']
            type = data['type']

            try:
                nbj = NormalBackupJobs.objects.get(name=selectedJob)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbj = NormalBackupJobs.objects.filter(name=selectedJob).first()

            if type == 'all':
                config = json.loads(nbj.config)

                try:
                    if config[IncScheduler.allSites] == 'all':
                        config[IncScheduler.allSites] = 'Selected Only'
                        nbj.config = json.dumps(config)
                        nbj.save()
                        data_ret = {'status': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                except:
                    pass
                config[IncScheduler.allSites] = type
                nbj.config = json.dumps(config)
                nbj.save()

                data_ret = {'status': 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            selectedWebsite = data['selectedWebsite']

            website = Websites.objects.get(domain=selectedWebsite)

            try:
                NormalBackupSites.objects.get(owner=nbj, domain=website)
            except:
                NormalBackupSites(owner=nbj, domain=website).save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteSiteNormal(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)

            selectedJob = data['selectedJob']
            selectedWebsite = data['website']

            try:
                nbj = NormalBackupJobs.objects.get(name=selectedJob)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbj = NormalBackupJobs.objects.filter(name=selectedJob).first()
            website = Websites.objects.get(domain=selectedWebsite)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            try:
                NormalBackupSites.objects.get(owner=nbj, domain=website).delete()
            except:
                pass

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeAccountFrequencyNormal(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedJob = data['selectedJob']
            backupFrequency = data['backupFrequency']


            try:
                nbj = NormalBackupJobs.objects.get(name=selectedJob)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbj = NormalBackupJobs.objects.filter(name=selectedJob).first()

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            config = json.loads(nbj.config)
            config[IncScheduler.frequency] = backupFrequency
            try:
                backupRetention = data['backupRetention']
                config[IncScheduler.retention] = backupRetention
            except:
                pass


            nbj.config = json.dumps(config)
            nbj.save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


    def deleteAccountNormal(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)

            selectedJob = data['selectedJob']

            try:
                nbj = NormalBackupJobs.objects.get(name=selectedJob)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbj = NormalBackupJobs.objects.filter(name=selectedJob).first()

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            nbj.delete()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchNormalLogs(self, request=None, userID=None, data=None):
        try:

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            data = json.loads(request.body)

            selectedJob = data['selectedJob']
            recordsToShow = int(data['recordsToShow'])
            page = int(str(data['page']).strip('\n'))

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            try:
                nbj = NormalBackupJobs.objects.get(name=selectedJob)
            except NormalBackupJobs.MultipleObjectsReturned:
                # If multiple jobs exist with same name, get the first one
                nbj = NormalBackupJobs.objects.filter(name=selectedJob).first()

            logs = nbj.normalbackupjoblogs_set.all().order_by('-id')

            from s3Backups.s3Backups import S3Backups

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            logs = logs[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 0

            from plogical.backupSchedule import backupSchedule

            for log in logs:

                if log.status == backupSchedule.INFO:
                    status = 'INFO'
                else:
                    status = 'ERROR'

                dic = {
                    'type': status,
                    'message': log.message
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'

            data_ret = {'status': 1, 'logs': json_data, 'pagination': pagination}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def CreateV2BackupStatus(self, userID=None, data=None):
        try:
            domain = data['domain']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            statusFile = f'/home/cyberpanel/{domain}_rustic_backup_log'

            if ACLManager.CheckStatusFilleLoc(statusFile, domain):
                pass
            else:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "100",
                            'currentStatus': 'Invalid status file.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            #currentStatus:"cat: /home/cyberpanel/9219: No such file or directory"

            statusData = ProcessUtilities.outputExecutioner("cat " + statusFile).splitlines()

            lastLine = statusData[-1]

            if lastLine.find('[200]') > -1:
                command = 'rm -f ' + statusFile
                subprocess.call(shlex.split(command))
                data_ret = {'abort': 1, 'installStatus': 1, 'installationProgress': "100",
                            'currentStatus': 'Successfully Created.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            elif lastLine.find('[404]') > -1:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0",
                            'error_message': ProcessUtilities.outputExecutioner("cat " + statusFile).splitlines()}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                progress = lastLine.split(',')
                currentStatus = progress[0]
                try:
                    installationProgress = progress[1]
                except:
                    installationProgress = 0
                data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': installationProgress,
                            'currentStatus': currentStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': "0", 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def OneClickBackups(self, request=None, userID=None, data=None):
        user = Administrator.objects.get(pk=userID)

        data = {}

        import requests
        try:
            if request.GET.get('status', 'none') == 'success':
                plan_name = request.GET.get('planName')
                months = request.GET.get('months')
                monthly_price = request.GET.get('monthlyPrice')
                yearly_price = request.GET.get('yearlyPrice')
                customer = request.GET.get('customer')
                subscription = request.GET.get('subscription')

                from IncBackups.models import OneClickBackups

                if months == '1':
                    price = monthly_price
                else:
                    price = yearly_price

                try:

                    userName = user.userName.lower()

                    not_allowed_characters = [
                        ' ', '/', '\\', '@', '!', '#', '$', '%', '^', '&', '*', '(', ')', '+', '=',
                        '{', '}', '[', ']', ':', ';', '"', "'", '<', '>', ',', '?', '|', '`', '~'
                    ]

                    for items in not_allowed_characters:
                        userName = userName.replace(items, '')

                    import plogical.randomPassword as randomPassword

                    backup_plan = OneClickBackups(
                        owner=user,
                        planName=plan_name,
                        months=months,
                        price=price,
                        customer=customer,
                        subscription=subscription,
                        sftpUser=f'{userName}_{randomPassword.generate_pass(8)}'.lower(),
                    )
                    backup_plan.save()

                    ####

                    import requests
                    import json


                    # Define the URL of the endpoint
                    url = 'http://platform.cyberpersons.com/Billing/CreateSFTPAccount'  # Replace with your actual endpoint URL

                    # Define the payload to send in the POST request
                    payload = {
                        'sub': subscription,
                        'key': ProcessUtilities.outputExecutioner(f'cat /root/.ssh/cyberpanel.pub'),  # Replace with the actual SSH public key
                        'sftpUser': backup_plan.sftpUser,
                        'serverIP': ACLManager.fetchIP(), # Replace with the actual server IP,
                        'planName': plan_name
                    }

                    # Convert the payload to JSON format
                    headers = {'Content-Type': 'application/json'}
                    dataRet = json.dumps(payload)

                    # Make the POST request
                    response = requests.post(url, headers=headers, data=dataRet)

                    # Handle the response
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get('status') == 1:

                            ocbkup = OneClickBackups.objects.get(owner=user,subscription=subscription)
                            ocbkup.state = 1
                            ocbkup.save()

                            finalDic = {}

                            finalDic['IPAddress'] = response_data.get('ipAddress')
                            finalDic['password'] = 'NOT-NEEDED'
                            finalDic['backupSSHPort'] = '22'
                            finalDic['userName'] = backup_plan.sftpUser
                            finalDic['type'] = 'SFTP'
                            finalDic['path'] = 'cpbackups'
                            finalDic['name'] = backup_plan.sftpUser

                            wm = BackupManager()
                            response_inner = wm.submitDestinationCreation(userID, finalDic)

                            response_data_inner = json.loads(response_inner.content.decode('utf-8'))

                            # Extract the value of 'status'
                            if response_data_inner.get('status') == 0:
                                data['status'] = 0
                                data[
                                    'message'] = f"[2109] Failed to create sftp account {response_data_inner.get('error_message')}"
                                print("Failed to create SFTP account:", response_data_inner.get('error_message'))
                            else:
                                data['status'] = 1

                        else:
                            data['status'] = 0
                            data['message'] = f"[1985] Failed to create sftp account {response_data.get('error_message')}"
                            print("Failed to create SFTP account:", response_data.get('error_message'))
                    else:
                        print("Failed to connect to the server. Status code:", response.status_code)
                        print("Response:", response.text)
                        data['status'] = 0
                        data['message'] = f"[1991] Failed to create sftp account {response.text}"

                    ####

                except BaseException as msg:
                    data['status'] = 4
                    data['message'] = str(msg)

            elif request.GET.get('status', 'none') == 'cancelled':
                data['status'] = 0
            else:
                data['status'] = 2
        except BaseException as msg:
            data['status'] = 0
            data['message'] = f"[2038] Unkown error occured in purchase process. Error message: {str(msg)}"


        url = 'https://platform.cyberpersons.com/Billing/FetchBackupPlans'

        try:
            response = requests.get(url)
            response.raise_for_status()  # Check if the request was successful
            data['plans'] = response.json()  # Convert the response to a Python dictionary
        except requests.exceptions.HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
        except Exception as err:
            print(f'Other error occurred: {err}')

        data['bPlans'] = user.oneclickbackups_set.all()

        proc = httpProc(request, 'backup/oneClickBackups.html', data, 'addDeleteDestinations')
        return proc.render()

    def ManageOCBackups(self, request=None, userID=None, data=None):
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        from IncBackups.models import OneClickBackups
        ocb = OneClickBackups.objects.get(pk = request.GET.get('id'), owner=admin)
        destinations = [NormalBackupDests.objects.get(name=ocb.sftpUser)]
        dests = []
        for dest in destinations:
            dests.append(dest.name)

        websitesName = ACLManager.findAllSites(currentACL, userID)

        # Fetch storage stats and backup info from platform API
        storage_info = {
            'total_storage': 'N/A',
            'used_storage': 'N/A',
            'available_storage': 'N/A',
            'usage_percentage': 0,
            'last_backup_run': 'Never',
            'last_backup_status': 'N/A',
            'total_backups': 0,
            'failed_backups': 0,
            'error_logs': []
        }

        try:
            import requests
            url = 'https://platform.cyberpersons.com/Billing/GetBackupStats'
            payload = {
                'sub': ocb.subscription,
                'sftpUser': ocb.sftpUser,
                'serverIP': ACLManager.fetchIP()
            }
            headers = {'Content-Type': 'application/json'}

            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

            if response.status_code == 200:
                api_data = response.json()
                if api_data.get('status') == 1:
                    storage_info = api_data.get('data', storage_info)
                    logging.CyberCPLogFileWriter.writeToFile(f'Successfully fetched backup stats for {ocb.sftpUser} [ManageOCBackups]')
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f'Platform API returned error: {api_data.get("error_message")} [ManageOCBackups]')
            else:
                logging.CyberCPLogFileWriter.writeToFile(f'Platform API returned HTTP {response.status_code} [ManageOCBackups]')
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Failed to fetch backup stats: {str(e)} [ManageOCBackups]')

        context = {
            'destination': NormalBackupDests.objects.get(name=ocb.sftpUser).name,
            'websites': websitesName,
            'storage_info': storage_info,
            'ocb_subscription': ocb.subscription,
            'ocb_plan_name': ocb.planName,
            'ocb_sftp_user': ocb.sftpUser
        }

        proc = httpProc(request, 'backup/OneClickBackupSchedule.html', context, 'scheduleBackups')
        return proc.render()

    def RestoreOCBackups(self, request=None, userID=None, data=None):
        try:
            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            from IncBackups.models import OneClickBackups
            
            # Check if an ID was provided
            backup_id = request.GET.get('id')
            if not backup_id:
                # If no ID provided, redirect to manage backups page
                from django.shortcuts import redirect
                return redirect('/backup/ManageOCBackups')
            
            try:
                ocb = OneClickBackups.objects.get(pk=backup_id, owner=admin)
            except OneClickBackups.DoesNotExist:
                return ACLManager.loadErrorJson('restoreStatus', 0)
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [RestoreOCBackups]')
            return HttpResponse("Error: " + str(msg))

        # Load the private key
        finalDirs = []
        
        try:
            nbd = NormalBackupDests.objects.get(name=ocb.sftpUser)
            ip = json.loads(nbd.config)['ip']
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Failed to get backup destination: {str(e)} [RestoreOCBackups]")
            return HttpResponse(f"Error: Failed to get backup destination configuration. {str(e)}")

        # Connect to the remote server using the private key
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Read the private key content
            private_key_path = '/root/.ssh/cyberpanel'
            
            # Check if file exists using ProcessUtilities (runs with proper privileges)
            check_exists = ProcessUtilities.outputExecutioner(f'test -f {private_key_path} && echo "EXISTS" || echo "NOT_EXISTS"').strip()
            
            if check_exists == "NOT_EXISTS":
                logging.CyberCPLogFileWriter.writeToFile(f"SSH key not found at {private_key_path} [RestoreOCBackups]")
                return HttpResponse(f"Error: SSH key not found at {private_key_path}. Please ensure One-click Backup is properly configured.")
            
            # Read the key content using ProcessUtilities
            key_content = ProcessUtilities.outputExecutioner(f'sudo cat {private_key_path}').rstrip('\n')
            
            if not key_content or key_content.startswith('cat:'):
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to read SSH key at {private_key_path} [RestoreOCBackups]")
                return HttpResponse(f"Error: Could not read SSH key at {private_key_path}. Please check permissions.")

            # Load the private key from the content
            key_file = StringIO(key_content)
            
            # Try different key types
            key = None
            try:
                key = paramiko.RSAKey.from_private_key(key_file)
            except:
                try:
                    key_file.seek(0)
                    key = paramiko.Ed25519Key.from_private_key(key_file)
                except:
                    try:
                        key_file.seek(0)
                        key = paramiko.ECDSAKey.from_private_key(key_file)
                    except:
                        key_file.seek(0)
                        key = paramiko.DSSKey.from_private_key(key_file)
            
            # Connect to the server using the private key
            ssh.connect(ip, username=ocb.sftpUser, pkey=key, timeout=30)
            
            # Command to list directories under the specified path
            command = f"ls -d cpbackups/*/ 2>/dev/null || echo 'NO_DIRS_FOUND'"

            # Execute the command
            stdin, stdout, stderr = ssh.exec_command(command)

            # Read the results
            output = stdout.read().decode().strip()
            
            if output == 'NO_DIRS_FOUND' or not output:
                finalDirs = []
            else:
                directories = output.splitlines()
                # Print directories
                for directory in directories:
                    if directory and '/' in directory:
                        finalDirs.append(directory.split('/')[1])
                        
        except paramiko.AuthenticationException as e:
            logging.CyberCPLogFileWriter.writeToFile(f"SSH Authentication failed: {str(e)} [RestoreOCBackups]")
            return HttpResponse("Error: SSH Authentication failed. Please check your One-click Backup configuration.")
        except paramiko.SSHException as e:
            logging.CyberCPLogFileWriter.writeToFile(f"SSH Connection failed: {str(e)} [RestoreOCBackups]")
            return HttpResponse(f"Error: Failed to connect to backup server: {str(e)}")
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Unexpected error during SSH operation: {str(e)} [RestoreOCBackups]")
            return HttpResponse(f"Error: Failed to retrieve backup list: {str(e)}")
        finally:
            try:
                ssh.close()
            except:
                pass

        proc = httpProc(request, 'backup/restoreOCBackups.html', {'directories': finalDirs},
                        'scheduleBackups')
        return proc.render()

    def fetchOCSites(self, request=None, userID=None, data=None):
        ssh = None
        try:
            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            data = json.loads(request.body)
            id = data['idValue']
            folder = data['folder']

            admin = Administrator.objects.get(pk=userID)
            from IncBackups.models import OneClickBackups

            try:
                ocb = OneClickBackups.objects.get(pk=id, owner=admin)
            except OneClickBackups.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f"OneClickBackup with id {id} not found for user {userID} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': 'Backup plan not found or you do not have permission to access it.'}
                return HttpResponse(json.dumps(data_ret))

            # Load backup destination configuration
            try:
                nbd = NormalBackupDests.objects.get(name=ocb.sftpUser)
                ip = json.loads(nbd.config)['ip']
            except NormalBackupDests.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f"Backup destination {ocb.sftpUser} not found [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': 'Backup destination not configured. Please deploy your backup account first.'}
                return HttpResponse(json.dumps(data_ret))
            except (KeyError, json.JSONDecodeError) as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Invalid backup destination config for {ocb.sftpUser}: {str(e)} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': 'Backup destination configuration is invalid. Please reconfigure your backup account.'}
                return HttpResponse(json.dumps(data_ret))

            # Read and validate SSH private key
            private_key_path = '/root/.ssh/cyberpanel'

            # Check if SSH key exists
            check_exists = ProcessUtilities.outputExecutioner(f'test -f {private_key_path} && echo "EXISTS" || echo "NOT_EXISTS"').strip()

            if check_exists == "NOT_EXISTS":
                logging.CyberCPLogFileWriter.writeToFile(f"SSH key not found at {private_key_path} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': f'SSH key not found at {private_key_path}. Please ensure One-click Backup is properly configured.'}
                return HttpResponse(json.dumps(data_ret))

            # Read the key content
            key_content = ProcessUtilities.outputExecutioner(f'sudo cat {private_key_path}').rstrip('\n')

            if not key_content or key_content.startswith('cat:'):
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to read SSH key at {private_key_path} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': f'Could not read SSH key at {private_key_path}. Please check permissions.'}
                return HttpResponse(json.dumps(data_ret))

            # Load the private key with support for multiple key types
            key_file = StringIO(key_content)
            key = None

            try:
                key = paramiko.RSAKey.from_private_key(key_file)
            except:
                try:
                    key_file.seek(0)
                    key = paramiko.Ed25519Key.from_private_key(key_file)
                except:
                    try:
                        key_file.seek(0)
                        key = paramiko.ECDSAKey.from_private_key(key_file)
                    except:
                        try:
                            key_file.seek(0)
                            key = paramiko.DSSKey.from_private_key(key_file)
                        except Exception as e:
                            logging.CyberCPLogFileWriter.writeToFile(f"Failed to load SSH key: {str(e)} [fetchOCSites]")
                            data_ret = {'status': 0, 'error_message': 'Failed to load SSH key. The key format may be unsupported or corrupted.'}
                            return HttpResponse(json.dumps(data_ret))

            # Connect to the remote server
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(ip, username=ocb.sftpUser, pkey=key, timeout=30)
            except paramiko.AuthenticationException as e:
                logging.CyberCPLogFileWriter.writeToFile(f"SSH Authentication failed for {ocb.sftpUser}@{ip}: {str(e)} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': 'SSH Authentication failed. Your backup account credentials may have changed. Please try redeploying your backup account.'}
                return HttpResponse(json.dumps(data_ret))
            except paramiko.SSHException as e:
                logging.CyberCPLogFileWriter.writeToFile(f"SSH Connection failed to {ip}: {str(e)} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': f'Failed to connect to backup server: {str(e)}. Please check your network connection and try again.'}
                return HttpResponse(json.dumps(data_ret))
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Unexpected SSH error connecting to {ip}: {str(e)} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': f'Connection to backup server failed: {str(e)}'}
                return HttpResponse(json.dumps(data_ret))

            # Execute command to list backup files
            command = f"ls -d cpbackups/{folder}/* 2>/dev/null || echo 'NO_FILES_FOUND'"

            try:
                stdin, stdout, stderr = ssh.exec_command(command)
                output = stdout.read().decode().strip()
                error_output = stderr.read().decode().strip()

                if output == 'NO_FILES_FOUND' or not output:
                    # No backups found in this folder
                    data_ret = {'status': 1, 'finalDirs': []}
                    return HttpResponse(json.dumps(data_ret))

                directories = output.splitlines()
                finalDirs = []

                # Extract backup names from paths
                for directory in directories:
                    if directory and '/' in directory:
                        try:
                            # Extract the backup filename from path: cpbackups/{folder}/{backup_name}
                            parts = directory.split('/')
                            if len(parts) >= 3:
                                finalDirs.append(parts[2])
                        except (IndexError, ValueError) as e:
                            logging.CyberCPLogFileWriter.writeToFile(f"Failed to parse directory path '{directory}': {str(e)} [fetchOCSites]")
                            continue

                data_ret = {'status': 1, 'finalDirs': finalDirs}
                return HttpResponse(json.dumps(data_ret))

            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to execute command on remote server: {str(e)} [fetchOCSites]")
                data_ret = {'status': 0, 'error_message': f'Failed to list backups: {str(e)}'}
                return HttpResponse(json.dumps(data_ret))

        except json.JSONDecodeError as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Invalid JSON in request: {str(e)} [fetchOCSites]")
            data_ret = {'status': 0, 'error_message': 'Invalid request format.'}
            return HttpResponse(json.dumps(data_ret))
        except KeyError as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Missing required field in request: {str(e)} [fetchOCSites]")
            data_ret = {'status': 0, 'error_message': f'Missing required field: {str(e)}'}
            return HttpResponse(json.dumps(data_ret))
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(f"Unexpected error in fetchOCSites: {str(msg)}")
            data_ret = {'status': 0, 'error_message': f'An unexpected error occurred: {str(msg)}'}
            return HttpResponse(json.dumps(data_ret))
        finally:
            # Always close SSH connection
            if ssh:
                try:
                    ssh.close()
                except:
                    pass

    def StartOCRestore(self, request=None, userID=None, data=None):
        try:
            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(request.body)
            id = data['idValue']
            folder = data['folder']
            backupfile = data['backupfile']


            extraArgs = {}
            extraArgs['id'] = id
            extraArgs['folder'] = folder
            extraArgs['backupfile'] = backupfile
            extraArgs['userID'] = userID
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            statusFile = open(extraArgs['tempStatusPath'], 'w')
            statusFile.writelines("Restore started..")
            statusFile.close()

            background = ApplicationInstaller('StartOCRestore', extraArgs)
            background.start()

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def DeployAccount(self, request=None, userID=None, data=None):
        """Deploy a One-Click Backup account by creating SFTP credentials on remote server"""
        try:
            user = Administrator.objects.get(pk=userID)
            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            # Parse request data
            try:
                data = json.loads(request.body)
                backup_id = data['id']
            except (json.JSONDecodeError, KeyError) as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Invalid request data in DeployAccount: {str(e)}")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': 'Invalid request format. Missing required field: id'
                }))

            # Get backup plan
            from IncBackups.models import OneClickBackups
            try:
                ocb = OneClickBackups.objects.get(pk=backup_id, owner=user)
            except OneClickBackups.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f"OneClickBackup {backup_id} not found for user {userID} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': 'Backup plan not found or you do not have permission to access it.'
                }))

            # Check if already deployed
            if ocb.state == 1:
                logging.CyberCPLogFileWriter.writeToFile(f"Backup plan {backup_id} already deployed [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 1,
                    'error_message': 'This backup account is already deployed.'
                }))

            # Read SSH public key
            try:
                ssh_pub_key = ProcessUtilities.outputExecutioner('cat /root/.ssh/cyberpanel.pub').strip()
                if not ssh_pub_key or ssh_pub_key.startswith('cat:'):
                    raise Exception("Failed to read SSH public key")
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to read SSH public key: {str(e)} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': 'SSH public key not found. Please ensure One-Click Backup is properly configured.'
                }))

            # Prepare API request
            url = 'https://platform.cyberpersons.com/Billing/CreateSFTPAccount'
            payload = {
                'sub': ocb.subscription,
                'key': ssh_pub_key,
                'sftpUser': ocb.sftpUser,
                'serverIP': ACLManager.fetchIP(),
                'planName': ocb.planName
            }
            headers = {'Content-Type': 'application/json'}

            # Make API request
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            except requests.exceptions.RequestException as e:
                logging.CyberCPLogFileWriter.writeToFile(f"API request failed: {str(e)} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': f'Failed to connect to backup platform: {str(e)}'
                }))

            # Handle non-200 responses
            if response.status_code != 200:
                logging.CyberCPLogFileWriter.writeToFile(f"API returned status {response.status_code}: {response.text} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': f'Backup platform returned error (HTTP {response.status_code}). Please try again later.'
                }))

            # Parse API response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                logging.CyberCPLogFileWriter.writeToFile(f"Invalid JSON response from API: {response.text} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': 'Received invalid response from backup platform.'
                }))

            # Check if deployment was successful or already deployed
            api_status = response_data.get('status')
            api_error = response_data.get('error_message', '')

            if api_status == 1 or api_error == "Already deployed.":
                # Both cases are success - account exists and is ready
                deployment_status = "created" if api_status == 1 else "already deployed"
                logging.CyberCPLogFileWriter.writeToFile(f"SFTP account {deployment_status} for {ocb.sftpUser} [DeployAccount]")

                # Update backup plan state
                ocb.state = 1
                ocb.save()

                # Create local backup destination
                finalDic = {
                    'IPAddress': response_data.get('ipAddress'),
                    'password': 'NOT-NEEDED',
                    'backupSSHPort': '22',
                    'userName': ocb.sftpUser,
                    'type': 'SFTP',
                    'path': 'cpbackups',
                    'name': ocb.sftpUser
                }

                try:
                    wm = BackupManager()
                    response_inner = wm.submitDestinationCreation(userID, finalDic)
                    response_data_inner = json.loads(response_inner.content.decode('utf-8'))

                    if response_data_inner.get('status') == 0:
                        # Destination creation failed, but account is deployed
                        logging.CyberCPLogFileWriter.writeToFile(
                            f"Destination creation failed: {response_data_inner.get('error_message')} [DeployAccount]"
                        )
                        return HttpResponse(json.dumps({
                            'status': 0,
                            'error_message': f"Account deployed but failed to create local destination: {response_data_inner.get('error_message')}"
                        }))

                    # Full success
                    return HttpResponse(json.dumps({
                        'status': 1,
                        'message': f'Backup account {deployment_status} successfully.'
                    }))

                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Failed to create destination: {str(e)} [DeployAccount]")
                    return HttpResponse(json.dumps({
                        'status': 0,
                        'error_message': f'Account deployed but failed to create local destination: {str(e)}'
                    }))

            else:
                # API returned an error
                logging.CyberCPLogFileWriter.writeToFile(f"API returned error: {api_error} [DeployAccount]")
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error_message': api_error or 'Unknown error occurred during deployment.'
                }))

        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Unexpected error in DeployAccount: {str(e)}")
            return HttpResponse(json.dumps({
                'status': 0,
                'error_message': f'An unexpected error occurred: {str(e)}'
            }))

    def ReconfigureSubscription(self, request=None, userID=None, data=None):
        try:
            if not data:
                return JsonResponse({'status': 0, 'error_message': 'No data provided'})

            subscription_id = data['subscription_id']
            customer_id = data['customer_id']
            plan_name = data['plan_name']
            amount = data['amount']
            interval = data['interval']

            # Call platform API to update SFTP key
            import requests
            import json

            url = 'http://platform.cyberpersons.com/Billing/ReconfigureSubscription'
            
            payload = {
                'subscription_id': subscription_id,
                'key': ProcessUtilities.outputExecutioner(f'cat /root/.ssh/cyberpanel.pub'),
                'serverIP': ACLManager.fetchIP(),
                'email': data['email'],
                'code': data['code']
            }

            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 1:
                    # Create OneClickBackups record
                    from IncBackups.models import OneClickBackups
                    backup_plan = OneClickBackups(
                        owner=Administrator.objects.get(pk=userID),
                        planName=plan_name,
                        months='1' if interval == 'month' else '12',
                        price=amount,
                        customer=customer_id,
                        subscription=subscription_id,
                        sftpUser=response_data.get('sftpUser'),
                        state=1  # Set as active since SFTP is already configured
                    )
                    backup_plan.save()

                    # Create SFTP destination in CyberPanel
                    finalDic = {
                        'IPAddress': response_data.get('ipAddress'),
                        'password': 'NOT-NEEDED',
                        'backupSSHPort': '22',
                        'userName': response_data.get('sftpUser'),
                        'type': 'SFTP',
                        'path': 'cpbackups',
                        'name': response_data.get('sftpUser')
                    }

                    wm = BackupManager()
                    response_inner = wm.submitDestinationCreation(userID, finalDic)
                    response_data_inner = json.loads(response_inner.content.decode('utf-8'))

                    if response_data_inner.get('status') == 0:
                        return JsonResponse({'status': 0, 'error_message': response_data_inner.get('error_message')})

                    return JsonResponse({'status': 1})
                else:
                    return JsonResponse({'status': 0, 'error_message': response_data.get('error_message')})
            else:
                return JsonResponse({'status': 0, 'error_message': f'Platform API error: {response.text}'})

        except Exception as e:
            return JsonResponse({'status': 0, 'error_message': str(e)})


