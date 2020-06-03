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
from websiteFunctions.models import BackupJob

class backupScheduleLocal:
    localBackupPath = '/home/cyberpanel/localBackupPath'
    runningPath = '/home/cyberpanel/localBackupPID'
    now = datetime.now()

    @staticmethod
    def prepare():
        try:

            if os.path.exists(backupScheduleLocal.runningPath):
                output = ProcessUtilities.outputExecutioner('ps aux')
                pid = open(backupScheduleLocal.runningPath, 'r').read()

                if output.find('/usr/local/CyberCP/plogical/backupScheduleLocal.py') > -1 and output.find(pid) > -1:
                    print('\n\nLocal backup is already running with PID: %s. If you want to run again kindly kill the backup process: \n\n kill -9 %s.\n\n' % (pid, pid))
                    return 0
                else:
                    os.remove(backupScheduleLocal.runningPath)

            writeToFile = open(backupScheduleLocal.runningPath, 'w')
            writeToFile.write(str(os.getpid()))
            writeToFile.close()

            backupRunTime = time.strftime("%m.%d.%Y_%H-%M-%S")
            backupLogPath = "/usr/local/lscp/logs/local_backup_log." + backupRunTime

            jobSuccessSites = 0
            jobFailedSites = 0

            backupSchedule.backupLog = BackupJob(logFile=backupLogPath, location=backupSchedule.LOCAL, jobSuccessSites=jobSuccessSites, jobFailedSites=jobFailedSites)
            backupSchedule.backupLog.save()

            writeToFile = open(backupLogPath, "a")

            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")
            backupSchedule.remoteBackupLogging(backupLogPath,"      Local Backup log for: " + backupRunTime)
            backupSchedule.remoteBackupLogging(backupLogPath, "#################################################\n")

            backupSchedule.remoteBackupLogging(backupLogPath, "")
            backupSchedule.remoteBackupLogging(backupLogPath, "")

            for virtualHost in os.listdir("/home"):
                if match(r'^[a-zA-Z0-9-]*[a-zA-Z0-9-]{0,61}[a-zA-Z0-9-](?:\.[a-zA-Z0-9-]{2,})+$', virtualHost, M | I):
                    try:
                        retValues = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                        if retValues[0] == 0:
                            backupSchedule.remoteBackupLogging(backupLogPath, '[ERROR] Backup failed for %s, error: %s moving on..' % (virtualHost, retValues[1]), backupSchedule.ERROR)
                            jobFailedSites = jobFailedSites + 1
                            continue

                        if os.path.exists(backupScheduleLocal.localBackupPath):
                            backupPath = retValues[1] + ".tar.gz"
                            localBackupPath = '%s/%s' % (open(backupScheduleLocal.localBackupPath, 'r').read().rstrip('/'), backupRunTime)

                            command = 'mkdir -p %s' % (localBackupPath)
                            ProcessUtilities.normalExecutioner(command)

                            command = 'mv %s %s' % (backupPath, localBackupPath)
                            ProcessUtilities.normalExecutioner(command)

                        jobSuccessSites = jobSuccessSites + 1
                    except BaseException as msg:

                        jobFailedSites = jobFailedSites + 1

                        backupSchedule.remoteBackupLogging(backupLogPath,
                                                           '[ERROR] Backup failed for %s, error: %s moving on..' % (virtualHost, str(msg)), backupSchedule.ERROR)

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

                backupSchedule.remoteBackupLogging(backupLogPath, "#################################################")

                backupSchedule.remoteBackupLogging(backupLogPath, "")
                backupSchedule.remoteBackupLogging(backupLogPath, "")

            backupSchedule.remoteBackupLogging(backupLogPath, "Local backup job completed.\n")

            writeToFile.close()

            job = BackupJob.objects.get(logFile=backupLogPath)
            job.jobFailedSites = jobFailedSites
            job.jobSuccessSites = jobSuccessSites
            job.save()

            if os.path.exists(backupScheduleLocal.runningPath):
                os.remove(backupScheduleLocal.runningPath)

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