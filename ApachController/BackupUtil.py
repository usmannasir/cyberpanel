import smtplib
import time
import argparse
import subprocess, shlex
import os

class BackupUtil:

    @staticmethod
    def normalExecutioner(command):
        try:
            res = subprocess.call(shlex.split(command))
            if res == 0:
                return 1
            else:
                return 0
        except BaseException as msg:
            return 0

    @staticmethod
    def SendEmail(message):
        sender = 'info@designti01.cyberhosting.org'
        receivers = ['jeanftellier@gmail.com', 'jeanftellier@gmail.com']

        try:
            smtpObj = smtplib.SMTP('127.0.0.1')
            smtpObj.sendmail(sender, receivers, message)
            print("Successfully sent email")
        except BaseException as msg:
            print("Error: unable to send email %s" % str(msg))

    @staticmethod
    def SyncHome():
        command = 'rsync -avz /home /mnt/HC_Volume_2760413'
        BackupUtil.normalExecutioner(command)
        message = "/home successfully synced on %s" % (time.strftime("%I-%M-%S-%a-%b-%Y"))
        BackupUtil.SendEmail(message)

    @staticmethod
    def BackupDBS():
        command = "/usr/local/CyberCP/ApachController/backup.sh"
        BackupUtil.normalExecutioner(command)

        message = "Database backups successfully generated on %s" % (time.strftime("%I-%M-%S-%a-%b-%Y"))
        BackupUtil.SendEmail(message)

    @staticmethod
    def MoveAllBackups():

        for virtualHost in os.listdir("/home"):
            completePath = "/home/%s/backup/" % (virtualHost)
            command = "mv %s %s" % (completePath + '*.tar.gz', '/home/backup/')
            subprocess.call(command, shell=True)




def main():

    parser = argparse.ArgumentParser(description='CyberPanel Backup tool.')
    parser.add_argument('function', help='Specific a function to call!')
    args = parser.parse_args()

    if args.function == "home":
        BackupUtil.SyncHome()
    elif args.function == "db":
        BackupUtil.BackupDBS()
    elif args.function == "sync":
        BackupUtil.MoveAllBackups()


if __name__ == "__main__":
    main()