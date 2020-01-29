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
from websiteFunctions.models import Backups
from plogical.processUtilities import ProcessUtilities
from random import randint
import json, requests
from datetime import datetime
import signal


class backupSchedule:
    now = datetime.now()

    @staticmethod
    def remoteBackupLogging(fileName, message):
        try:
            file = open(fileName,'a')
            file.writelines("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] "+ message + "\n")
            print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] "+ message + "\n"))
            file.close()
        except IOError as msg:
            return "Can not write to error file."

    @staticmethod
    def createLocalBackup(virtualHost, backupLogPath):
        try:

            startingTime = datetime.now()

            backupSchedule.remoteBackupLogging(backupLogPath, "Starting local backup for: " + virtualHost)

            ###

            pathToFile = "/home/cyberpanel/" + str(randint(1000, 9999))
            file = open(pathToFile, "w+")
            file.close()

            finalData = json.dumps({'randomFile': pathToFile, 'websiteToBeBacked': virtualHost})
            r = requests.post("https://localhost:8090/backup/localInitiate", data=finalData, verify=False)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(r.text)

            data = json.loads(r.text)
            tempStoragePath = data['tempStorage']

            backupSchedule.remoteBackupLogging(backupLogPath, "Waiting for backup to complete.. ")
            time.sleep(5)
            schedulerPath = '/home/cyberpanel/%s-backup.txt' % (virtualHost)

            while (1):
                diff = datetime.now() - startingTime

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
                    print(status)
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
                        ## removing status file, so that backup can re-run
                        try:
                            command = 'sudo rm -f ' + status
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + backupFileNamePath
                            ProcessUtilities.normalExecutioner(command)

                            command = 'sudo rm -f ' + pid
                            ProcessUtilities.normalExecutioner(command)

                            backupObs = Backups.objects.filter(fileName=fileName)
                            for items in backupObs:
                                items.delete()

                        except:
                            pass

                        backupSchedule.remoteBackupLogging(backupLogPath, "An error occurred, Error message: " + status)
                        try:
                            os.remove(pathToFile)
                        except:
                            pass
                        return 0, tempStoragePath
                    elif os.path.exists(schedulerPath):
                        os.remove(schedulerPath)
                        return 0, 'Backup process killed without reporting any error.'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [119:startBackup]")
            return 0, str(msg)

    @staticmethod
    def createBackup(virtualHost, ipAddress, backupLogPath , port):
        try:

            backupSchedule.remoteBackupLogging(backupLogPath, "Preparing to create backup for: " + virtualHost)
            backupSchedule.remoteBackupLogging(backupLogPath, "Backup started for: " + virtualHost)

            retValues = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

            if retValues[0] == 1:
                backupPath = retValues[1]

                backupSchedule.remoteBackupLogging(backupLogPath, "Backup created for: " + virtualHost)

                ## Prepping to send backup.

                backupSchedule.remoteBackupLogging(backupLogPath, "Preparing to send backup for: " + virtualHost +" to " + ipAddress)

                backupSchedule.sendBackup(backupPath+".tar.gz", ipAddress, backupLogPath, port)

                backupSchedule.remoteBackupLogging(backupLogPath, "Backup for: " + virtualHost + " is sent to " + ipAddress)

                ## Backup sent.


                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")
            else:

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupSchedule.createBackup]")

    @staticmethod
    def sendBackup(backupPath, IPAddress, backupLogPath , port):
        try:

            ## IPAddress of local server

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddressLocal = ipData.split('\n', 1)[0]

            ##

            writeToFile = open(backupLogPath, "a")
            command = "sudo scp -o StrictHostKeyChecking=no -P "+port+" -i /root/.ssh/cyberpanel " + backupPath + " root@"+IPAddress+":/home/backup/" + ipAddressLocal + "/" + time.strftime("%a-%b") + "/"
            subprocess.call(shlex.split(command), stdout=writeToFile)

            ## Remove backups already sent to remote destinations

            os.remove(backupPath)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [189:startBackup]")

    @staticmethod
    def prepare():
        try:
            destinations = backupUtilities.destinationsPath

            backupLogPath = "/usr/local/lscp/logs/backup_log."+time.strftime("%m.%d.%Y_%H-%M-%S")

            backupSchedule.remoteBackupLogging(backupLogPath,"#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Backup log for: " +time.strftime("%m.%d.%Y_%H-%M-%S"))
            backupSchedule.remoteBackupLogging(backupLogPath,"#################################################\n")

            backupSchedule.remoteBackupLogging(backupLogPath, "")
            backupSchedule.remoteBackupLogging(backupLogPath, "")

            ## IP of Remote server.

            data = open(destinations,'r').readlines()
            ipAddress = data[0].strip("\n")
            port = data[1].strip("\n")

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
                ## Create backup dir on remote server

                command = "sudo ssh -o StrictHostKeyChecking=no -p " + port + " -i /root/.ssh/cyberpanel root@" + ipAddress + " mkdir -p /home/backup/" + ipAddressLocal + "/" + time.strftime(
                    "%a-%b")
                subprocess.call(shlex.split(command))
                pass

            for virtualHost in os.listdir("/home"):
                if match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', virtualHost, M | I):
                    backupSchedule.createBackup(virtualHost, ipAddress, backupLogPath, port)


            backupSchedule.remoteBackupLogging(backupLogPath, "Remote backup job completed.\n")



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