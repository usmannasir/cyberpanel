#!/usr/local/CyberCP/bin/python2
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
    import json
    from .models import *
    from math import ceil
    import requests
    import time
    from random import randint
    import subprocess, shlex
    from plogical.processUtilities import ProcessUtilities
except:
    import threading as multi
    from random import randint
    import json
    import requests
    import subprocess, shlex

class S3Backups(multi.Thread):

    def __init__(self, request = None, data = None, function = None):
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
            elif self.function == 'runAWSBackups':
                self.runAWSBackups()
        except BaseException, msg:
            logging.writeToFile( str(msg) + ' [S3Backups.run]')

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

        for items in reversed(logs):
            dic = { 'id': items.id, 'timeStamp': items.timeStamp, 'level': items.level, 'mesg': items.msg }
            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)
            counter = counter + 1

        json_data = json_data + ']'
        return json_data

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

            cronPath = '/etc/crontab'

            command = 'sudo cat ' + cronPath
            output = subprocess.check_output(shlex.split(command)).split('\n')

            insertCron = 1

            for items in output:
                if items.find('s3backups.py') > -1:
                    insertCron = 0
                    break

            if insertCron:
                pathToFile = "/home/cyberpanel/" + str(randint(1000, 9999))
                writeToFile = open(pathToFile, 'w')
                for items in output:
                    writeToFile.writelines(items + '\n')
                writeToFile.writelines('0 24 * * * cyberpanel /usr/local/CyberCP/bin/python2 /usr/local/CyberCP/s3Backups/s3Backups.py\n')
                writeToFile.close()
                command = 'sudo mv ' + pathToFile + ' /etc/crontab'
                ProcessUtilities.executioner(command)

            return proc.ajax(1, None)

        except BaseException, msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def fetchBuckets(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')


            s3 = boto3.resource('s3')
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

        except BaseException, msg:
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

            newPlan = BackupPlan(owner=admin, name=self.data['planName'], freq = self.data['frequency'],
                                 retention= self.data['retenion'], bucket= self.data['bucketName'])
            newPlan.save()

            for items in self.data['websitesInPlan']:
                wp = WebsitesInPlan(owner=newPlan, domain=items)
                wp.save()

            return proc.ajax(1, None)

        except BaseException, msg:
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

        except BaseException, msg:
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

        except BaseException, msg:
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

        except BaseException, msg:
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

        except BaseException, msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def savePlanChanges(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can use AWS S3 Backups.')

            logging.writeToFile('hello world')

            changePlan = BackupPlan.objects.get(name=self.data['planName'])

            changePlan.bucket = self.data['bucketName']
            changePlan.freq = self.data['frequency']
            changePlan.retention = self.data['retention']

            changePlan.save()

            return proc.ajax(1, None)

        except BaseException, msg:
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
            logs = backupPlan.backuplogs_set.all()

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            jsonData = S3Backups.getLogsInJson(logs[finalPageNumber:endPageNumber])

            data = {}
            data['data'] = jsonData
            data['pagination'] = pagination

            return proc.ajax(1, None, data)

        except BaseException, msg:
            proc = httpProc(self.request, None, None)
            return proc.ajaxPre(0, str(msg))

    def createBackup(self, virtualHost):
        finalData = json.dumps({'websiteToBeBacked': virtualHost})

        r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData)

        data = json.loads(r.text)
        try:
            backupPath = data['tempStorage']
        except:
            pass

        while (1):
            r = requests.post("http://localhost:5003/backup/backupStatus", data=finalData)
            time.sleep(2)
            data = json.loads(r.text)

            if data['backupStatus'] == 0:
                return 0, data['error_message']
            elif data['abort'] == 1:
                return 1, backupPath

    def forceRunAWSBackup(self):
        try:

            s3 = boto3.resource('s3')
            plan = BackupPlan.objects.get(name=self.data['planName'])
            bucketName = plan.bucket.strip('\n').strip(' ')
            runTime = time.strftime("%d:%m:%Y")

            ## Set Expiration for objects
            try:
                client = boto3.client('s3')
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
            except BaseException, msg:
                BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR', msg=str(msg)).save()

            ##

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='INFO', msg='Unauthorised user tried to run AWS Backups.').save()
                return 0

            BackupLogs(owner=plan,level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"),  msg='Starting backup process..').save()

            for items in plan.websitesinplan_set.all():
                result = self.createBackup(items.domain)
                if result[0]:
                    data = open(result[1] + ".tar.gz", 'rb')
                    s3.Bucket(bucketName).put_object(Key=plan.name + '/' + runTime + '/' + result[1].split('/')[-1] + ".tar.gz", Body=data)
                    BackupLogs(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), msg='Backup successful for ' + items.domain + '.').save()
                else:
                    BackupLogs(owner=plan, level='ERROR', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), msg='Backup failed for ' + items.domain + '. Error: ' + result[1]).save()


            plan.lastRun = runTime
            plan.save()

            BackupLogs(owner=plan, level='INFO', timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), msg='Backup Process Finished.').save()


        except BaseException, msg:
            logging.writeToFile(str(msg) + ' [S3Backups.runBackupPlan]')
            plan = BackupPlan.objects.get(name=self.data['planName'])
            BackupLogs(owner=plan, timeStamp=time.strftime("%b %d %Y, %H:%M:%S"), level='ERROR', msg=str(msg)).save()

    def runAWSBackups(self):
        try:
            admin = Administrator.objects.get(pk=1)
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
                        if days >=6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackup()
                    else:
                        days = 30 - int(lastRunDay)
                        days = days + int(time.strftime("%d"))
                        if days >=6:
                            self.data = {}
                            self.data['planName'] = plan.name
                            self.forceRunAWSBackup()

        except BaseException, msg:
            logging.writeToFile(str(msg) + ' [S3Backups.runAWSBackups]')

def main():

    pathToFile = "/home/cyberpanel/" + str(randint(1000, 9999))
    file = open(pathToFile, "w")
    file.close()

    finalData = json.dumps({'randomFile': pathToFile})
    requests.post("http://localhost:5003/api/runAWSBackups", data=finalData,verify=False)

if __name__ == "__main__":
    main()

