import CyberCPLogFileWriter as logging
import os
import time
from backupSchedule import backupSchedule
from plogical.processUtilities import ProcessUtilities
from re import match,I,M

class backupScheduleLocal:
    localBackupPath = '/home/cyberpanel/localBackupPath'

    @staticmethod
    def prepare():
        try:
            backupLogPath = "/usr/local/lscp/logs/local_backup_log." + time.strftime("%I-%M-%S-%a-%b-%Y")

            writeToFile = open(backupLogPath, "a")

            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Local Backup log for: " + time.strftime("%I-%M-%S-%a-%b-%Y"))
            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################\n")

            backupSchedule.remoteBackupLogging(backupLogPath, "")
            backupSchedule.remoteBackupLogging(backupLogPath, "")

            for virtualHost in os.listdir("/home"):
                if match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', virtualHost, M | I):
                    retValues = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                    if os.path.exists(backupScheduleLocal.localBackupPath):
                        backupPath = retValues[1] + ".tar.gz"
                        localBackupPath = '%s/%s' % (open(backupScheduleLocal.localBackupPath, 'r').read().rstrip('/'), time.strftime("%b-%d-%Y"))

                        command = 'mkdir -p %s' % (localBackupPath)
                        ProcessUtilities.normalExecutioner(command)

                        command = 'mv %s %s' % (backupPath, localBackupPath)
                        ProcessUtilities.normalExecutioner(command)



                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

            backupSchedule.remoteBackupLogging(backupLogPath, "Local backup job completed.\n")

            writeToFile.close()

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [214:startBackup]")

def main():
    backupScheduleLocal.prepare()


if __name__ == "__main__":
    main()