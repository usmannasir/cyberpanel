#!/usr/local/CyberCP/bin/python
import os.path
import sys
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
import django
django.setup()
from IncBackups.IncBackupsControl import IncJobs
from IncBackups.models import BackupJob
from random import randint
import argparse
import json
from websiteFunctions.models import GitLogs, Websites, GDrive, GDriveJobLogs
from websiteFunctions.website import WebsiteManager
import time
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from plogical.backupSchedule import backupSchedule
import requests
from websiteFunctions.models import NormalBackupJobs, NormalBackupSites, NormalBackupDests, NormalBackupJobLogs
try:
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.mailUtilities import mailUtilities
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
except:
    pass

class IncScheduler():
    logPath = '/home/cyberpanel/incbackuplogs'
    gitFolder = '/home/cyberpanel/git'

    timeFormat = time.strftime("%m.%d.%Y_%H-%M-%S")

    ### Normal scheduled backups constants

    frequency = 'frequency'
    allSites = 'allSites'
    currentStatus = 'currentStatus'
    lastRun = 'lastRun'

    @staticmethod
    def startBackup(type):
        try:
            logging.statusWriter(IncScheduler.logPath, 'Starting Incremental Backup job..', 1)
            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            for job in BackupJob.objects.all():
                logging.statusWriter(IncScheduler.logPath, 'Job Description:\n\n Destination: %s, Frequency: %s.\n ' % (job.destination, job.frequency), 1)
                if job.frequency == type:
                    for web in job.jobsites_set.all():
                        logging.statusWriter(IncScheduler.logPath, 'Backing up %s.' % (web.website), 1)

                        extraArgs = {}
                        extraArgs['website'] = web.website
                        extraArgs['tempPath'] = tempPath
                        extraArgs['backupDestinations'] = job.destination

                        if job.websiteData == 1:
                            extraArgs['websiteData'] = True
                        else:
                            extraArgs['websiteData'] = False

                        if job.websiteDatabases == 1:
                            extraArgs['websiteDatabases'] = True
                        else:
                            extraArgs['websiteDatabases'] = False

                        if job.websiteDataEmails == 1:
                            extraArgs['websiteEmails'] = True
                        else:
                            extraArgs['websiteEmails'] = False

                        extraArgs['websiteSSLs'] = False

                        startJob = IncJobs('createBackup', extraArgs)
                        startJob.start()

                        ### Checking status

                        while True:
                            if os.path.exists(tempPath):
                                result = open(tempPath, 'r').read()

                                if result.find("Completed") > -1:

                                    ### Removing Files

                                    os.remove(tempPath)

                                    logging.statusWriter(IncScheduler.logPath, 'Backed up %s.' % (web.website), 1)
                                    break
                                elif result.find("[5009]") > -1:
                                    ## removing status file, so that backup can re-runn
                                    try:
                                        os.remove(tempPath)
                                    except:
                                        pass

                                    logging.statusWriter(IncScheduler.logPath, 'Failed backup for %s, error: %s.' % (web.website, result), 1)
                                    break

        except BaseException as msg:
            logging.writeToFile(str(msg))

    @staticmethod
    def git(type):
        try:
            for website in os.listdir(IncScheduler.gitFolder):
                finalText = ''
                web = Websites.objects.get(domain=website)

                message = '[%s Cron] Checking if %s has any pending commits on %s.' % (type, website, time.strftime("%m.%d.%Y_%H-%M-%S"))
                finalText = '%s\n' % (message)
                GitLogs(owner=web, type='INFO', message = message).save()

                finalPathInside = '%s/%s' % (IncScheduler.gitFolder, website)

                for file in os.listdir(finalPathInside):

                    try:

                        ##
                        finalPathConf = '%s/%s' % (finalPathInside, file)

                        gitConf = json.loads(open(finalPathConf, 'r').read())

                        data = {}
                        data['domain'] = gitConf['domain']
                        data['folder'] = gitConf['folder']
                        data['commitMessage'] = 'Auto commit by CyberPanel %s cron on %s' % (type, time.strftime('%m-%d-%Y_%H-%M-%S'))

                        if gitConf['autoCommit'] == type:

                            wm = WebsiteManager()
                            resp = wm.commitChanges(1, data)
                            resp = json.loads(resp.content)

                            if resp['status'] == 1:
                                message = 'Folder: %s, Status: %s' % (gitConf['folder'], resp['commandStatus'])
                                finalText = '%s\n%s' % (finalText, message)
                                GitLogs(owner=web, type='INFO', message=message).save()
                            else:
                                message = 'Folder: %s, Status: %s' % (gitConf['folder'], resp['commandStatus'])
                                finalText = '%s\n%s' % (finalText, message)
                                GitLogs(owner=web, type='ERROR', message=message).save()

                        if gitConf['autoPush'] == type:

                            wm = WebsiteManager()
                            resp = wm.gitPush(1, data)
                            resp = json.loads(resp.content)

                            if resp['status'] == 1:
                                GitLogs(owner=web, type='INFO', message=resp['commandStatus']).save()
                                finalText = '%s\n%s' % (finalText, resp['commandStatus'])
                            else:
                                GitLogs(owner=web, type='ERROR', message=resp['commandStatus']).save()
                                finalText = '%s\n%s' % (finalText, resp['commandStatus'])
                    except BaseException as msg:
                        message = 'File: %s, Status: %s' % (file, str(msg))
                        finalText = '%s\n%s' % (finalText, message)


                message = '[%s Cron] Finished checking for %s on %s.' % (type, website, time.strftime("%m.%d.%Y_%H-%M-%S"))
                finalText = '%s\n%s' % (finalText, message)
                logging.SendEmail(web.adminEmail, web.adminEmail, finalText, 'Git report for %s.' % (web.domain))
                GitLogs(owner=web, type='INFO', message=message).save()

        except BaseException as msg:
            logging.writeToFile('%s. [IncScheduler.git:90]' % (str(msg)))

    @staticmethod
    def checkDiskUsage():

        try:

            import psutil, math
            from websiteFunctions.models import Administrator
            admin = Administrator.objects.get(pk=1)

            diskUsage = math.floor(psutil.disk_usage('/')[3])

            from plogical.acl import ACLManager
            message = '%s - Disk Usage Warning - CyberPanel' % (ACLManager.fetchIP())

            if diskUsage >= 50 and diskUsage <= 60 :

                finalText = 'Current disk usage at "/" is %s percent. No action required.' % (str(diskUsage))
                logging.SendEmail(admin.email, admin.email, finalText, message)

            elif diskUsage >= 60 and diskUsage <= 80:

                finalText = 'Current disk usage at "/" is %s percent. We recommend clearing log directory by running \n\n rm -rf /usr/local/lsws/logs/*. \n\n When disk usage go above 80 percent we will automatically run this command.' % (str(diskUsage))
                logging.SendEmail(admin.email, admin.email, finalText, message)

            elif diskUsage > 80:

                finalText = 'Current disk usage at "/" is %s percent. We are going to run below command to free up space, If disk usage is still high, manual action is required by the system administrator. \n\n rm -rf /usr/local/lsws/logs/*.' % (
                    str(diskUsage))
                logging.SendEmail(admin.email, admin.email, finalText, message)

                command = 'rm -rf /usr/local/lsws/logs/*'
                import subprocess
                subprocess.call(command, shell=True)

        except BaseException as msg:
            logging.writeToFile('[IncScheduler:193:checkDiskUsage] %s.' % str(msg))

    @staticmethod
    def runGoogleDriveBackups(type):

        backupRunTime = time.strftime("%m.%d.%Y_%H-%M-%S")
        backupLogPath = "/usr/local/lscp/logs/local_backup_log." + backupRunTime

        for items in GDrive.objects.all():
            try:
                if items.runTime == type:
                    gDriveData = json.loads(items.auth)
                    try:
                        credentials = google.oauth2.credentials.Credentials(gDriveData['token'], gDriveData['refresh_token'],
                                                                gDriveData['token_uri'], None, None, gDriveData['scopes'])


                        drive = build('drive', 'v3', credentials=credentials)
                        drive.files().list(pageSize=10, fields="files(id, name)").execute()
                    except BaseException as msg:
                        try:

                            finalData = json.dumps({'refresh_token': gDriveData['refresh_token']})
                            r = requests.post("https://platform.cyberpanel.net/refreshToken", data=finalData
                                              )
                            gDriveData['token'] = json.loads(r.text)['access_token']

                            credentials = google.oauth2.credentials.Credentials(gDriveData['token'],
                                                                                gDriveData['refresh_token'],
                                                                                gDriveData['token_uri'],
                                                                                None,
                                                                                None,
                                                                                gDriveData['scopes'])

                            drive = build('drive', 'v3', credentials=credentials)
                            drive.files().list(pageSize=5, fields="files(id, name)").execute()

                            items.auth = json.dumps(gDriveData)
                            items.save()
                        except BaseException as msg:
                            GDriveJobLogs(owner=items, status=backupSchedule.ERROR, message='Connection to this account failed. Delete and re-setup this account. Error: %s' % (str(msg))).save()
                            continue

                    try:
                        folderIDIP = gDriveData['folderIDIP']
                    except:

                        ipFile = "/etc/cyberpanel/machineIP"
                        f = open(ipFile)
                        ipData = f.read()
                        ipAddress = ipData.split('\n', 1)[0]

                        ## Create CyberPanel Folder

                        file_metadata = {
                            'name': '%s-%s' % (items.name, ipAddress),
                            'mimeType': 'application/vnd.google-apps.folder'
                        }
                        file = drive.files().create(body=file_metadata,
                                                            fields='id').execute()
                        folderIDIP = file.get('id')

                        gDriveData['folderIDIP'] = folderIDIP

                        items.auth = json.dumps(gDriveData)
                        items.save()

                    ### Current folder to store files

                    file_metadata = {
                        'name': time.strftime("%m.%d.%Y_%H-%M-%S"),
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [folderIDIP]
                    }
                    file = drive.files().create(body=file_metadata,
                                                fields='id').execute()
                    folderID = file.get('id')

                    ###

                    GDriveJobLogs(owner=items, status=backupSchedule.INFO, message='Starting backup job..').save()

                    for website in items.gdrivesites_set.all():
                        try:
                            GDriveJobLogs(owner=items, status=backupSchedule.INFO, message='Local backup creation started for %s..' % (website.domain)).save()

                            retValues = backupSchedule.createLocalBackup(website.domain, backupLogPath)

                            if retValues[0] == 0:
                                GDriveJobLogs(owner=items, status=backupSchedule.ERROR,
                                              message='[ERROR] Backup failed for %s, error: %s moving on..' % (website.domain, retValues[1])).save()
                                continue

                            completeFileToSend = retValues[1] + ".tar.gz"
                            fileName = completeFileToSend.split('/')[-1]

                            file_metadata = {
                                'name': '%s' % (fileName),
                                'parents': [folderID]
                            }
                            media = MediaFileUpload(completeFileToSend, mimetype='application/gzip', resumable=True)
                            try:
                                drive.files().create(body=file_metadata, media_body=media, fields='id').execute()
                            except:
                                finalData = json.dumps({'refresh_token': gDriveData['refresh_token']})
                                r = requests.post("https://platform.cyberpanel.net/refreshToken", data=finalData
                                                  )
                                gDriveData['token'] = json.loads(r.text)['access_token']

                                credentials = google.oauth2.credentials.Credentials(gDriveData['token'],
                                                                                    gDriveData['refresh_token'],
                                                                                    gDriveData['token_uri'],
                                                                                    None,
                                                                                    None,
                                                                                    gDriveData['scopes'])

                                drive = build('drive', 'v3', credentials=credentials)
                                drive.files().create(body=file_metadata, media_body=media, fields='id').execute()

                                items.auth = json.dumps(gDriveData)
                                items.save()

                            GDriveJobLogs(owner=items, status=backupSchedule.INFO,
                                          message='Backup for %s successfully sent to Google Drive.' % (website.domain)).save()

                            os.remove(completeFileToSend)

                        except BaseException as msg:
                            GDriveJobLogs(owner=items, status=backupSchedule.ERROR,
                                          message='[Site] Site backup failed, Error message: %s.' % (str(msg))).save()


                    GDriveJobLogs(owner=items, status=backupSchedule.INFO,
                                  message='Job Completed').save()
            except BaseException as msg:
                GDriveJobLogs(owner=items, status=backupSchedule.ERROR,
                              message='[Completely] Job failed, Error message: %s.' % (str(msg))).save()

    @staticmethod
    def startNormalBackups(type):
        from plogical.processUtilities import ProcessUtilities
        from plogical.backupSchedule import backupSchedule
        import socket

        ## SFTP Destination Config sample
        ## {"type": "SFTP", "ip": "ip", "username": "root", "port": "22", "path": "/home/backup"}

        ## Local Destination config sample
        ## {"type": "local", "path": "/home/backup"}

        ## Backup jobs config

        ## {"frequency": "Daily", "allSites": "Selected Only"}
        ## {"frequency": "Daily"}


        for backupjob in NormalBackupJobs.objects.all():

            jobConfig = json.loads(backupjob.config)
            destinationConfig = json.loads(backupjob.owner.config)

            currentTime = time.strftime("%m.%d.%Y_%H-%M-%S")

            if destinationConfig['type'] == 'local':

                finalPath = '%s/%s' % (destinationConfig['path'].rstrip('/'), currentTime)
                command = 'mkdir -p %s' % (finalPath)
                ProcessUtilities.executioner(command)

                if jobConfig[IncScheduler.frequency] == type:

                    ### Check if an old job prematurely killed, then start from there.
                    try:
                        oldJobContinue = 1
                        pid = jobConfig['pid']
                        stuckDomain = jobConfig['website']
                        finalPath = jobConfig['finalPath']
                        jobConfig['pid'] = str(os.getpid())

                        command = 'ps aux'
                        result = ProcessUtilities.outputExecutioner(command)

                        if result.find(pid) > -1 and result.find('IncScheduler.py') > -1:
                            quit(1)


                    except:
                        ### Save some important info in backup config
                        oldJobContinue = 0
                        jobConfig['pid'] = str(os.getpid())
                        jobConfig['finalPath'] = finalPath

                    NormalBackupJobLogs.objects.filter(owner=backupjob).delete()
                    NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO,
                                  message='Starting %s backup on %s..' % (type, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                    if oldJobContinue:
                        NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO, message='Will continue old killed job starting from %s.' % (stuckDomain)).save()

                    actualDomain = 0
                    try:
                        if jobConfig[IncScheduler.allSites] == 'all':
                            websites = Websites.objects.all().order_by('domain')
                            actualDomain = 1
                        else:
                            websites = backupjob.normalbackupsites_set.all().order_by('domain__domain')
                    except:
                        websites = backupjob.normalbackupsites_set.all().order_by('domain__domain')

                    doit = 0

                    for site in websites:
                        if actualDomain:
                            domain = site.domain
                        else:
                            domain = site.domain.domain


                        ## Save currently backing domain in db, so that i can restart from here when prematurely killed

                        jobConfig['website'] = domain
                        jobConfig[IncScheduler.lastRun] = time.strftime("%d %b %Y, %I:%M %p")
                        jobConfig[IncScheduler.currentStatus] = 'Running..'
                        backupjob.config = json.dumps(jobConfig)
                        backupjob.save()

                        if oldJobContinue and not doit:
                            if domain == stuckDomain:
                                doit = 1
                                continue
                            else:
                                continue

                        retValues = backupSchedule.createLocalBackup(domain, '/dev/null')

                        if retValues[0] == 0:
                            NormalBackupJobLogs(owner=backupjob, status=backupSchedule.ERROR,
                                                message='Backup failed for %s on %s.' % (
                                                domain, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                            SUBJECT = "Automatic backup failed for %s on %s." % (domain, currentTime)
                            adminEmailPath = '/home/cyberpanel/adminEmail'
                            adminEmail = open(adminEmailPath, 'r').read().rstrip('\n')
                            sender = 'root@%s' % (socket.gethostname())
                            TO = [adminEmail]
                            message = """\
From: %s
To: %s
Subject: %s
    
Automatic backup failed for %s on %s.
""" % (sender, ", ".join(TO), SUBJECT, domain, currentTime)

                            logging.SendEmail(sender, TO, message)
                        else:
                            backupPath = retValues[1] + ".tar.gz"

                            command = 'mv %s %s' % (backupPath, finalPath)
                            ProcessUtilities.executioner(command)

                            NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO,
                                                message='Backup completed for %s on %s.' % (
                                                    domain, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                    jobConfig = json.loads(backupjob.config)
                    if jobConfig['pid']:
                        del jobConfig['pid']
                    jobConfig[IncScheduler.currentStatus] = 'Not running'
                    backupjob.config = json.dumps(jobConfig)
                    backupjob.save()
            else:
                import subprocess
                import shlex
                finalPath = '%s/%s' % (destinationConfig['path'].rstrip('/'), currentTime)
                command = "ssh -o StrictHostKeyChecking=no -p " + destinationConfig['port'] + " -i /root/.ssh/cyberpanel " + destinationConfig['username'] + "@" + destinationConfig['ip'] + " mkdir -p %s" % (finalPath)
                subprocess.call(shlex.split(command))

                if jobConfig[IncScheduler.frequency] == type:

                    ### Check if an old job prematurely killed, then start from there.
                    try:
                        oldJobContinue = 1
                        pid = jobConfig['pid']
                        stuckDomain = jobConfig['website']
                        finalPath = jobConfig['finalPath']
                        jobConfig['pid'] = str(os.getpid())

                        command = 'ps aux'
                        result = ProcessUtilities.outputExecutioner(command)

                        if result.find(pid) > -1 and result.find('IncScheduler.py') > -1:
                            quit(1)


                    except:
                        ### Save some important info in backup config
                        oldJobContinue = 0
                        jobConfig['pid'] = str(os.getpid())
                        jobConfig['finalPath'] = finalPath

                    NormalBackupJobLogs.objects.filter(owner=backupjob).delete()
                    NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO,
                                        message='Starting %s backup on %s..' % (
                                        type, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                    if oldJobContinue:
                        NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO, message='Will continue old killed job starting from %s.' % (stuckDomain)).save()

                    actualDomain = 0
                    try:
                        if jobConfig[IncScheduler.allSites] == 'all':
                            websites = Websites.objects.all().order_by('domain')
                            actualDomain = 1
                        else:
                            websites = backupjob.normalbackupsites_set.all().order_by('domain__domain')
                    except:
                        websites = backupjob.normalbackupsites_set.all().order_by('domain__domain')

                    doit = 0

                    for site in websites:

                        if actualDomain:
                            domain = site.domain
                        else:
                            domain = site.domain.domain

                        ## Save currently backing domain in db, so that i can restart from here when prematurely killed

                        jobConfig['website'] = domain
                        jobConfig[IncScheduler.lastRun] = time.strftime("%d %b %Y, %I:%M %p")
                        jobConfig[IncScheduler.currentStatus] = 'Running..'
                        backupjob.config = json.dumps(jobConfig)
                        backupjob.save()

                        if oldJobContinue and not doit:
                            if domain == stuckDomain:
                                doit = 1
                                continue
                            else:
                                continue

                        retValues = backupSchedule.createLocalBackup(domain, '/dev/null')

                        if retValues[0] == 0:
                            NormalBackupJobLogs(owner=backupjob, status=backupSchedule.ERROR,
                                                message='Backup failed for %s on %s.' % (
                                                    domain, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                            SUBJECT = "Automatic backup failed for %s on %s." % (domain, currentTime)
                            adminEmailPath = '/home/cyberpanel/adminEmail'
                            adminEmail = open(adminEmailPath, 'r').read().rstrip('\n')
                            sender = 'root@%s' % (socket.gethostname())
                            TO = [adminEmail]
                            message = """\
From: %s
To: %s
Subject: %s

Automatic backup failed for %s on %s.
""" % (sender, ", ".join(TO), SUBJECT, domain, currentTime)

                            logging.SendEmail(sender, TO, message)
                        else:
                            backupPath = retValues[1] + ".tar.gz"

                            command = "scp -o StrictHostKeyChecking=no -P " + destinationConfig['port'] + " -i /root/.ssh/cyberpanel " + backupPath + " " + destinationConfig['username'] + "@" + destinationConfig['ip'] + ":%s" % (finalPath)
                            ProcessUtilities.executioner(command)

                            try:
                                os.remove(backupPath)
                            except:
                                pass

                            NormalBackupJobLogs(owner=backupjob, status=backupSchedule.INFO,
                                                message='Backup completed for %s on %s.' % (
                                                    domain, time.strftime("%m.%d.%Y_%H-%M-%S"))).save()

                    jobConfig = json.loads(backupjob.config)
                    if jobConfig['pid']:
                        del jobConfig['pid']
                    jobConfig[IncScheduler.currentStatus] = 'Not running'
                    backupjob.config = json.dumps(jobConfig)
                    backupjob.save()



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    args = parser.parse_args()

    IncScheduler.startBackup(args.function)
    IncScheduler.runGoogleDriveBackups(args.function)
    IncScheduler.git(args.function)
    IncScheduler.checkDiskUsage()
    IncScheduler.startNormalBackups(args.function)


if __name__ == "__main__":
    main()