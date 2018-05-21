import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os
import requests
import json
import time
from backupUtilities import backupUtilities
from re import match,I,M

class backupSchedule:

    @staticmethod
    def remoteBackupLogging(fileName, message):
        try:
            file = open(fileName,'a')
            file.writelines("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] "+ message + "\n")
            file.close()
        except IOError,msg:
            return "Can not write to error file."


    @staticmethod
    def createBackup(virtualHost, ipAddress, backupLogPath , port):
        try:

            backupSchedule.remoteBackupLogging(backupLogPath, "Preparing to create backup for: " + virtualHost)
            backupSchedule.remoteBackupLogging(backupLogPath, "Backup started for: " + virtualHost)

            finalData = json.dumps({'websiteToBeBacked': virtualHost})
            r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData)
            data = json.loads(r.text)
            backupPath = data['tempStorage']


            while (1):
                r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData)
                time.sleep(2)
                data = json.loads(r.text)

                if data['backupStatus'] == 0:
                    break
                elif data['abort'] == 1:
                    break

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

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createBackup]")

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
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def prepare():
        try:
            destinations = backupUtilities.destinationsPath

            backupLogPath = "/usr/local/lscp/logs/backup_log."+time.strftime("%I-%M-%S-%a-%b-%Y")

            backupSchedule.remoteBackupLogging(backupLogPath,"#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Backup log for: " +time.strftime("%I-%M-%S-%a-%b-%Y"))
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


            if backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                checkConn = backupUtilities.checkConnection(ipAddress)
                if checkConn[0] == 0:
                    backupSchedule.remoteBackupLogging(backupLogPath, "Connection to: " + ipAddress+ " Failed, please resetup this destination from CyberPanel, aborting.")
                    return 0
                else:
                    ## Create backup dir on remote server

                    command = "sudo ssh -o StrictHostKeyChecking=no -p " + port + " -i /root/.ssh/cyberpanel root@" + ipAddress + " mkdir -p /home/backup/"+ ipAddressLocal + "/" + time.strftime("%a-%b")
                    subprocess.call(shlex.split(command))
                    pass
            else:
                backupSchedule.remoteBackupLogging(backupLogPath, "Host: " + ipAddress + " is down, aborting.")
                return 0

            for virtualHost in os.listdir("/home"):
                if match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', virtualHost, M | I):
                    backupSchedule.createBackup(virtualHost, ipAddress, backupLogPath, port)

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [prepare]")


backupSchedule.prepare()