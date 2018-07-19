# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
# Create your views here.
from .models import DBUsers
from loginSystem.models import Administrator
import json
from websiteFunctions.models import Websites,Backups,dest,backupSchedules
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import os
import time
import plogical.backupUtilities as backupUtil
import shlex
import subprocess
import requests
from baseTemplate.models import version
from plogical.virtualHostUtilities import virtualHostUtilities
from random import randint
from plogical.mailUtilities import mailUtilities



def loadBackupHome(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        viewStatus = 1
        if admin.type == 3:
            viewStatus = 0

        return render(request,'backup/index.html',{"viewStatus":viewStatus})
    except KeyError:
        return redirect(loadLoginPage)

def restoreSite(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:

                path = os.path.join("/home","backup")

                if not os.path.exists(path):
                    return render(request, 'backup/restore.html')
                else:
                    all_files = []
                    ext = ".tar.gz"

                    command = 'sudo chown -R  cyberpanel:cyberpanel '+ path

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    files = os.listdir(path)
                    for filename in files:
                            if filename.endswith(ext):
                                all_files.append(filename)

                    return render(request, 'backup/restore.html',{'backups':all_files})

            else:
                return HttpResponse("You should be admin to perform restores.")

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def backupSite(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'backup/backup.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def getCurrentBackups(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                backupDomain = data['websiteToBeBacked']
                website = Websites.objects.get(domain=backupDomain)

                if admin.type != 1:
                    if website.admin != admin:
                        dic = {'fetchStatus': 0, 'error_message': "Only administrator can view this page."}
                        json_data = json.dumps(dic)
                        return HttpResponse(json_data)

                backups = website.backups_set.all()


                json_data = "["
                checker = 0

                for items in backups:
                    if items.status == 0:
                        status="Pending"
                    else:
                        status="Completed"
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
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def submitBackupCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            backupDomain = data['websiteToBeBacked']
            website = Websites.objects.get(domain=backupDomain)

            ## defining paths

            ## /home/example.com/backup
            backupPath = os.path.join("/home",backupDomain,"backup/")
            domainUser = website.externalApp
            backupName = 'backup-' + domainUser + "-" + time.strftime("%I-%M-%S-%a-%b-%Y")

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018
            tempStoragePath = os.path.join(backupPath,backupName)

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " submitBackupCreation --tempStoragePath " + tempStoragePath + " --backupName " \
                       + backupName + " --backupPath " + backupPath + ' --backupDomain ' + backupDomain

            subprocess.Popen(shlex.split(execPath))

            time.sleep(2)

            final_json = json.dumps({'metaStatus': 1, 'error_message': "None", 'tempStorage': tempStoragePath})
            return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)

        return HttpResponse(final_json)

def backupStatus(request):
    try:
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                backupDomain = data['websiteToBeBacked']

                status = os.path.join("/home",backupDomain,"backup/status")

                ## read file name

                try:
                    backupFileNamePath = os.path.join("/home",backupDomain,"backup/backupFileName")
                    command = "sudo cat " + backupFileNamePath
                    fileName = subprocess.check_output(shlex.split(command))
                except:
                    fileName = "Fetching.."

                ## file name read ends

                if os.path.exists(status):
                    command = "sudo cat " + status
                    status = subprocess.check_output(shlex.split(command))

                    if status.find("Completed")> -1:

                        command = 'sudo rm -f ' + status
                        subprocess.call(shlex.split(command))

                        backupOb = Backups.objects.get(fileName=fileName)
                        backupOb.status = 1

                        ## adding backup data to database.
                        try:
                            backupOb.size = str(int(float(os.path.getsize("/home/"+backupDomain+"/backup/"+fileName+".tar.gz"))/(1024.0 * 1024.0)))+"MB"
                            backupOb.save()
                        except:
                            backupOb.size = str(int(os.path.getsize("/home/"+backupDomain+"/backup/"+fileName+".tar.gz")))
                            backupOb.save()

                        final_json = json.dumps({'backupStatus': 1, 'error_message': "None", "status": status,"abort": 1,'fileName': fileName,})
                        return HttpResponse(final_json)

                    elif status.find("[5009]")> -1:
                        ## removing status file, so that backup can re-run
                        try:
                            command = 'sudo rm -f ' + status
                            cmd = shlex.split(command)
                            res = subprocess.call(cmd)

                            backupOb = Backups.objects.get(fileName=fileName)
                            backupOb.delete()
                        except BaseException,msg:
                            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupStatus]")

                        final_json = json.dumps({'backupStatus': 1,'fileName': fileName, 'error_message': "None", "status": status, "abort": 1})
                        return HttpResponse(final_json)
                    else:
                        final_json = json.dumps(
                            {'backupStatus': 1, 'error_message': "None", 'fileName': fileName, "status": status,"abort": 0})
                        return HttpResponse(final_json)
                else:
                    final_json = json.dumps({'backupStatus': 0, 'error_message': "None", "status": 0,"abort": 0})
                    return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'backupStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupStatus]")

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'backupStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupStatus]")
        return HttpResponse(final_json)

def cancelBackupCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                backupCancellationDomain = data['backupCancellationDomain']
                fileName = data['fileName']


                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"

                execPath = execPath + " cancelBackupCreation --backupCancellationDomain " + backupCancellationDomain + " --fileName " + fileName

                subprocess.call(shlex.split(execPath))

                try:
                    backupOb = Backups.objects.get(fileName=fileName)
                    backupOb.delete()
                except BaseException, msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

                final_json = json.dumps({'abortStatus': 1, 'error_message': "None", "status": 0})
                return HttpResponse(final_json)
        except BaseException,msg:
            final_dic = {'abortStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abortStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteBackup(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                backupID = data['backupID']
                backup = Backups.objects.get(id=backupID)

                if admin.type != 1:
                    if backup.website.admin != admin:
                        dic = {'deleteStatus': 0, 'error_message': "Only administrator can view this page."}
                        json_data = json.dumps(dic)
                        return HttpResponse(json_data)

                domainName = backup.website.domain

                path = "/home/"+domainName+"/backup/"+backup.fileName+".tar.gz"

                command = 'sudo rm -f ' + path
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                backup.delete()


                final_json = json.dumps({'deleteStatus': 1, 'error_message': "None", "status": 0})
                return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'deleteStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'deleteStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def submitRestore(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            backupFile = data['backupFile']

            originalFile = "/home/backup/" + backupFile

            if not os.path.exists(originalFile):
                dir = data['dir']
            else:
                dir = "CyberPanelRestore"

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"

            execPath = execPath + " submitRestore --backupFile " + backupFile + " --dir " + dir

            subprocess.Popen(shlex.split(execPath))

            time.sleep(4)

            final_dic = {'restoreStatus': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    except BaseException, msg:
        final_dic = {'restoreStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def restoreStatus(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            backupFile = data['backupFile'].strip(".tar.gz")

            path = os.path.join("/home","backup",data['backupFile'])

            if os.path.exists(path):
                path = os.path.join("/home","backup",backupFile)
            elif os.path.exists(data['backupFile']):
                path = data['backupFile'].strip(".tar.gz")
            else:
                dir = data['dir']
                path = "/home/backup/transfer-" + str(dir) + "/" + backupFile

            if os.path.exists(path):
                try:
                    execPath = "sudo cat " + path + "/status"

                    status = subprocess.check_output(shlex.split(execPath))

                    if status.find("Done") > -1:

                        command = "sudo rm -rf " + path
                        subprocess.call(shlex.split(command))

                        final_json = json.dumps(
                            {'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 1,'running': 'Completed'})
                        return HttpResponse(final_json)
                    elif status.find("[5009]") > -1:
                        ## removing temporarily generated files while restoring
                        command = "sudo rm -rf " + path
                        subprocess.call(shlex.split(command))
                        final_json = json.dumps({'restoreStatus': 1, 'error_message': "None",
                                                 "status": status, 'abort': 1,'alreadyRunning': 0,'running': 'Error'})
                        return HttpResponse(final_json)
                    else:
                        final_json = json.dumps({'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 0,'running': 'Running..'})
                        return HttpResponse(final_json)

                except BaseException,msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg))
                    status = "Just Started"
                    final_json = json.dumps({'restoreStatus': 1, 'error_message': "None", "status": status, 'abort': 0,'running': 'Running..'})
                    return HttpResponse(final_json)
            else:
                final_json = json.dumps({'restoreStatus': 1, 'error_message': "None", "status": "OK To Run",'running': 'Halted','abort': 1})
                return HttpResponse(final_json)


    except BaseException, msg:
        final_dic = {'restoreStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def backupDestinations(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 1:
            return render(request, 'backup/backupDestinations.html', {})
        else:
            return HttpResponse("You should be admin to add backup destinations.")
    except KeyError:
        return redirect(loadLoginPage)

def submitDestinationCreation(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'destStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)


                destinations = backupUtil.backupUtilities.destinationsPath

                data = json.loads(request.body)
                ipAddress = data['IPAddress']
                password = data['password']
                port = "22"

                try:
                    port = data['backupSSHPort']
                except:
                    pass

                if dest.objects.all().count() == 2:
                    final_dic = {'destStatus': 0, 'error_message': "Currently only one remote destination is allowed."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                try:
                    d = dest.objects.get(destLoc=ipAddress)
                    final_dic = {'destStatus': 0, 'error_message': "This destination already exists."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                except:
                    setupKeys = backupUtil.backupUtilities.setupSSHKeys(ipAddress, password, port)

                    if setupKeys[0] == 1:
                        backupUtil.backupUtilities.createBackupDir(ipAddress,port)
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
                            writeToFile.writelines("22"+"\n")
                            writeToFile.close()
                            newDest = dest(destLoc=ipAddress)
                            newDest.save()

                        final_dic = {'destStatus': 1, 'error_message': "None"}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                    else:
                        final_dic = {'destStatus': 0, 'error_message': setupKeys[1]}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
        except BaseException,msg:
            final_dic = {'destStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def getCurrentBackupDestinations(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'fetchStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

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
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def getConnectionStatus(request):
    try:
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                ipAddress = data['IPAddress']

                checkCon = backupUtil.backupUtilities.checkConnection(ipAddress)

                if checkCon[0]==1:
                    final_dic = {'connStatus': 1, 'error_message': "None"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'connStatus': 0, 'error_message': checkCon[1]}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'connStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'connStatus': 1, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def deleteDestination(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'delStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)


                data = json.loads(request.body)
                ipAddress = data['IPAddress']

                delDest = dest.objects.get(destLoc=ipAddress)
                delDest.delete()

                path = "/usr/local/CyberCP/backup/"
                destinations = path + "destinations"

                data = open(destinations,'r').readlines()

                writeToFile = open(destinations,'r')

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

        except BaseException,msg:
            final_dic = {'delStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'delStatus': 1, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def scheduleBackup(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 1:

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

            return render(request,'backup/backupSchedule.html',{'destinations':destinations})
        else:
            return HttpResponse("You should be admin to schedule backups.")
    except KeyError:
        return redirect(loadLoginPage)


def getCurrentBackupSchedules(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'fetchStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                records = backupSchedules.objects.all()

                json_data = "["
                checker = 0

                for items in records:
                    dic = {'id': items.id,
                           'destLoc': items.dest.destLoc,
                           'frequency':items.frequency,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def submitBackupSchedule(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                backupDest = data['backupDest']
                backupFreq = data['backupFreq']

                if admin.type != 1:
                    dic = {'scheduleStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                path = "/etc/crontab"

                ## check if already exists
                try:
                    schedule = backupSchedules.objects.get(frequency=backupFreq)
                    if schedule.dest.destLoc == backupDest:
                        final_json = json.dumps({'scheduleStatus': 0, 'error_message': "This schedule already exists"})
                        return HttpResponse(final_json)
                    else:
                        if backupDest == "Home" and backupFreq == "Daily":
                            cronJob = "0 3 * * 0-6 root python /usr/local/CyberCP/plogical/backupScheduleLocal.py"

                            virtualHostUtilities.permissionControl(path)

                            writeToFile = open(path,'a')
                            writeToFile.writelines(cronJob+"\n")
                            writeToFile.close()

                            virtualHostUtilities.leaveControl(path)

                            command = "sudo systemctl restart crond"

                            subprocess.call(shlex.split(command))

                            destination = dest.objects.get(destLoc=backupDest)
                            newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                            newSchedule.save()

                            final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                            return HttpResponse(final_json)

                        elif backupDest == "Home" and backupFreq == "Weekly":
                            cronJob = "0 3 * * 3 root python /usr/local/CyberCP/plogical/backupScheduleLocal.py "

                            virtualHostUtilities.permissionControl(path)

                            writeToFile = open(path, 'a')
                            writeToFile.writelines(cronJob + "\n")
                            writeToFile.close()

                            virtualHostUtilities.leaveControl(path)

                            command = "sudo systemctl restart crond"

                            subprocess.call(shlex.split(command))

                            destination = dest.objects.get(destLoc=backupDest)
                            newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                            newSchedule.save()

                            final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                            return HttpResponse(final_json)

                        elif backupDest != "Home" and backupFreq == "Daily":
                            cronJob = "0 3 * * 0-6 root python /usr/local/CyberCP/plogical/backupSchedule.py"

                            virtualHostUtilities.permissionControl(path)

                            writeToFile = open(path, 'a')
                            writeToFile.writelines(cronJob + "\n")
                            writeToFile.close()

                            virtualHostUtilities.leaveControl(path)

                            command = "sudo systemctl restart crond"

                            subprocess.call(shlex.split(command))

                            destination = dest.objects.get(destLoc=backupDest)
                            newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                            newSchedule.save()

                            final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                            return HttpResponse(final_json)

                        elif backupDest != "Home" and backupFreq == "Weekly":
                            cronJob = "0 3 * * 3 root python /usr/local/CyberCP/plogical/backupSchedule.py "

                            virtualHostUtilities.permissionControl(path)

                            writeToFile = open(path, 'a')
                            writeToFile.writelines(cronJob + "\n")
                            writeToFile.close()

                            virtualHostUtilities.leaveControl(path)

                            command = "sudo systemctl restart crond"

                            subprocess.call(shlex.split(command))

                            destination = dest.objects.get(destLoc=backupDest)
                            newSchedule = backupSchedules(dest=destination,frequency=backupFreq)
                            newSchedule.save()

                            final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                            return HttpResponse(final_json)
                except:
                    if backupDest == "Home" and backupFreq == "Daily":
                        cronJob = "0 3 * * 0-6 root python /usr/local/CyberCP/plogical/backupScheduleLocal.py"

                        virtualHostUtilities.permissionControl(path)

                        writeToFile = open(path, 'a')
                        writeToFile.writelines(cronJob + "\n")
                        writeToFile.close()

                        virtualHostUtilities.leaveControl(path)

                        command = "sudo systemctl restart crond"

                        subprocess.call(shlex.split(command))

                        destination = dest.objects.get(destLoc=backupDest)
                        newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                        newSchedule.save()

                        final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                        return HttpResponse(final_json)

                    elif backupDest == "Home" and backupFreq == "Weekly":
                        cronJob = "0 3 * * 3 root python /usr/local/CyberCP/plogical/backupScheduleLocal.py "

                        virtualHostUtilities.permissionControl(path)

                        writeToFile = open(path, 'a')
                        writeToFile.writelines(cronJob + "\n")
                        writeToFile.close()

                        virtualHostUtilities.leaveControl(path)

                        command = "sudo systemctl restart crond"

                        subprocess.call(shlex.split(command))

                        destination = dest.objects.get(destLoc=backupDest)
                        newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                        newSchedule.save()

                        final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                        return HttpResponse(final_json)

                    elif backupDest != "Home" and backupFreq == "Daily":
                        cronJob = "0 3 * * 0-6 root python /usr/local/CyberCP/plogical/backupSchedule.py"

                        virtualHostUtilities.permissionControl(path)

                        writeToFile = open(path, 'a')
                        writeToFile.writelines(cronJob + "\n")
                        writeToFile.close()

                        virtualHostUtilities.leaveControl(path)

                        command = "sudo systemctl restart crond"

                        subprocess.call(shlex.split(command))

                        destination = dest.objects.get(destLoc=backupDest)
                        newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                        newSchedule.save()

                        final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                        return HttpResponse(final_json)

                    elif backupDest != "Home" and backupFreq == "Weekly":
                        cronJob = "0 3 * * 3 root python /usr/local/CyberCP/plogical/backupSchedule.py "

                        virtualHostUtilities.permissionControl(path)

                        writeToFile = open(path, 'a')
                        writeToFile.writelines(cronJob + "\n")
                        writeToFile.close()

                        virtualHostUtilities.leaveControl(path)

                        command = "sudo systemctl restart crond"

                        subprocess.call(shlex.split(command))

                        destination = dest.objects.get(destLoc=backupDest)
                        newSchedule = backupSchedules(dest=destination, frequency=backupFreq)
                        newSchedule.save()

                        final_json = json.dumps({'scheduleStatus': 1, 'error_message': "None"})
                        return HttpResponse(final_json)



        except BaseException,msg:
            final_json = json.dumps({'scheduleStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)
    except KeyError:
        final_json = json.dumps({'scheduleStatus': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)


def scheduleDelete(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'delStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                data = json.loads(request.body)
                backupDest = data['destLoc']
                backupFreq = data['frequency']


                path = "/etc/crontab"


                if backupDest == "Home" and backupFreq == "Daily":

                    virtualHostUtilities.permissionControl(path)

                    data = open(path, "r").readlines()
                    writeToFile = open(path, 'w')

                    for items in data:
                        if items.find("0-6") > -1 and items.find("backupScheduleLocal.py") > -1:
                            continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                    virtualHostUtilities.leaveControl(path)

                    command = "sudo systemctl restart crond"

                    subprocess.call(shlex.split(command))

                    destination = dest.objects.get(destLoc=backupDest)
                    newSchedule = backupSchedules.objects.get(dest=destination, frequency=backupFreq)
                    newSchedule.delete()

                    final_json = json.dumps({'delStatus': 1, 'error_message': "None"})
                    return HttpResponse(final_json)

                elif backupDest == "Home" and backupFreq == "Weekly":

                    virtualHostUtilities.permissionControl(path)

                    data = open(path, "r").readlines()
                    writeToFile = open(path, 'w')

                    for items in data:
                        if items.find("* 3") > -1 and items.find("backupScheduleLocal.py") > -1:
                            continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                    virtualHostUtilities.leaveControl(path)

                    command = "sudo systemctl restart crond"

                    subprocess.call(shlex.split(command))

                    destination = dest.objects.get(destLoc=backupDest)
                    newSchedule = backupSchedules.objects.get(dest=destination, frequency=backupFreq)
                    newSchedule.delete()

                    final_json = json.dumps({'delStatus': 1, 'error_message': "None"})
                    return HttpResponse(final_json)

                elif backupDest != "Home" and backupFreq == "Daily":

                    virtualHostUtilities.permissionControl(path)

                    data = open(path, "r").readlines()
                    writeToFile = open(path, 'w')

                    for items in data:
                        if items.find("0-6") > -1 and items.find("backupSchedule.py") > -1:
                            continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                    virtualHostUtilities.leaveControl(path)

                    command = "sudo systemctl restart crond"

                    subprocess.call(shlex.split(command))

                    destination = dest.objects.get(destLoc=backupDest)
                    newSchedule = backupSchedules.objects.get(dest=destination, frequency=backupFreq)
                    newSchedule.delete()

                    final_json = json.dumps({'delStatus': 1, 'error_message': "None"})
                    return HttpResponse(final_json)

                elif backupDest != "Home" and backupFreq == "Weekly":

                    virtualHostUtilities.permissionControl(path)

                    data = open(path, "r").readlines()
                    writeToFile = open(path, 'w')

                    for items in data:
                        if items.find("* 3") > -1 and items.find("backupSchedule.py") > -1:
                            continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                    virtualHostUtilities.leaveControl(path)

                    command = "sudo systemctl restart crond"

                    subprocess.call(shlex.split(command))

                    destination = dest.objects.get(destLoc=backupDest)
                    newSchedule = backupSchedules.objects.get(dest=destination, frequency=backupFreq)
                    newSchedule.delete()

                    final_json = json.dumps({'delStatus': 1, 'error_message': "None"})
                    return HttpResponse(final_json)



        except BaseException,msg:
            final_json = json.dumps({'delStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)
    except KeyError:
        final_json = json.dumps({'delStatus': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def remoteBackups(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        return render(request,'backup/remoteBackups.html')
    except KeyError:
        return redirect(loadLoginPage)

def submitRemoteBackups(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        if request.method == 'POST':

            if admin.type != 1:
                dic = {'status': 0, 'error_message': "Only administrator can view this page."}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            data = json.loads(request.body)
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
                                'error_message': "Not able to fetch version of remote server. Error Message: " + data[
                                    'error_message'], "dir": "Null"}
                    data_ret = json.dumps(data_ret)
                    return HttpResponse(data_ret)


            except BaseException, msg:
                data_ret = {'status': 0,
                            'error_message': "Not able to fetch version of remote server. Error Message: " + str(msg),
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
                                         'error_message': "I am sorry, I could not fetch key from remote server. Error Message: " + data['error_message']
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

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
            execPath = execPath + " writeAuthKey --pathToKey " + pathToKey
            output = subprocess.check_output(shlex.split(execPath))

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
            except BaseException, msg:
                data_ret = {'status': 0,
                            'error_message': "Not able to fetch accounts from remote server. Error Message: " + str(
                                msg), "dir": "Null"}
                data_ret = json.dumps(data_ret)
                return HttpResponse(data_ret)
        else:
            return HttpResponse("This URL only accepts POST requests")

    except BaseException, msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
    return HttpResponse(final_json)

def starRemoteTransfer(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)

                if admin.type != 1:
                    dic = {'remoteTransferStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                ipAddress = data['ipAddress']
                password = data['password']
                accountsToTransfer = data['accountsToTransfer']

                try:

                    ipFile = os.path.join("/etc","cyberpanel","machineIP")
                    f = open(ipFile)
                    ownIP = f.read()

                    finalData = json.dumps({'username': "admin", "password": password,"ipAddress": ownIP,"accountsToTransfer":accountsToTransfer})

                    url = "https://" + ipAddress + ":8090/api/remoteTransfer"

                    r = requests.post(url, data=finalData, verify=False)

                    data = json.loads(r.text)


                    if data['transferStatus'] == 1:

                        ## Create local backup dir

                        localBackupDir = os.path.join("/home","backup")

                        if not os.path.exists(localBackupDir):
                            command = "sudo mkdir " + localBackupDir
                            subprocess.call(shlex.split(command))

                        ## create local directory that will host backups

                        localStoragePath = "/home/backup/transfer-" + str(data['dir'])

                        ## making local storage directory for backups

                        command = "sudo mkdir " + localStoragePath
                        subprocess.call(shlex.split(command))

                        final_json = json.dumps({'remoteTransferStatus': 1, 'error_message': "None","dir":data['dir']})
                        return HttpResponse(final_json)
                    else:
                        final_json = json.dumps({'remoteTransferStatus': 0, 'error_message':"Can not initiate remote transfer. Error message: "+ data['error_message']})
                        return HttpResponse(final_json)

                except BaseException,msg:
                    final_json = json.dumps({'remoteTransferStatus': 0,
                                             'error_message': "Can not initiate remote transfer. Error message: " +
                                                              str(msg)})
                    return HttpResponse(final_json)



        except BaseException,msg:
            final_json = json.dumps({'remoteTransferStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)
    except KeyError:
        final_json = json.dumps({'remoteTransferStatus': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def getRemoteTransferStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if request.method == "POST":

            if admin.type != 1:
                dic = {'remoteTransferStatus': 0, 'error_message': "Only administrator can view this page."}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            data = json.loads(request.body)
            ipAddress = data['ipAddress']
            password = data['password']
            dir = data['dir']
            username = "admin"

            finalData = json.dumps({'dir': dir, "username":username,"password":password})
            r = requests.post("https://"+ipAddress+":8090/api/FetchRemoteTransferStatus", data=finalData,verify=False)

            data = json.loads(r.text)

            if data['fetchStatus'] == 1:
                if data['status'].find("Backups are successfully generated and received on") > -1:

                    data = {'remoteTransferStatus': 1, 'error_message': "None", "status": data['status'],'backupsSent': 1}
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


    except BaseException, msg:
        data = {'remoteTransferStatus': 0, 'error_message': str(msg),'backupsSent': 0}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


def remoteBackupRestore(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == "POST":

                if admin.type != 1:
                    dic = {'remoteRestoreStatus': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                data = json.loads(request.body)
                backupDir = data['backupDir']

                backupDirComplete = "/home/backup/transfer-"+str(backupDir)
                #adminEmail = admin.email

                ##

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"

                execPath = execPath + " remoteBackupRestore --backupDirComplete " + backupDirComplete + " --backupDir " + str(backupDir)

                subprocess.Popen(shlex.split(execPath))

                time.sleep(3)

                data = {'remoteRestoreStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

                ##


        except BaseException, msg:
            data = {'remoteRestoreStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'remoteRestoreStatus': 0, 'error_message': "not logged in as admin", "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def localRestoreStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        if request.method == "POST":

            if admin.type != 1:
                data_ret = {'remoteTransferStatus': 0, 'error_message': "No such log found", "status": "None",
                            "complete": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data = json.loads(request.body)
            backupDir = data['backupDir']

            #admin = Administrator.objects.get(userName=username)
            backupLogPath = "/home/backup/transfer-"+ backupDir +"/" + "backup_log"

            removalPath = "/home/backup/transfer-"+ str(backupDir)

            time.sleep(3)

            if os.path.isfile(backupLogPath):
                command = "sudo cat " + backupLogPath
                status = subprocess.check_output(shlex.split(command))

                if status.find("completed[success]")>-1:
                    command = "sudo rm -rf " + removalPath
                    #subprocess.call(shlex.split(command))
                    data_ret = {'remoteTransferStatus': 1, 'error_message': "None", "status": status, "complete": 1}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                elif status.find("[5010]") > -1:
                    command = "sudo rm -rf " + removalPath
                    #subprocess.call(shlex.split(command))
                    data = {'remoteTransferStatus': 0, 'error_message': status,
                            "status":"None","complete":0}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'remoteTransferStatus': 1, 'error_message': "None", "status": status, "complete": 0}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            else:
                data_ret = {'remoteTransferStatus': 0, 'error_message': "No such log found","status":"None","complete":0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except BaseException, msg:
        data = {'remoteTransferStatus': 0,'error_message': str(msg),"status":"None","complete":0}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

def cancelRemoteBackup(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if admin.type != 1:
            dic = {'cancelStatus': 0, 'error_message': "Only administrator can view this page."}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

        if request.method == "POST":

            data = json.loads(request.body)
            ipAddress = data['ipAddress']
            password = data['password']
            dir = data['dir']
            username = "admin"


            finalData = json.dumps({'dir': dir, "username":username,"password":password})
            r = requests.post("https://"+ipAddress+":8090/api/cancelRemoteTransfer", data=finalData,verify=False)

            data = json.loads(r.text)

            if data['cancelStatus'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.writeToFile("Some error cancelling at remote server, see the log file for remote server.")

            path = "/home/backup/transfer-" + str(dir)
            pathpid = path + "/pid"

            command = "sudo cat " + pathpid
            pid = subprocess.check_output(shlex.split(command))

            command = "sudo kill -KILL " + pid
            subprocess.call(shlex.split(command))

            command = "sudo rm -rf " + path
            subprocess.call(shlex.split(command))

            data = {'cancelStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data)
            return HttpResponse(json_data)


    except BaseException, msg:
        data = {'cancelStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)
