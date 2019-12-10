#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, Backups, dest, backupSchedules
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
from django.shortcuts import HttpResponse, render
from loginSystem.models import Administrator
from plogical.mailUtilities import mailUtilities
from random import randint
import time
import plogical.backupUtilities as backupUtil
import requests
from plogical.processUtilities import ProcessUtilities
from multiprocessing import Process

class BackupManager:
    localBackupPath = '/home/cyberpanel/localBackupPath'
    def __init__(self, domain = None, childDomain = None):
        self.domain = domain
        self.childDomain = childDomain

    def loadBackupHome(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            return render(request, 'backup/index.html', currentACL)
        except BaseException as msg:
            return HttpResponse(str(msg))

    def backupSite(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createBackup') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)
            return render(request, 'backup/backup.html', {'websiteList': websitesName})
        except BaseException as msg:
            return HttpResponse(str(msg))

    def restoreSite(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'restoreBackup') == 0:
                return ACLManager.loadError()

            path = os.path.join("/home", "backup")

            if not os.path.exists(path):
                return render(request, 'backup/restore.html')
            else:
                all_files = []
                ext = ".tar.gz"

                command = 'sudo chown -R  cyberpanel:cyberpanel ' + path
                ACLManager.executeCall(command)

                files = os.listdir(path)
                for filename in files:
                    if filename.endswith(ext):
                        all_files.append(filename)

                return render(request, 'backup/restore.html', {'backups': all_files})

        except BaseException as msg:
            return HttpResponse(str(msg))

    def getCurrentBackups(self, userID = None, data = None):
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

    def submitBackupCreation(self, userID = None, data = None):
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


            p = Process(target=backupUtil.submitBackupCreation, args=(tempStoragePath, backupName, backupPath,backupDomain))
            p.start()

            time.sleep(2)

            final_json = json.dumps({'status': 1, 'metaStatus': 1, 'error_message': "None", 'tempStorage': tempStoragePath})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def backupStatus(self, userID = None, data = None):
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

    def cancelBackupCreation(self, userID = None, data = None):
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

    def deleteBackup(self, userID = None, data = None):
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

    def submitRestore(self, data = None, userID = None):
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

    def restoreStatus(self, data = None):
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

    def backupDestinations(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadError()

            return render(request, 'backup/backupDestinations.html', {})

        except BaseException as msg:
            return HttpResponse(str(msg))

    def submitDestinationCreation(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('destStatus', 0)

            destinations = backupUtil.backupUtilities.destinationsPath

            ipAddress = data['IPAddress']
            password = data['password']

            if dest.objects.all().count() == 2:
                final_dic = {'destStatus': 0,
                             'error_message': "Currently only one remote destination is allowed."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            try:
                d = dest.objects.get(destLoc=ipAddress)
                final_dic = {'destStatus': 0, 'error_message': "This destination already exists."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            except:

                try:
                    port = data['backupSSHPort']
                except:
                    port = "22"

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
                execPath = execPath + " submitDestinationCreation --ipAddress " + ipAddress + " --password " \
                           + password + " --port " + port

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find('1,') > -1:
                    try:
                        writeToFile = open(destinations, "w")
                        writeToFile.writelines(ipAddress + "\n")
                        writeToFile.writelines(data['backupSSHPort'] + "\n")
                        writeToFile.close()
                        newDest = dest(destLoc=ipAddress)
                        newDest.save()
                    except:
                        writeToFile = open(destinations, "w")
                        writeToFile.writelines(ipAddress + "\n")
                        writeToFile.writelines("22" + "\n")
                        writeToFile.close()
                        newDest = dest(destLoc=ipAddress)
                        newDest.save()

                        final_dic = {'destStatus': 1, 'error_message': "None"}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                else:
                    final_dic = {'destStatus': 0, 'error_message': output}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'destStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getCurrentBackupDestinations(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            records = dest.objects.all()

            json_data = "["
            checker = 0

            for items in records:
                if items.destLoc == "Home":
                    continue
                dic = {'id': items.id,
                       'ip': items.destLoc,
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

    def getConnectionStatus(self, userID = None, data = None):
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

    def deleteDestination(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
                return ACLManager.loadErrorJson('delStatus', 0)

            ipAddress = data['IPAddress']

            delDest = dest.objects.get(destLoc=ipAddress)
            delDest.delete()

            path = "/usr/local/CyberCP/backup/"
            destinations = path + "destinations"

            data = open(destinations, 'r').readlines()

            writeToFile = open(destinations, 'r')

            for items in data:
                if items.find(ipAddress) > -1:
                    continue
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            ## Deleting Cron Tab Entries for this destination

            path = "/etc/crontab"

            data = open(path, 'r').readlines()

            writeToFile = open(path, 'w')

            for items in data:
                if items.find("backupSchedule.py") > -1:
                    continue
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            final_dic = {'delStatus': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'delStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def scheduleBackup(self, request, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
                return ACLManager.loadError()

            if dest.objects.all().count() <= 1:
                try:
                    homeDest = dest(destLoc="Home")
                    homeDest.save()
                except:
                    pass
            backups = dest.objects.all()

            destinations = []

            for items in backups:
                destinations.append(items.destLoc)

            return render(request, 'backup/backupSchedule.html', {'destinations': destinations})

        except BaseException as msg:
            return HttpResponse(str(msg))

    def getCurrentBackupSchedules(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
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

    def submitBackupSchedule(self, userID = None, data = None):
        try:
            backupDest = data['backupDest']
            backupFreq = data['backupFreq']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
                return ACLManager.loadErrorJson('scheduleStatus', 0)

            path = "/etc/crontab"

            ## check if already exists
            try:
                schedule = backupSchedules.objects.get(frequency=backupFreq)

                if schedule.dest.destLoc == backupDest:
                    final_json = json.dumps(
                        {'scheduleStatus': 0, 'error_message': "This schedule already exists"})
                    return HttpResponse(final_json)
                else:
                    if backupDest == "Home" and backupFreq == "Daily":
                        cronJob = "0 3 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupScheduleLocal.py"
                    elif backupDest == "Home" and backupFreq == "Weekly":
                        cronJob = "0 0 * * 0 root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupScheduleLocal.py "
                    elif backupDest != "Home" and backupFreq == "Daily":
                        cronJob = "0 3 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupSchedule.py"
                    elif backupDest != "Home" and backupFreq == "Weekly":
                        cronJob = "0 0 * * 0 root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupSchedule.py "

                    command = "cat " + path
                    output = ProcessUtilities.outputExecutioner(command)

                    finalCronJob = output + cronJob
                    tempCronPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                    writeToFile = open(tempCronPath, 'a')
                    writeToFile.writelines(finalCronJob + "\n")
                    writeToFile.close()

                    command = "mv " + tempCronPath + " " + path
                    ProcessUtilities.executioner(command)

                    command = 'chown root:root %s' % (path)
                    ProcessUtilities.executioner(command)

                    command = "systemctl restart crond"
                    ProcessUtilities.executioner(command)

                    ## Set local path for backup

                    if backupDest == "Home":
                        writeToFile = open(BackupManager.localBackupPath, 'w')
                        writeToFile.write(data['localPath'])
                        writeToFile.close()

                    destination = dest.objects.get(destLoc=backupDest)
                    newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                    newSchedule.save()

                    final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                    return HttpResponse(final_json)
            except:
                if backupDest == "Home" and backupFreq == "Daily":
                    cronJob = "0 3 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupScheduleLocal.py"
                elif backupDest == "Home" and backupFreq == "Weekly":
                    cronJob = "0 0 * * 0 root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupScheduleLocal.py "
                elif backupDest != "Home" and backupFreq == "Daily":
                    cronJob = "0 3 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupSchedule.py"
                elif backupDest != "Home" and backupFreq == "Weekly":
                    cronJob = "0 0 * * 0 root /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupSchedule.py "

                command = "cat " + path
                output = ProcessUtilities.outputExecutioner(command)

                finalCronJob = output + cronJob
                tempCronPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                writeToFile = open(tempCronPath, 'a')
                writeToFile.writelines(finalCronJob + "\n")
                writeToFile.close()

                command = "sudo mv " + tempCronPath + " " + path
                ProcessUtilities.executioner(command)

                command = 'chown root:root %s' % (path)
                ProcessUtilities.executioner(command)

                command = "sudo systemctl restart crond"
                ProcessUtilities.executioner(command)

                destination = dest.objects.get(destLoc=backupDest)
                newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                newSchedule.save()

                ## Set local path for backup

                if backupDest == "Home":
                    writeToFile = open(BackupManager.localBackupPath, 'w')
                    writeToFile.write(data['localPath'])
                    writeToFile.close()

                final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_json = json.dumps({'scheduleStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def scheduleDelete(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
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
                if (items.find(findTxt) > -1 and items.find("backupScheduleLocal.py") > -1) or (items.find(findTxt) > -1 and items.find('backupSchedule.py')):
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

    def remoteBackups(self, request, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadError()

            return render(request, 'backup/remoteBackups.html')

        except BaseException as msg:
            return HttpResponse(str(msg))

    def submitRemoteBackups(self, userID = None, data = None):
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

    def starRemoteTransfer(self, userID = None, data = None):
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

    def getRemoteTransferStatus(self, userID = None, data = None):
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

    def remoteBackupRestore(self, userID = None, data = None):
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

    def localRestoreStatus(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'remoteBackups') == 0:
                return ACLManager.loadErrorJson('remoteTransferStatus', 0)

            backupDir = data['backupDir']

            # admin = Administrator.objects.get(userName=username)
            backupLogPath = "/home/backup/transfer-" + backupDir + "/" + "backup_log"

            removalPath = "/home/backup/transfer-" + str(backupDir)

            time.sleep(3)

            if os.path.isfile(backupLogPath):
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
            else:
                data_ret = {'remoteTransferStatus': 0, 'error_message': "No such log found", "status": "None",
                            "complete": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        except BaseException as msg:
            data = {'remoteTransferStatus': 0, 'error_message': str(msg), "status": "None", "complete": 0}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    def cancelRemoteBackup(self, userID = None, data = None):
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
