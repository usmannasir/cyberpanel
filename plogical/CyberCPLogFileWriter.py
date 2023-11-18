import subprocess
import time
import socket
import os
import smtplib

class CyberCPLogFileWriter:
    fileName = "/home/cyberpanel/error-logs.txt"

    @staticmethod
    def AddFromHeader(sender, message):
        try:
            import re

            if not re.search('^From: ', message, re.MULTILINE):
                message = 'From: {}\n{}'.format(sender, message)

            return message
        except BaseException as msg:
            CyberCPLogFileWriter.writeToFile(str(msg) + ' [AddFromHeader]')

    @staticmethod
    def SendEmail(sender, receivers, message, subject=None, type=None):
        try:
            smtpPath = '/home/cyberpanel/smtpDetails'

            if os.path.exists(smtpPath):
                import json

                mailSettings = json.loads(open(smtpPath, 'r').read())
                smtpHost = mailSettings['smtpHost']
                smtpPort = mailSettings['smtpPort']
                smtpUserName = mailSettings['smtpUserName']
                smtpPassword = mailSettings['smtpPassword']

                smtpServer = smtplib.SMTP(str(smtpHost), int(smtpPort))
                smtpServer.login(smtpUserName, smtpPassword)

                ##

                if subject != None:
                    message = 'Subject: {}\n\n{}'.format(subject, message)

                message = CyberCPLogFileWriter.AddFromHeader(sender, message)
                smtpServer.sendmail(smtpUserName, receivers, message)
            else:
                smtpObj = smtplib.SMTP('localhost')

                message = CyberCPLogFileWriter.AddFromHeader(sender, message)
                smtpObj.sendmail(sender, receivers, message)
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
        except BaseException as msg:
            CyberCPLogFileWriter.writeToFile(str(msg) + ' [statusWriter]')
