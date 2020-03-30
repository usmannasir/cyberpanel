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
from websiteFunctions.models import GitLogs, Websites
from websiteFunctions.website import WebsiteManager
import time

try:
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.mailUtilities import mailUtilities
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
except:
    pass

class IncScheduler():
    logPath = '/home/cyberpanel/incbackuplogs'
    gitFolder = '/home/cyberpanel/git'

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


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    args = parser.parse_args()

    IncScheduler.startBackup(args.function)
    IncScheduler.git(args.function)
    IncScheduler.checkDiskUsage()


if __name__ == "__main__":
    main()