import thread
import pexpect
import CyberCPLogFileWriter as logging
import subprocess
import shlex
from shutil import rmtree
import os
import requests
import json
import time

class backupScheduleLocal:


    @staticmethod
    def createBackup(virtualHost,writeToFile):
        try:

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Starting local backup for: "+virtualHost + "\n")

            finalData = json.dumps({'websiteToBeBacked': virtualHost})
            requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData)

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for backup to complete.. " + "\n")

            while (1):
                r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData)
                time.sleep(2)
                data = json.loads(r.text)

                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for backup to complete.. " + "\n")

                if data['backupStatus'] == 0:
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + "An error occurred, Error message: " + data['error_message'] + "\n")
                    break
                elif data['abort'] == 1:
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Backup Completed for: " + virtualHost + "\n")

                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " #############################################" + "\n")
                    break

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def prepare():
        try:
            backupLogPath = "/usr/local/lscp/logs/local_backup_log." + time.strftime("%I-%M-%S-%a-%b-%Y")

            writeToFile = open(backupLogPath, "a")

            writeToFile.writelines("#################################################\n")
            writeToFile.writelines("      Backup log for: " + time.strftime("%I-%M-%S-%a-%b-%Y") + "\n")
            writeToFile.writelines("#################################################\n")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

            for virtualHost in os.listdir("/home"):
                backupScheduleLocal.createBackup(virtualHost,writeToFile)

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " #############################################" + "\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Local Backup Completed" + "\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " #############################################" + "\n")

            writeToFile.close()

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")


backupScheduleLocal.prepare()