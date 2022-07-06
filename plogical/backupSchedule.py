#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os
import time
from plogical.backupUtilities import backupUtilities
from re import match,I,M
from websiteFunctions.models import Backups, BackupJob, BackupJobLogs
from plogical.processUtilities import ProcessUtilities
from random import randint
import json, requests
from datetime import datetime
import signal


class backupSchedule:
    now = datetime.now()
    LOCAL = 0
    REMOTE = 1
    INFO = 0
    ERROR = 1
    backupLog = ''
    runningPath = '/home/cyberpanel/remoteBackupPID'

    @staticmethod
    def remoteBackupLogging(fileName, message, status = 0):
        try:
            file = open(fileName,'a')
            file.writelines("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] "+ message + "\n")
            print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] "+ message + "\n"))
            file.close()

            if backupSchedule.backupLog == '':
                pass
            else:
                BackupJobLogs(owner=backupSchedule.backupLog, status=status, message="[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] "+ message).save()

        except IOError as msg:
            return "Can not write to error file."

    @staticmethod
    def createLocalBackup(virtualHost, backupLogPath):
        try:

            backupSchedule.remoteBackupLogging(backupLogPath, "Starting local backup for: " + virtualHost)

            ###

            pathToFile = "/home/cyberpanel/" + str(randint(1000, 9999))
            file = open(pathToFile, "w+")
            file.close()

            port = ProcessUtilities.fetchCurrentPort()

            finalData = json.dumps({'randomFile': pathToFile, 'websiteToBeBacked': virtualHost})
            r = requests.post("https://localhost:%s/backup/localInitiate" % (port), data=finalData, verify=False)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(r.text)

            data = json.loads(r.text)
            tempStoragePath = data['tempStorage']

            backupSchedule.remoteBackupLogging(backupLogPath, "Waiting for backup to complete.. ")
            time.sleep(5)
            schedulerPath = '/home/cyberpanel/%s-backup.txt' % (virtualHost)

            killCounter = 0

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

                ifRunning = ProcessUtilities.outputExecutioner('ps aux')

                if os.path.exists('/usr/local/CyberCP/debug'):
                    message = 'Output of px aux when running remote backup status check: %s' % (ifRunning)
                    logging.CyberCPLogFileWriter.writeToFile(message)


                if (ifRunning.find('startBackup') > -1 or ifRunning.find('BackupRoot') > -1) and ifRunning.find('/%s/' % (backupDomain)):
                    if os.path.exists('/usr/local/CyberCP/debug'):
                        message = 'If running found.'
                        logging.CyberCPLogFileWriter.writeToFile(message)

                    if os.path.exists(status):
                        if os.path.exists('/usr/local/CyberCP/debug'):
                            message = 'If running found. and status file exists'
                            logging.CyberCPLogFileWriter.writeToFile(message)

                        status = open(status, 'r').read()
                        time.sleep(2)

                        if status.find("Completed") > -1:

                            ### Removing Files

                            command = 'sudo rm -f ' + status
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + backupFileNamePath
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + pid
                            ProcessUtilities.normalExecutioner(command)

                            backupSchedule.remoteBackupLogging(backupLogPath, "Backup Completed for: " + virtualHost)
                            try:
                                os.remove(pathToFile)
                            except:
                                pass
                            return 1, tempStoragePath

                        elif status.find("[5009]") > -1:
                            if os.path.exists('/usr/local/CyberCP/debug'):
                                message = 'If running found. status file exists but error'
                                logging.CyberCPLogFileWriter.writeToFile(message)
                            ## removing status file, so that backup can re-run
                            try:
                                command = 'sudo rm -f ' + status
                                ProcessUtilities.normalExecutioner(command)

                                command = 'sudo rm -f ' + backupFileNamePath
                                ProcessUtilities.normalExecutioner(command)

                                command = 'sudo rm -f ' + pid
                                ProcessUtilities.normalExecutioner(command)

                                command = 'rm -rf %s' % (tempStoragePath)
                                ProcessUtilities.normalExecutioner(command)

                                backupObs = Backups.objects.filter(fileName=fileName)
                                for items in backupObs:
                                    items.delete()

                            except:
                                pass

                            backupSchedule.remoteBackupLogging(backupLogPath,
                                                               "Local backup creating failed for %s, Error message: %s" % (
                                                               virtualHost, status), backupSchedule.ERROR)

                            try:
                                os.remove(pathToFile)
                            except:
                                pass

                            command = 'rm -rf %s' % (tempStoragePath)
                            ProcessUtilities.normalExecutioner(command)
                            return 0, tempStoragePath

                        elif os.path.exists(schedulerPath):
                            if os.path.exists('/usr/local/CyberCP/debug'):
                                message = 'If running found. status file exists, scheduler path also exists hence killed'
                                logging.CyberCPLogFileWriter.writeToFile(message)
                            backupSchedule.remoteBackupLogging(backupLogPath, 'Backup process killed. Error: %s' % (
                                open(schedulerPath, 'r').read()),
                                                               backupSchedule.ERROR)
                            os.remove(schedulerPath)
                            command = 'rm -rf %s' % (tempStoragePath)
                            ProcessUtilities.normalExecutioner(command)
                            return 0, 'Backup process killed.'

                else:
                    if os.path.exists('/usr/local/CyberCP/debug'):
                        message = 'If running not found.'
                        logging.CyberCPLogFileWriter.writeToFile(message)
                    if os.path.exists(status):
                        if os.path.exists('/usr/local/CyberCP/debug'):
                            message = 'if running not found, Status file exists'
                            logging.CyberCPLogFileWriter.writeToFile(message)
                        status = open(status, 'r').read()
                        time.sleep(2)

                        if status.find("Completed") > -1:

                            ### Removing Files

                            command = 'sudo rm -f ' + status
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + backupFileNamePath
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + pid
                            ProcessUtilities.normalExecutioner(command)

                            backupSchedule.remoteBackupLogging(backupLogPath, "Backup Completed for: " + virtualHost)
                            try:
                                os.remove(pathToFile)
                            except:
                                pass
                            return 1, tempStoragePath
                        elif os.path.exists(schedulerPath):

                            if os.path.exists('/usr/local/CyberCP/debug'):
                                message = 'if running not found, Status file exists, scheduler path exists thus killed.'
                                logging.CyberCPLogFileWriter.writeToFile(message)

                            backupSchedule.remoteBackupLogging(backupLogPath, 'Backup process killed. Error: %s' % (open(schedulerPath, 'r').read()),
                                                           backupSchedule.ERROR)
                            os.remove(schedulerPath)
                            command = 'rm -rf %s' % (tempStoragePath)
                            ProcessUtilities.normalExecutioner(command)
                            return 0, 'Backup process killed.'
                    else:
                        if os.path.exists('/usr/local/CyberCP/debug'):
                            message = 'Status file does not exists.'
                            logging.CyberCPLogFileWriter.writeToFile(message)
                        if killCounter == 1:

                            if os.path.exists('/usr/local/CyberCP/debug'):
                                message = 'if running not found, Status file  does not exists, kill counter 1, thus killed'
                                logging.CyberCPLogFileWriter.writeToFile(message)

                            command = 'rm -rf %s' % (tempStoragePath)
                            ProcessUtilities.normalExecutioner(command)

                            return 0, 'Backup process killed without reporting any error. [184]'
                        elif os.path.exists(schedulerPath):
                            if os.path.exists('/usr/local/CyberCP/debug'):
                                message = 'if running not found, Status file does not exists, scheduler path found thus killed'
                                logging.CyberCPLogFileWriter.writeToFile(message)
                            backupSchedule.remoteBackupLogging(backupLogPath, 'Backup process killed. Error: %s' % (
                                open(schedulerPath, 'r').read()),
                                                               backupSchedule.ERROR)
                            os.remove(schedulerPath)
                            command = 'rm -rf %s' % (tempStoragePath)
                            ProcessUtilities.normalExecutioner(command)
                            return 0, 'Backup process killed.'
                        else:
                            time.sleep(10)
                            killCounter = 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [119:startBackup]")
            backupSchedule.remoteBackupLogging(backupLogPath,
                                               "Local backup creating failed for %s, Error message: %s" % (
                                               virtualHost, str(msg)), backupSchedule.ERROR)
            return 0, str(msg)

    @staticmethod
    def createBackup(virtualHost, ipAddress, backupLogPath , port='22', user='root'):
        try:

            backupSchedule.remoteBackupLogging(backupLogPath, "Preparing to create backup for: " + virtualHost)
            backupSchedule.remoteBackupLogging(backupLogPath, "Backup started for: " + virtualHost)

            retValues = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

            if retValues[0] == 1:
                backupPath = retValues[1]

                backupSchedule.remoteBackupLogging(backupLogPath, "Backup created for: " + virtualHost)

                ## Prepping to send backup.

                backupSchedule.remoteBackupLogging(backupLogPath, "Preparing to send backup for: " + virtualHost +" to " + ipAddress)

                backupSchedule.sendBackup(backupPath+".tar.gz", ipAddress, backupLogPath, port, user)

                backupSchedule.remoteBackupLogging(backupLogPath, "Backup for: " + virtualHost + " is sent to " + ipAddress)

                ## Backup sent.


                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")
                return 1
            else:

                backupSchedule.remoteBackupLogging(backupLogPath, 'Remote backup creation failed for %s.' % (virtualHost) )

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupSchedule.createBackup]")

    @staticmethod
    def sendBackup(backupPath, IPAddress, backupLogPath , port='22', user='root'):
        try:

            ## IPAddress of local server

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddressLocal = ipData.split('\n', 1)[0]

            ##

            writeToFile = open(backupLogPath, "a")
            command = "scp -o StrictHostKeyChecking=no -P "+port+" -i /root/.ssh/cyberpanel " + backupPath + " " + user + "@" + IPAddress+":~/backup/" + ipAddressLocal + "/" + time.strftime("%m.%d.%Y_%H-%M-%S") + "/"
            subprocess.call(shlex.split(command), stdout=writeToFile)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(command)

            ## Remove backups already sent to remote destinations

            os.remove(backupPath)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [189:startBackup]")

    @staticmethod
    def prepare():
        try:

            if os.path.exists(backupSchedule.runningPath):
                pid = open(backupSchedule.runningPath, 'r').read()

                output = ProcessUtilities.outputExecutioner('ps aux')

                if output.find('/usr/local/CyberCP/plogical/backupSchedule.py') > -1 and output.find(pid) > -1:
                    print(
                        '\n\nRemote backup is already running with PID: %s. If you want to run again kindly kill the backup process: \n\n kill -9 %s.\n\n' % (
                        pid, pid))
                    return 0
                else:
                    os.remove(backupSchedule.runningPath)


            writeToFile = open(backupSchedule.runningPath, 'w')
            writeToFile.write(str(os.getpid()))
            writeToFile.close()

            ## IP of Remote server.

            destinations = backupUtilities.destinationsPath
            data = json.loads(open(destinations, 'r').read())
            port = data['port']

            try:
                user = data['user']
            except:
                user = 'root'

            ipAddress = data['ipAddress']

            jobSuccessSites = 0
            jobFailedSites = 0

            backupLogPath = "/usr/local/lscp/logs/backup_log." + time.strftime("%m.%d.%Y_%H-%M-%S")

            backupSchedule.backupLog = BackupJob(logFile=backupLogPath, location=backupSchedule.REMOTE,
                                                 jobSuccessSites=jobSuccessSites, jobFailedSites=jobFailedSites,
                                                 ipAddress=ipAddress, port=port)
            backupSchedule.backupLog.save()


            destinations = backupUtilities.destinationsPath


            backupSchedule.remoteBackupLogging(backupLogPath,"#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Backup log for: " +time.strftime("%m.%d.%Y_%H-%M-%S"))
            backupSchedule.remoteBackupLogging(backupLogPath,"#################################################\n")

            backupSchedule.remoteBackupLogging(backupLogPath, "")
            backupSchedule.remoteBackupLogging(backupLogPath, "")

            ## IPAddress of local server

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddressLocal = ipData.split('\n', 1)[0]


            if backupUtilities.checkIfHostIsUp(ipAddress) != 1:
                backupSchedule.remoteBackupLogging(backupLogPath, "Ping for : " + ipAddress + " does not seems to work, however we will continue.")


            checkConn = backupUtilities.checkConnection(ipAddress)
            if checkConn[0] == 0:
                backupSchedule.remoteBackupLogging(backupLogPath,
                                                   "Connection to: " + ipAddress + " Failed, please resetup this destination from CyberPanel, aborting.")
                return 0
            else:
                ## Create backup dir on remote server in ~/backup

                command = "ssh -o StrictHostKeyChecking=no -p " + port + " -i /root/.ssh/cyberpanel " + user + "@" + ipAddress + " mkdir -p ~/backup/" + ipAddressLocal + "/" + time.strftime(
                    "%a-%b")
                subprocess.call(shlex.split(command))
                pass

            for virtualHost in os.listdir("/home"):
                if match(r'^[a-zA-Z0-9-]*[a-zA-Z0-9-]{0,61}[a-zA-Z0-9-](?:\.[a-zA-Z0-9-]{2,})+$', virtualHost, M | I):
                    if backupSchedule.createBackup(virtualHost, ipAddress, backupLogPath, port, user):
                        jobSuccessSites = jobSuccessSites + 1
                    else:
                        jobFailedSites = jobFailedSites + 1

            backupSchedule.backupLog.jobFailedSites = jobFailedSites
            backupSchedule.backupLog.jobSuccessSites = jobSuccessSites
            backupSchedule.backupLog.save()

            backupSchedule.remoteBackupLogging(backupLogPath, "Remote backup job completed.\n")

            if os.path.exists(backupSchedule.runningPath):
                os.remove(backupSchedule.runningPath)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [prepare]")

def main():
    backupSchedule.prepare()

def handler(signum, frame):
    diff = datetime.now() - backupSchedule.now
    logging.CyberCPLogFileWriter.writeToFile('Signal: %s, time spent: %s' % (str(signum), str(diff.total_seconds())))


if __name__ == "__main__":
    for i in range(1,32):
        if i == 9 or i == 19 or i == 32:
            continue
        signal.signal(i, handler)
    main()