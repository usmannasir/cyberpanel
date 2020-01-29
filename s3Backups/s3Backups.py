#!/usr/local/CyberCP/bin/python
try:
    import os
    import os.path
    from django.shortcuts import HttpResponse
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
    from plogical.httpProc import httpProc
    from plogical.acl import ACLManager
    import threading as multi
    from plogical.mailUtilities import mailUtilities
    import boto3
    from boto3.s3.transfer import TransferConfig
    import json
    from .models import *
    from math import ceil
    import requests
    import time
    from random import randint
    import subprocess, shlex
    from plogical.processUtilities import ProcessUtilities
    from websiteFunctions.models import Websites, Backups
    from plogical.virtualHostUtilities import virtualHostUtilities
    from multiprocessing import Process
    import plogical.backupUtilities as backupUtil
except:
    import threading as multi
    from random import randint
    import json
    import requests
    import subprocess, shlex
    from multiprocessing import Process


class S3Backups(multi.Thread):
    def __init__(self, request=None, data=None, function=None):
        multi.Thread.__init__(self)
        self.request = request
        self.data = data
        self.function = function

    def run(self):
        try:
            if self.function == 'connectAccount':
                self.connectAccount()
            elif self.function == 'forceRunAWSBackup':
                self.forceRunAWSBackup()
            elif self.function == 'forceRunAWSBackupDO':
                self.forceRunAWSBackupDO()
            elif self.function == 'runAWSBackups':
                self.runAWSBackups()
            elif self.function == 'forceRunAWSBackupMINIO':
                self.forceRunAWSBackupMINIO()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [S3Backups.run]')

    @staticmethod
    def getPagination(records, toShow):
        pages = float(records) / float(toShow)

        pagination = []
        counter = 1

        if pages <= 1.0:
            pages = 1
            pagination.append(counter)
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append(counter)
                counter = counter + 1

        return pagination

    @staticmethod
    def recordsPointer(page, toShow):
        finalPageNumber = ((page * toShow)) - toShow
        endPageNumber = finalPageNumber + toShow
        return endPageNumber, finalPageNumber

    @staticmethod
    def getLogsInJson(logs):
        json_data = "["
        checker = 0
        counter = 1

        for items in logs:
            dic = {'id': items.id, 'timeStamp': items.timeStamp, 'level': items.level, 'mesg': items.msg}
            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)
            counter = counter + 1

        json_data = json_data + ']'
        return json_data

    def setupCron(self):
        try:

            command = "sudo cat /etc/crontab"
            crons = ProcessUtilities.outputExecutioner(command).splitlines()

            cronCheck = 1

            for items in crons:
                if items.find('s3Backups.py') > -1:
                    cronCheck = 0

            tempPath = '/home/cyberpanel/' + str(randint(10000, 99999))

            writeToFile = open(tempPath, "w")

            for items in crons:
                writeToFile.writelines(items + "\n")

            if cronCheck:
                writeToFile.writelines("0 0 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/s3Backups/s3Backups.py > /home/cyberpanel/error-logs.txt 2>&1\n")

            writeToFile.close()

            command = 'sudo mv ' + tempPath + " /etc/crontab"
            ProcessUtilities.executioner(command)

            command = 'chown root:root /etc/crontab'
            ProcessUtilities.executioner(command)

            try:
                os.remove(tempPath)
            except:
                pass
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [S3Backups.setupCron]")

    def connectAccount(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            mailUtilities.checkHome()

            path = '/home/cyberpanel/.aws'

            if not os.path.exists(path):
                os.mkdir(path)

            credentials = path + '/credentials'

            credFile = open(credentials, 'w')
            credFile.write(self.data['credData'])
            credFile.close()

            ##

            self.setupCron()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchAWSKeys(self):
        path = '/home/cyberpanel/.aws'
        credentials = path + '/credentials'

        data = open(credentials, 'r').readlines()

        aws_access_key_id = data[1].split(' ')[2].strip(' ').strip('\n')
        aws_secret_access_key = data[2].split(' ')[2].strip(' ').strip('\n')

        return aws_access_key_id, aws_secret_access_key

    def fetchBuckets(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')


            aws_access_key_id, aws_secret_access_key = self.fetchAWSKeys()

            s3 = boto3.resource(
                's3',
                aws_access_key_id = aws_access_key_id,
                aws_secret_access_key = aws_secret_access_key
            )

            json_data = "["
            checker = 0

            for bucket in s3.buckets.all():
                dic = {'name': bucket.name}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def createPlan(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)

            newPlan = BackupPlan(owner=admin, name=self.data['planName'].replace(' ', ''), freq=self.data['frequency'],
                                 retention=self.data['retenion'], bucket=self.data['bucketName'])
            newPlan.save()

            for items in self.data['websitesInPlan']:
                wp = WebsitesInPlan(owner=newPlan, domain=items)
                wp.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [createPlan]')
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupPlans(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)
            json_data = "["
            checker = 0

            for plan in admin.backupplan_set.all():
                dic = {
                    'name': plan.name,
                    'bucket': plan.bucket,
                    'freq': plan.freq,
                    'retention': plan.retention,
                    'lastRun': plan.lastRun,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def deletePlan(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            delPlan = BackupPlan.objects.get(name=self.data['planName'])
            delPlan.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchWebsitesInPlan(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlan.objects.get(name=self.data['planName'])
            json_data = "["
            checker = 0

            for website in plan.websitesinplan_set.all():
                dic = {
                    'id': website.id,
                    'domain': website.domain,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def deleteDomainFromPlan(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlan.objects.get(name=self.data['planName'])
            web = WebsitesInPlan.objects.get(owner=plan, domain=self.data['domainName'])
            web.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def savePlanChanges(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            changePlan = BackupPlan.objects.get(name=self.data['planName'])

            changePlan.bucket = self.data['bucketName']
            changePlan.freq = self.data['frequency']
            changePlan.retention = self.data['retention']

            changePlan.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupLogs(self):
        try:
            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            recordsToShow = int(self.data['recordsToShow'])
            page = int(self.data['page'])

            backupPlan = BackupPlan.objects.get(name=self.data['planName'])
            logs = backupPlan.backuplogs_set.all().order_by('-id')

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            jsonData = S3Backups.getLogsInJson(logs[finalPageNumber:endPageNumber])

            data = {}
            data['data'] = jsonData
            data['pagination'] = pagination

            return proc.ajax(1, None, data)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajaxPre(0, str(msg))

    def createBackup(self, virtualHost):

        website = Websites.objects.get(domain=virtualHost)
        # defining paths

        ## /home/example.com/backup
        backupPath = os.path.join("/home", virtualHost, "backup/")
        domainUser = website.externalApp
        backupName = 'backup-' + domainUser + "-" + time.strftime("%m.%d.%Y_%H-%M-%S")

        ## /home/example.com/backup/backup-example.com-02.13.2018_10-24-52
        tempStoragePath = os.path.join(backupPath, backupName)

        p = Process(target=backupUtil.submitBackupCreation,
                    args=(tempStoragePath, backupName, backupPath, virtualHost))
        p.start()

        time.sleep(2)

        while (1):

            backupDomain = virtualHost
            status = os.path.join("/home", backupDomain, "backup/status")
            backupFileNamePath = os.path.join("/home", backupDomain, "backup/backupFileName")
            pid = os.path.join("/home", backupDomain, "backup/pid")
            ## read file name

            try:
                fileName = open(backupFileNamePath, 'r').read()
            except:
                fileName = "Fetching.."

            ## file name read ends

            if os.path.exists(status):
                status = open(status, 'r').read()

                if status.find("Completed") > -1:

                    ### Removing Files

                    command = 'sudo rm -f ' + status
                    ProcessUtilities.normalExecutioner(command)

                    command = 'sudo rm -f ' + backupFileNamePath
                    ProcessUtilities.normalExecutioner(command)

                    command = 'sudo rm -f ' + pid
                    ProcessUtilities.normalExecutioner(command)

                    return 1, tempStoragePath

                elif status.find("[5009]") > -1:
                    backupObs = Backups.objects.filter(fileName=fileName)
                    for items in backupObs:
                        items.delete()
                    return 0, status

    def forceRunAWSBackup(self):
        try:

            plan = BackupPlan.objects.get(name=self.data['planName'])
            bucketName = plan.bucket.strip('\n').strip(' ')
            runTime = time.strftime("%d:%m:%Y")

            aws_access_key_id, aws_secret_access_key = self.fetchAWSKeys()

            client = boto3.client(
                's3',
                aws_access_key_id = aws_access_key_id,
                aws_secret_access_key = aws_secret_access_key
            )


            config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                    multipart_chunksize=1024 * 25, use_threads=True)

            ## Set Expiration for objects
            try:

                client.put_bucket_lifecycle_configuration(
                    Bucket='string',
                    LifecycleConfiguration={
                        'Rules': [
                            {
                                'Expiration': {
                                    'Days': plan.retention,
                                    'ExpiredObjectDeleteMarker': True
                                },
                                'ID': plan.name,
                                'Prefix': '',
                                'Filter': {
                                    'Prefix': plan.name + '/',
                                },
                                'Status': 'Enabled',

                            },
                        ]
                    }
                )
            except BaseException as msg:
                BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR',
                           msg=str(msg)).save()

            ##

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='INFO',
                           msg='Unauthorised user tried to run AWS Backups.').save()
                return 0

            BackupLogs(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                       msg='Starting backup process..').save()

            for items in plan.websitesinplan_set.all():
                result = self.createBackup(items.domain)
                if result[0]:
                    key = plan.name + '/' + runTime + '/' + result[1].split('/')[-1] + ".tar.gz"
                    client.upload_file(
                        result[1] + ".tar.gz",
                        bucketName,
                        key,
                        Config=config,
                    )

                    command = 'rm -f ' + result[1] + ".tar.gz"
                    ProcessUtilities.executioner(command)

                    BackupLogs(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                               msg='Backup successful for ' + items.domain + '.').save()
                else:
                    BackupLogs(owner=plan, level='ERROR', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                               msg='Backup failed for ' + items.domain + '. Error: ' + result[1]).save()

            plan.lastRun = runTime
            plan.save()

            BackupLogs(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                       msg='Backup Process Finished.').save()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [S3Backups.runBackupPlan]')
            plan = BackupPlan.objects.get(name=self.data['planName'])
            BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR', msg=str(msg)).save()

    def connectAccountDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            mailUtilities.checkHome()

            path = '/home/cyberpanel/.do'

            if not os.path.exists(path):
                os.mkdir(path)

            credentials = path + '/credentials'

            credFile = open(credentials, 'w')
            credFile.write(self.data['credData'])
            credFile.close()

            ##

            self.setupCron()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBucketsDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            filePath = '/home/cyberpanel/.do/credentials'

            data = open(filePath, 'r').readlines()

            accessID = data[1].split('=')[1].strip(' ').strip('\n')
            secret = data[2].split('=')[1].strip(' ').strip('\n')

            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=self.data['doRegion'],
                endpoint_url='https://' + self.data['doRegion'] + '.digitaloceanspaces.com',
                aws_access_key_id=accessID,
                aws_secret_access_key=secret
            )
            response = client.list_buckets()
            spaces = [space['Name'] for space in response['Buckets']]
            json_data = "["
            checker = 0

            for space in spaces:
                dic = {'name': space}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.writeToFile(str(msg))
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def createPlanDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)

            newPlan = BackupPlanDO(owner=admin, name=self.data['planName'].replace(' ', ''),
                                   freq=self.data['frequency'],
                                   retention=self.data['retenion'], bucket=self.data['bucketName'],
                                   type=self.data['type'],
                                   region=self.data['region'])
            newPlan.save()

            for items in self.data['websitesInPlan']:
                wp = WebsitesInPlanDO(owner=newPlan, domain=items)
                wp.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [createPlanDO]')
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupPlansDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)
            json_data = "["
            checker = 0

            for plan in admin.backupplando_set.filter(type=self.data['type']):
                dic = {
                    'name': plan.name,
                    'bucket': plan.bucket,
                    'freq': plan.freq,
                    'retention': plan.retention,
                    'lastRun': plan.lastRun,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def deletePlanDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            delPlan = BackupPlanDO.objects.get(name=self.data['planName'])
            delPlan.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchWebsitesInPlanDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlanDO.objects.get(name=self.data['planName'])
            json_data = "["
            checker = 0

            for website in plan.websitesinplando_set.all():
                dic = {
                    'id': website.id,
                    'domain': website.domain,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupLogsDO(self):
        try:
            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            recordsToShow = int(self.data['recordsToShow'])
            page = int(self.data['page'])

            backupPlan = BackupPlanDO.objects.get(name=self.data['planName'])
            logs = backupPlan.backuplogsdo_set.all().order_by('-id')

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            jsonData = S3Backups.getLogsInJson(logs[finalPageNumber:endPageNumber])

            data = {}
            data['data'] = jsonData
            data['pagination'] = pagination

            return proc.ajax(1, None, data)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajaxPre(0, str(msg))

    def deleteDomainFromPlanDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlanDO.objects.get(name=self.data['planName'])
            web = WebsitesInPlanDO.objects.get(owner=plan, domain=self.data['domainName'])
            web.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def savePlanChangesDO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            changePlan = BackupPlanDO.objects.get(name=self.data['planName'])

            changePlan.bucket = self.data['bucketName']
            changePlan.freq = self.data['frequency']
            changePlan.retention = self.data['retention']
            changePlan.region = self.data['region']

            changePlan.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def forceRunAWSBackupDO(self):
        try:

            plan = BackupPlanDO.objects.get(name=self.data['planName'])
            bucketName = plan.bucket.strip('\n').strip(' ')
            runTime = time.strftime("%d:%m:%Y")

            ## Setup DO Client

            filePath = '/home/cyberpanel/.do/credentials'

            data = open(filePath, 'r').readlines()

            accessID = data[1].split('=')[1].strip(' ').strip('\n')
            secret = data[2].split('=')[1].strip(' ').strip('\n')

            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=plan.region,
                endpoint_url='https://' + plan.region + '.digitaloceanspaces.com',
                aws_access_key_id=accessID,
                aws_secret_access_key=secret
            )

            config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                    multipart_chunksize=1024 * 25, use_threads=True)

            ## Set Expiration for objects
            try:

                client.put_bucket_lifecycle_configuration(
                    Bucket='string',
                    LifecycleConfiguration={
                        'Rules': [
                            {
                                'Expiration': {
                                    'Days': plan.retention,
                                    'ExpiredObjectDeleteMarker': True
                                },
                                'ID': plan.name,
                                'Prefix': '',
                                'Filter': {
                                    'Prefix': plan.name + '/',
                                },
                                'Status': 'Enabled',

                            },
                        ]
                    }
                )
            except BaseException as msg:
                BackupLogsDO(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR',
                             msg=str(msg)).save()

            ##

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                BackupLogsDO(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='INFO',
                             msg='Unauthorised user tried to run AWS Backups.').save()
                return 0

            BackupLogsDO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                         msg='Starting backup process..').save()

            for items in plan.websitesinplando_set.all():
                result = self.createBackup(items.domain)
                if result[0]:
                    key = plan.name + '/' + runTime + '/' + result[1].split('/')[-1] + ".tar.gz"
                    client.upload_file(
                        result[1] + ".tar.gz",
                        bucketName,
                        key,
                        Config=config,
                    )
                    command = 'rm -f ' + result[1] + ".tar.gz"
                    ProcessUtilities.executioner(command)
                    BackupLogsDO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                                 msg='Backup successful for ' + items.domain + '.').save()

                else:
                    BackupLogsDO(owner=plan, level='ERROR', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                                 msg='Backup failed for ' + items.domain + '. Error: ' + result[1]).save()

            plan.lastRun = runTime
            plan.save()

            BackupLogsDO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                         msg='Backup Process Finished.').save()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [S3Backups.forceRunAWSBackupDO]')
            plan = BackupPlanDO.objects.get(name=self.data['planName'])
            BackupLogsDO(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR', msg=str(msg)).save()

    def addMINIONode(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use MINIO Backups.')

            admin = Administrator.objects.get(pk=userID)

            newNode = MINIONodes(owner=admin, endPointURL=self.data['endPoint'], accessKey=self.data['accessKey'],
                                 secretKey=self.data['secretKey'])
            newNode.save()

            self.setupCron()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [addMINIONode]')
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchMINIONodes(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use MINIO Backups.')

            admin = Administrator.objects.get(pk=userID)
            json_data = "["
            checker = 0

            for node in admin.minionodes_set.all():
                dic = {
                    'accessKey': node.accessKey,
                    'endPoint': node.endPointURL.lstrip('https://').lstrip('http://')
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def deleteMINIONode(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            delNode = MINIONodes.objects.get(accessKey=self.data['accessKey'])
            delNode.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def createPlanMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)

            minioNode = MINIONodes.objects.get(accessKey=self.data['minioNode'])

            newPlan = BackupPlanMINIO(owner=admin, name=self.data['planName'].replace(' ', ''),
                                      freq=self.data['frequency'],
                                      retention=self.data['retenion'], minioNode=minioNode)
            newPlan.save()

            for items in self.data['websitesInPlan']:
                wp = WebsitesInPlanMINIO(owner=newPlan, domain=items)
                wp.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [createPlanDO]')
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupPlansMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            admin = Administrator.objects.get(pk=userID)
            json_data = "["
            checker = 0

            for plan in admin.backupplanminio_set.all():
                dic = {
                    'name': plan.name,
                    'minioNode': plan.minioNode.accessKey,
                    'freq': plan.freq,
                    'retention': plan.retention,
                    'lastRun': plan.lastRun,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def deletePlanMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            delPlan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            delPlan.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def savePlanChangesMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            changePlan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            minioNode = MINIONodes.objects.get(accessKey=self.data['minioNode'].strip(' ').strip('\n'))

            changePlan.minioNode = minioNode
            changePlan.freq = self.data['frequency']
            changePlan.retention = self.data['retention']

            changePlan.save()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def forceRunAWSBackupMINIO(self):
        try:

            plan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            runTime = time.strftime("%d:%m:%Y")

            ## Setup MINIO Client

            endPoint = plan.minioNode.endPointURL
            accessID = plan.minioNode.accessKey
            secret = plan.minioNode.secretKey

            session = boto3.session.Session()
            client = session.client(
                's3',
                endpoint_url= endPoint,
                aws_access_key_id=accessID,
                aws_secret_access_key=secret,
                verify= False
            )

            config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                    multipart_chunksize=1024 * 25, use_threads=True)

            try:
                client.create_bucket(Bucket=plan.name.lower())
            except BaseException as msg:
                BackupLogsMINIO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                                msg=str(msg)).save()
                return 0

            ##

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                BackupLogsMINIO(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='INFO',
                                msg='Unauthorised user tried to run AWS Backups.').save()
                return 0

            BackupLogsMINIO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                            msg='Starting backup process..').save()

            for items in plan.websitesinplanminio_set.all():
                result = self.createBackup(items.domain)
                if result[0]:
                    key = runTime + '/' + result[1].split('/')[-1] + ".tar.gz"

                    client.upload_file(
                        result[1] + ".tar.gz",
                        plan.name.lower(),
                        key,
                        Config=config,
                    )
                    command = 'rm -f ' + result[1] + ".tar.gz"
                    ProcessUtilities.executioner(command)
                    BackupLogsMINIO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                                    msg='Backup successful for ' + items.domain + '.').save()
                else:
                    BackupLogsMINIO(owner=plan, level='ERROR', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                                    msg='Backup failed for ' + items.domain + '. Error: ' + result[1]).save()

            plan.lastRun = runTime
            plan.save()

            BackupLogsMINIO(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),
                            msg='Backup Process Finished.').save()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [S3Backups.forceRunAWSBackupMINIO]')
            plan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            BackupLogsMINIO(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR',
                            msg=str(msg)).save()

    def fetchWebsitesInPlanMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            json_data = "["
            checker = 0

            for website in plan.websitesinplanminio_set.all():
                dic = {
                    'id': website.id,
                    'domain': website.domain,
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
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBackupLogsMINIO(self):
        try:
            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            recordsToShow = int(self.data['recordsToShow'])
            page = int(self.data['page'])

            backupPlan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            logs = backupPlan.backuplogsminio_set.all().order_by('-id')

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            jsonData = S3Backups.getLogsInJson(logs[finalPageNumber:endPageNumber])

            data = {}
            data['data'] = jsonData
            data['pagination'] = pagination

            return proc.ajax(1, None, data)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajaxPre(0, str(msg))

    def deleteDomainFromPlanMINIO(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            plan = BackupPlanMINIO.objects.get(name=self.data['planName'])
            web = WebsitesInPlanMINIO.objects.get(owner=plan, domain=self.data['domainName'])
            web.delete()

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def runAWSBackups(self):
        try:
            admin = Administrator.objects.get(userName='admin')
            self.request.session['userID'] = admin.pk

            for plan in BackupPlan.objects.all():
                lastRunDay = plan.lastRun.split(':')[0]
                lastRunMonth = plan.lastRun.split(':')[1]

                if plan.freq == 'Daily' and lastRunDay != time.strftime("%d"):
                    self.data = {}
                    self.data['planName'] = plan.name
                    self.forceRunAWSBackup()
                else:
                    if lastRunMonth == time.strftime("%m"):
                        days = int(time.strftime("%d")) - int(lastRunDay)
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackup()
                    else:
                        days = 30 - int(lastRunDay)
                        days = days + int(time.strftime("%d"))
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackup()

            for plan in BackupPlanDO.objects.all():
                lastRunDay = plan.lastRun.split(':')[0]
                lastRunMonth = plan.lastRun.split(':')[1]

                if plan.freq == 'Daily' and lastRunDay != time.strftime("%d"):
                    self.data = {}
                    self.data['planName'] = plan.name
                    self.forceRunAWSBackupDO()
                else:
                    if lastRunMonth == time.strftime("%m"):
                        days = int(time.strftime("%d")) - int(lastRunDay)
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackupDO()
                    else:
                        days = 30 - int(lastRunDay)
                        days = days + int(time.strftime("%d"))
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackupDO()

            for plan in BackupPlanMINIO.objects.all():
                lastRunDay = plan.lastRun.split(':')[0]
                lastRunMonth = plan.lastRun.split(':')[1]

                if plan.freq == 'Daily' and lastRunDay != time.strftime("%d"):
                    self.data = {}
                    self.data['planName'] = plan.name
                    self.forceRunAWSBackupMINIO()
                else:
                    if lastRunMonth == time.strftime("%m"):
                        days = int(time.strftime("%d")) - int(lastRunDay)
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackupMINIO()
                    else:
                        days = 30 - int(lastRunDay)
                        days = days + int(time.strftime("%d"))
                        if days >= 6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackupMINIO()

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [S3Backups.runAWSBackups]')


def main():
    pathToFile = "/home/cyberpanel/" + str(randint(1000, 9999))
    file = open(pathToFile, "w")
    file.close()

    finalData = json.dumps({'randomFile': pathToFile})
    requests.post("https://localhost:8090/api/runAWSBackups", data=finalData, verify=False)


if __name__ == "__main__":
    main()
