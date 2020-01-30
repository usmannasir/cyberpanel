import subprocess
import time
import socket
import os
import smtplib

class CyberCPLogFileWriter:
    fileName = "/home/cyberpanel/error-logs.txt"

    @staticmethod
    def SendEmail(sender, receivers, message):
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            print("Successfully sent email")
        except BaseException as msg:
            CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def writeToFile(message, email=None):
        try:
            file = open(CyberCPLogFileWriter.fileName,'a')
            file.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "] "+ message + "\n")
            file.close()

            ## Send Email

            emailPath = '/usr/local/CyberCP/emailDebug'

            try:
                if os.path.exists(emailPath):
                    SUBJECT = "CyberPanel log reporting"
                    adminEmailPath = '/home/cyberpanel/adminEmail'
                    adminEmail = open(adminEmailPath, 'r').read().rstrip('\n')
                    sender = 'root@%s' % (socket.gethostname())
                    TO = [adminEmail]
                    message = """\
From: %s
To: %s
Subject: %s

%s
""" % (
                    sender, ", ".join(TO), SUBJECT, '[%s] %s. \n' % (time.strftime("%m.%d.%Y_%H-%M-%S"), message))

                    if email == None or email == 1:
                        CyberCPLogFileWriter.SendEmail(sender, TO, message)
            except BaseException as msg:
                file = open(CyberCPLogFileWriter.fileName, 'a')
                file.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "] " + str(msg) + "\n")
                file.close()

        except BaseException as msg:
            return "Can not write to error file."

    @staticmethod
    def writeforCLI(message, level, method):
        try:
            file = open(CyberCPLogFileWriter.fileName, 'a')
            file.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + "] [" + level + ":" + method + "] " + message + "\n")
            file.close()
            file.close()
        except BaseException:
            return "Can not write to error file!"

    @staticmethod
    def readLastNFiles(numberOfLines,fileName):
        try:

            lastFewLines = str(subprocess.check_output(["tail", "-n",str(numberOfLines),fileName]).decode("utf-8"))

            return lastFewLines

        except subprocess.CalledProcessError as msg:
            return "File was empty"

    @staticmethod
    def statusWriter(tempStatusPath, mesg, append = None):
        try:
            if append == None:
                statusFile = open(tempStatusPath, 'w')
            else:
                statusFile = open(tempStatusPath, 'a')
            statusFile.writelines(mesg + '\n')
            statusFile.close()
            print((mesg + '\n'))
        except BaseException as msg:
            CyberCPLogFileWriter.writeToFile(str(msg) + ' [statusWriter]')
            #print str(msg)