# -*- coding: utf-8 -*-

from django.shortcuts import render
from plogical.acl import ACLManager
from django.shortcuts import HttpResponse, redirect
from plogical.processUtilities import ProcessUtilities
from plogical.virtualHostUtilities import virtualHostUtilities
import json
import os
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
from .models import IncJob, BackupJob, JobSites
from .IncBackupsControl import IncJobs
from random import randint
import time
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import stat
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

        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('sftp:%s' % (items))

        path = '/home/cyberpanel/aws'
        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('s3:s3.amazonaws.com/%s' % (items))

        return defRenderer(request, 'IncBackups/createBackup.html', {'websiteList': websitesName, 'destinations': destinations})
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)

def backupDestinations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'addDeleteDestinations') == 0:
            return ACLManager.loadError()

        return defRenderer(request, 'IncBackups/incrementalDestinations.html', {})
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)

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


            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
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
                if currentConfig.find('cat') == -1:
                    writeToFile.write(currentConfig)

                content = """Host %s
    IdentityFile ~/.ssh/cyberpanel
    Port %s
""" % (ipAddress, port)
                if currentConfig.find(ipAddress) == -1:
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

            os.chmod(awsFile, stat.S_IRUSR | stat.S_IWUSR)

            final_dic = {'status': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    except BaseException as msg:
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

    except BaseException as msg:
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

    except BaseException as msg:
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

        try:
            backupDestinations = data['backupDestinations']

            extraArgs = {}
            extraArgs['website'] = backupDomain
            extraArgs['backupDestinations'] = backupDestinations
            try:
                extraArgs['password'] = data['password']
            except:
                final_json = json.dumps({'status': 0, 'error_message': "Please supply the password."})
                return HttpResponse(final_json)

            startJob = IncJobs('Dummpy', extraArgs)
            return startJob.fetchCurrentBackups()

        except:

            website = Websites.objects.get(domain=backupDomain)

            backups = website.incjob_set.all()

            json_data = "["
            checker = 0

            for items in reversed(backups):

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


    except BaseException as msg:
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


        try:
            websiteDatabases = data['websiteDatabases']
        except:
            websiteDatabases = False

        extraArgs = {}
        extraArgs['website'] = backupDomain
        extraArgs['tempPath'] = tempPath
        extraArgs['backupDestinations'] = backupDestinations
        extraArgs['websiteData'] = websiteData
        extraArgs['websiteEmails'] = websiteEmails
        extraArgs['websiteSSLs'] = websiteSSLs
        extraArgs['websiteDatabases'] = websiteDatabases

        startJob = IncJobs('createBackup', extraArgs)
        startJob.start()

        time.sleep(2)

        final_json = json.dumps({'status': 1,  'error_message': "None", 'tempPath': tempPath})
        return HttpResponse(final_json)

    except BaseException as msg:
        logging.writeToFile(str(msg))
        final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def getBackupStatus(request):
    try:
        data = json.loads(request.body)

        status = data['tempPath']
        backupDomain = data['websiteToBeBacked']

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        if (status[:16] == "/home/cyberpanel" or status[:4] == '/tmp' or status[:18] == '/usr/local/CyberCP') \
                and status != '/usr/local/CyberCP/CyberCP/settings.py' and status.find('..') == -1:
            pass
        else:
            data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "100",
                        'currentStatus': 'Invalid status file.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        ## file name read ends

        if os.path.exists(status):
            command = "cat " + status
            result = ProcessUtilities.outputExecutioner(command, 'cyberpanel')

            if result.find("Completed") > -1:

                ### Removing Files

                os.remove(status)

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result, "abort": 1})
                return HttpResponse(final_json)

            elif result.find("[5009]") > -1:
                ## removing status file, so that backup can re-run
                try:
                    os.remove(status)
                except:
                    pass

                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result,
                     "abort": 1})
                return HttpResponse(final_json)
            else:
                final_json = json.dumps(
                    {'backupStatus': 1, 'error_message': "None", "status": result,
                     "abort": 0})
                return HttpResponse(final_json)
        else:
            final_json = json.dumps({'backupStatus': 1, 'error_message': "None", "status": 1, "abort": 0})
            return HttpResponse(final_json)

    except BaseException as msg:
        final_dic = {'backupStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        logging.writeToFile(str(msg) + " [backupStatus]")
        return HttpResponse(final_json)

def deleteBackup(request):
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

        id = data['backupID']

        IncJob.objects.get(id=id).delete()

        final_dic = {'status': 1, 'error_message': 'None'}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    except BaseException as msg:
        final_dic = {'destStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetchRestorePoints(request):
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

        data = json.loads(request.body)
        id = data['id']

        incJob = IncJob.objects.get(id=id)

        backups = incJob.jobsnapshots_set.all()

        json_data = "["
        checker = 0

        for items in backups:

            dic = {'id': items.id,
                   'snapshotid': items.snapshotid,
                   'type': items.type,
                   'destination': items.destination,
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

def restorePoint(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        data = json.loads(request.body)
        backupDomain = data['websiteToBeBacked']
        jobid = data['jobid']

        if ACLManager.checkOwnership(backupDomain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('metaStatus', 0)

        tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        if data['reconstruct'] == 'remote':
            extraArgs = {}
            extraArgs['website'] = backupDomain
            extraArgs['jobid'] = jobid
            extraArgs['tempPath'] = tempPath
            extraArgs['reconstruct'] = data['reconstruct']
            extraArgs['backupDestinations'] = data['backupDestinations']
            extraArgs['password'] = data['password']
            extraArgs['path'] = data['path']
        else:
            extraArgs = {}
            extraArgs['website'] = backupDomain
            extraArgs['jobid'] = jobid
            extraArgs['tempPath'] = tempPath
            extraArgs['reconstruct'] = data['reconstruct']


        startJob = IncJobs('restorePoint', extraArgs)
        startJob.start()


        time.sleep(2)

        final_json = json.dumps({'status': 1,  'error_message': "None", 'tempPath': tempPath})
        return HttpResponse(final_json)

    except BaseException as msg:
        logging.writeToFile(str(msg))
        final_dic = {'status': 0, 'metaStatus': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def scheduleBackups(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        destinations = []
        destinations.append('local')

        path = '/home/cyberpanel/sftp'

        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('sftp:%s' % (items))

        path = '/home/cyberpanel/aws'
        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('s3:s3.amazonaws.com/%s' % (items))

        websitesName = ACLManager.findAllSites(currentACL, userID)

        return defRenderer(request, 'IncBackups/backupSchedule.html', {'websiteList': websitesName, 'destinations': destinations})
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)

def submitBackupSchedule(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        backupDest = data['backupDestinations']
        backupFreq = data['backupFreq']
        websitesToBeBacked = data['websitesToBeBacked']

        try:
            websiteData = data['websiteData']
            websiteData = 1
        except:
            websiteData = False
            websiteData = 0

        try:
            websiteEmails = data['websiteEmails']
            websiteEmails = 1
        except:
            websiteEmails = False
            websiteEmails = 0

        try:
            websiteDatabases = data['websiteDatabases']
            websiteDatabases = 1
        except:
            websiteDatabases = False
            websiteDatabases = 0

        newJob = BackupJob(websiteData=websiteData, websiteDataEmails=websiteEmails, websiteDatabases=websiteDatabases, destination=backupDest, frequency=backupFreq)
        newJob.save()

        for items in websitesToBeBacked:
            jobsite = JobSites(job=newJob, website=items)
            jobsite.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)


    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def getCurrentBackupSchedules(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        records = BackupJob.objects.all()

        json_data = "["
        checker = 0

        for items in records:
            dic = {'id': items.id,
                   'destination': items.destination,
                   'frequency': items.frequency,
                   'numberOfSites': items.jobsites_set.all().count()
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

def fetchSites(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        data = json.loads(request.body)

        job = BackupJob.objects.get(pk=data['id'])

        json_data = "["
        checker = 0

        for items in job.jobsites_set.all():
            dic = {'id': items.id,
                   'website': items.website,
                   }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data,
                                 'websiteData': job.websiteData, 'websiteDatabases': job.websiteDatabases,
                                 'websiteEmails': job.websiteDataEmails})
        return HttpResponse(final_json)

    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def scheduleDelete(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        id = data['id']

        backupJob = BackupJob.objects.get(id=id)
        backupJob.delete()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)

    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def restoreRemoteBackups(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'createBackup') == 0:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        destinations = []

        path = '/home/cyberpanel/sftp'

        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('sftp:%s' % (items))

        path = '/home/cyberpanel/aws'
        if os.path.exists(path):
            for items in os.listdir(path):
                destinations.append('s3:s3.amazonaws.com/%s' % (items))

        return defRenderer(request, 'IncBackups/restoreRemoteBackups.html', {'websiteList': websitesName, 'destinations': destinations})
    except BaseException as msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)

def saveChanges(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        id = data['id']
        try:
            websiteData = data['websiteData']
        except:
            websiteData = 0
        try:
            websiteDatabases = data['websiteDatabases']
        except:
            websiteDatabases = 0
        try:
            websiteEmails = data['websiteEmails']
        except:
            websiteEmails = 0

        job = BackupJob.objects.get(pk=id)

        job.websiteData = int(websiteData)
        job.websiteDatabases = int(websiteDatabases)
        job.websiteDataEmails = int(websiteEmails)
        job.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)


    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def removeSite(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        id = data['id']
        website = data['website']


        job = BackupJob.objects.get(pk=id)

        site = JobSites.objects.get(job=job, website=website)
        site.delete()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)


    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def addWebsite(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if ACLManager.currentContextPermission(currentACL, 'scheDuleBackups') == 0:
            return ACLManager.loadErrorJson('scheduleStatus', 0)

        data = json.loads(request.body)

        id = data['id']
        website = data['website']


        job = BackupJob.objects.get(pk=id)

        try:
            JobSites.objects.get(job=job, website=website)
        except:
            site = JobSites(job=job, website=website)
            site.save()

        final_json = json.dumps({'status': 1, 'error_message': "None"})
        return HttpResponse(final_json)


    except BaseException as msg:
        final_json = json.dumps({'status': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)