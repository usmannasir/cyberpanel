#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django

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
        proc = httpProc(request, 'backup/backup.html', {'websiteList': websitesName}, 'createBackup')
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

            execPath = "sudo nice -n 10 /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " submitRestore --backupFile " + backupFile + " --dir " + dir
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
                    execPath = "sudo cat " + path + "/status"
                    status = ProcessUtilities.outputExecutioner(execPath)

                    if status.find("Done") > -1:

                        command = "sudo rm -rf " + path
                        ProcessUtilities.executioner(command)

                        final_json = json.dumps(
                            {'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 1,
                             'running': 'Completed'})
                        return HttpResponse(final_json)
                    elif status.find("[5009]") > -1:
                        ## removing temporarily generated files while restoring
                        command = "sudo rm -rf " + path
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
            final_dic = {'restoreStatus': 0, 'error_message': str(msg)}
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

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
                execPath = execPath + " submitDestinationCreation --ipAddress " + finalDic['ipAddress'] + " --password " \
                           + finalDic['password'] + " --port " + finalDic['port'] + ' --user %s' % (finalDic['user'])

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

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " getConnectionStatus --ipAddress " + ipAddress

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
        currentACL = ACLManager.loadedACL(userID)
        destinations = NormalBackupDests.objects.all()
        dests = []
        for dest in destinations:
            dests.append(dest.name)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'backup/backupSchedule.html', {'destinations': dests, 'websites': websitesName},
                        'scheduleBackups')
        return proc.render()

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

                ipFile = os.path.join("/etc", "cyberpanel", "machineIP")
                f = open(ipFile)
                ownIP = f.read()

                finalData = json.dumps({'username': "admin", "password": password, "ipAddress": ownIP,
                                        "accountsToTransfer": accountsToTransfer})

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

            backupDir = data['backupDir']

            backupDirComplete = "/home/backup/transfer-" + str(backupDir)
            # adminEmail = admin.email

            ##

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
            execPath = execPath + " remoteBackupRestore --backupDirComplete " + backupDirComplete + " --backupDir " + str(
                backupDir)

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

            backupDir = data['backupDir']

            # admin = Administrator.objects.get(userName=username)
            backupLogPath = "/home/backup/transfer-" + backupDir + "/" + "backup_log"

            removalPath = "/home/backup/transfer-" + str(backupDir)

            time.sleep(3)

            command = "sudo cat " + backupLogPath
            status = ProcessUtilities.outputExecutioner(command)

            if status.find("completed[success]") > -1:
                command = "rm -rf " + removalPath
                ProcessUtilities.executioner(command)
                data_ret = {'remoteTransferStatus': 1, 'error_message': "None", "status": status, "complete": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            elif status.find("[5010]") > -1:
                command = "sudo rm -rf " + removalPath
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

            nbd = NormalBackupJobs.objects.get(name=selectedAccount)

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

            nbj = NormalBackupJobs.objects.get(name=selectedJob)

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

            nbj = NormalBackupJobs.objects.get(name=selectedJob)
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
            backupRetention = data['backupRetention']

            nbj = NormalBackupJobs.objects.get(name=selectedJob)

            if ACLManager.currentContextPermission(currentACL, 'scheduleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            config = json.loads(nbj.config)
            config[IncScheduler.frequency] = backupFrequency
            config[IncScheduler.retention] = backupRetention

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

            nbj = NormalBackupJobs.objects.get(name=selectedJob)

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

            nbj = NormalBackupJobs.objects.get(name=selectedJob)

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
