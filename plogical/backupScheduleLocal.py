import CyberCPLogFileWriter as logging
import os
import time
from backupSchedule import backupSchedule

class backupScheduleLocal:

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
                backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

            backupSchedule.remoteBackupLogging(backupLogPath, "Local backup job completed.\n")

            writeToFile.close()

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

def main():
    backupScheduleLocal.prepare()


if __name__ == "__main__":
    main()