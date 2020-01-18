#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
from plogical import CyberCPLogFileWriter as logging
import os
import time
from plogical.backupSchedule import backupSchedule
from plogical.processUtilities import ProcessUtilities
from re import match,I,M
import signal
from datetime import datetime

class backupScheduleLocal:
    localBackupPath = '/home/cyberpanel/localBackupPath'
    now = datetime.now()


    @staticmethod
    def prepare():
        try:
            backupRunTime = time.strftime("%m.%d.%Y_%H-%M-%S")
            backupLogPath = "/usr/local/lscp/logs/local_backup_log." + backupRunTime

            writeToFile = open(backupLogPath, "a")

            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Local Backup log for: " + backupRunTime)
            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################\n")

            backupSchedule.remoteBackupLogging(backupLogPath, "")
            backupSchedule.remoteBackupLogging(backupLogPath, "")

            for virtualHost in os.listdir("/home"):
                if match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', virtualHost, M | I):
                    try:
                        retValues = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                        if os.path.exists(backupScheduleLocal.localBackupPath):
                            backupPath = retValues[1] + ".tar.gz"
                            localBackupPath = '%s/%s' % (open(backupScheduleLocal.localBackupPath, 'r').read().rstrip('/'), backupRunTime)

                            command = 'mkdir -p %s' % (localBackupPath)
                            ProcessUtilities.normalExecutioner(command)

                            command = 'mv %s %s' % (backupPath, localBackupPath)
                            ProcessUtilities.normalExecutioner(command)
                    except BaseException as msg:
                        backupSchedule.remoteBackupLogging(backupLogPath,
                                                           '[ERROR] Backup failed for %s, error: %s moving on..' % (virtualHost, str(msg)))




                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

            backupSchedule.remoteBackupLogging(backupLogPath, "Local backup job completed.\n")

            writeToFile.close()

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [214:startBackup]")

def main():
    backupScheduleLocal.prepare()


def handler(signum, frame):
    diff = datetime.now() - backupScheduleLocal.now
    logging.CyberCPLogFileWriter.writeToFile('Signal: %s, time spent: %s' % (str(signum), str(diff.total_seconds())))

if __name__ == "__main__":
    for i in range(1,32):
        if i == 9 or i == 19 or i == 32:
            continue
        signal.signal(i, handler)
    main()