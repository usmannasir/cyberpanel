#!/usr/local/CyberCP/bin/python

import os
import time
import csv
import re
import plogical.CyberCPLogFileWriter as logging
from .models import EmailLists, EmailsInList, EmailTemplate, EmailJobs, SMTPHosts, ValidationLog
from plogical.backupSchedule import backupSchedule
from websiteFunctions.models import Websites
import threading as multi
import socket, smtplib
import DNS
from random import randint
from plogical.processUtilities import ProcessUtilities

class emailMarketing(multi.Thread):
    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'createEmailList':
                self.createEmailList()
            elif self.function == 'verificationJob':
                self.verificationJob()
            elif self.function == 'startEmailJob':
                self.startEmailJob()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [emailMarketing.run]')

    def createEmailList(self):
        try:
            website = Websites.objects.get(domain=self.extraArgs['domain'])
            try:
                newList = EmailLists(owner=website, listName=self.extraArgs['listName'], dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                newList.save()
            except:
                newList = EmailLists.objects.get(listName=self.extraArgs['listName'])

            counter = 0

            if self.extraArgs['path'].endswith('.csv'):
                with open(self.extraArgs['path'], 'r') as emailsList:
                    data = csv.reader(emailsList, delimiter=',')
                    for items in data:
                        try:
                            for value in items:
                                if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', value) != None:
                                    try:
                                        getEmail = EmailsInList.objects.get(owner=newList, email=value)
                                    except:
                                        try:
                                            newEmail = EmailsInList(owner=newList, email=value,
                                                                    verificationStatus='NOT CHECKED',
                                                                    dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                                            newEmail.save()
                                        except:
                                            pass
                                    logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(counter) + ' emails read.')
                                    counter = counter + 1
                        except BaseException as msg:
                            logging.CyberCPLogFileWriter.writeToFile('%s. [createEmailList]' % (str(msg)))
                            continue
            elif self.extraArgs['path'].endswith('.txt'):
                with open(self.extraArgs['path'], 'r') as emailsList:
                    emails = emailsList.readline()
                    while emails:
                        email = emails.strip('\n')
                        if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email) != None:
                            try:
                                getEmail = EmailsInList.objects.get(owner=newList, email=email)
                            except BaseException as msg:
                                newEmail = EmailsInList(owner=newList, email=email, verificationStatus='NOT CHECKED',
                                                        dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                                newEmail.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],str(counter) + ' emails read.')
                            counter = counter + 1
                        emails = emailsList.readline()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(counter) + 'Successfully read all emails. [200]')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(msg) +'. [404]')
            return 0

    def findNextIP(self):
        try:
            if self.delayData['rotation'] == 'Disable':
                return None
            elif self.delayData['rotation'] == 'IPv4':
                if self.delayData['ipv4'].find(',') == -1:
                    return self.delayData['ipv4']
                else:
                    ipv4s = self.delayData['ipv4'].split(',')

                    if self.currentIP == '':
                        return ipv4s[0]
                    else:
                        returnCheck = 0

                        for items in ipv4s:
                            if returnCheck == 1:
                                return items
                            if items == self.currentIP:
                                returnCheck = 1

                        return ipv4s[0]
            else:
                if self.delayData['ipv6'].find(',') == -1:
                    return self.delayData['ipv6']
                else:
                    ipv6 = self.delayData['ipv6'].split(',')

                    if self.currentIP == '':
                        return ipv6[0]
                    else:
                        returnCheck = 0

                        for items in ipv6:
                            if returnCheck == 1:
                                return items
                            if items == self.currentIP:
                                returnCheck = 1
                    return ipv6[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return None

    def verificationJob(self):
        try:

            verificationList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            domain = verificationList.owner.domain

            if not os.path.exists('/home/cyberpanel/' + domain):
                os.mkdir('/home/cyberpanel/' + domain)

            tempStatusPath = '/home/cyberpanel/' + domain + "/" + self.extraArgs['listName']
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Starting verification job..')

            counter = 1
            counterGlobal = 0

            allEmailsInList = verificationList.emailsinlist_set.all()

            configureVerifyPath = '/home/cyberpanel/configureVerify'
            finalPath = '%s/%s' % (configureVerifyPath, domain)


            import json
            if os.path.exists(finalPath):
                self.delayData = json.loads(open(finalPath, 'r').read())

            self.currentIP = ''

            ValidationLog(owner=verificationList, status=backupSchedule.INFO, message='Starting email verification..').save()

            for items in allEmailsInList:
                if items.verificationStatus != 'Verified':
                    try:

                        email = items.email
                        self.currentEmail = email
                        domainName = email.split('@')[1]
                        records = DNS.dnslookup(domainName, 'MX', 15)

                        counterGlobal = counterGlobal + 1

                        for mxRecord in records:

                            # Get local server hostname
                            host = socket.gethostname()

                            ## Only fetching smtp object

                            if os.path.exists(finalPath):
                                try:
                                    delay = self.delayData['delay']
                                    if delay == 'Enable':
                                        if counterGlobal == int(self.delayData['delayAfter']):
                                            ValidationLog(owner=verificationList, status=backupSchedule.INFO,
                                                          message='Sleeping for %s seconds...' % (self.delayData['delayTime'])).save()

                                            time.sleep(int(self.delayData['delayTime']))
                                            counterGlobal = 0
                                            self.currentIP = self.findNextIP()

                                            ValidationLog(owner=verificationList, status=backupSchedule.INFO,
                                                          message='IP being used for validation until next sleep: %s.' % (str(self.currentIP))).save()

                                            if self.currentIP == None:
                                                server = smtplib.SMTP(timeout=10)
                                            else:
                                                server = smtplib.SMTP(self.currentIP, timeout=10)
                                        else:

                                            if self.currentIP == '':
                                                self.currentIP = self.findNextIP()
                                                ValidationLog(owner=verificationList, status=backupSchedule.INFO,
                                                              message='IP being used for validation until next sleep: %s.' % (
                                                                  str(self.currentIP))).save()

                                            if self.currentIP == None:
                                                server = smtplib.SMTP(timeout=10)
                                            else:
                                                server = smtplib.SMTP(self.currentIP, timeout=10)
                                    else:
                                        logging.CyberCPLogFileWriter.writeToFile(
                                            'Delay not configured..')

                                        ValidationLog(owner=verificationList, status=backupSchedule.INFO,
                                                      message='Delay not configured..').save()

                                        server = smtplib.SMTP(timeout=10)
                                except BaseException as msg:

                                    ValidationLog(owner=verificationList, status=backupSchedule.ERROR,
                                                  message='Delay not configured. Error message: %s' % (str(msg))).save()

                                    server = smtplib.SMTP(timeout=10)
                            else:
                                server = smtplib.SMTP(timeout=10)

                            ###

                            server.set_debuglevel(0)

                            # SMTP Conversation
                            server.connect(mxRecord[1])
                            server.helo(host)
                            server.mail('host' + "@" + host)
                            code, message = server.rcpt(str(email))
                            server.quit()

                            # Assume 250 as Success
                            if code == 250:
                                items.verificationStatus = 'Verified'
                                items.save()
                                break
                            else:
                                ValidationLog(owner=verificationList, status=backupSchedule.ERROR,
                                              message='Failed to verify %s. Error message %s' % (email, message.decode())).save()
                                items.verificationStatus = 'Verification Failed'
                                items.save()

                        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(counter) + ' emails verified so far..')
                        counter = counter + 1
                    except BaseException as msg:
                        items.verificationStatus = 'Verification Failed'
                        items.save()
                        counter = counter + 1
                        ValidationLog(owner=verificationList, status=backupSchedule.ERROR,
                                      message='Failed to verify %s. Error message %s' % (
                                      self.currentEmail , str(msg))).save()


                verificationList.notVerified = verificationList.emailsinlist_set.filter(verificationStatus='Verification Failed').count()
                verificationList.verified = verificationList.emailsinlist_set.filter(verificationStatus='Verified').count()
                verificationList.save()

            ValidationLog(owner=verificationList, status=backupSchedule.ERROR, message=str(counter) + ' emails successfully verified. [200]').save()

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(counter) + ' emails successfully verified. [200]')
        except BaseException as msg:
            verificationList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            domain = verificationList.owner.domain
            tempStatusPath = '/home/cyberpanel/' + domain + "/" + self.extraArgs['listName']
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) +'. [404]')
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    def setupSMTPConnection(self):
        try:
            if self.extraArgs['host'] == 'localhost':
                self.smtpServer = smtplib.SMTP('127.0.0.1')
                return 1
            else:
                self.verifyHost = SMTPHosts.objects.get(host=self.extraArgs['host'])
                self.smtpServer = smtplib.SMTP(str(self.verifyHost.host), int(self.verifyHost.port))

                if int(self.verifyHost.port) == 587:
                    self.smtpServer.starttls()

                self.smtpServer.login(str(self.verifyHost.userName), str(self.verifyHost.password))
                return 1
        except smtplib.SMTPHeloError:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'The server didnt reply properly to the HELO greeting.')
            return 0
        except smtplib.SMTPAuthenticationError:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Username and password combination not accepted.')
            return 0
        except smtplib.SMTPException:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'No suitable authentication method was found.')
            return 0

    def startEmailJob(self):
        try:

            if self.setupSMTPConnection() == 0:
                logging.CyberCPLogFileWriter.writeToFile('SMTP Connection failed. [301]')
                return 0

            emailList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            allEmails = emailList.emailsinlist_set.all()
            emailMessage = EmailTemplate.objects.get(name=self.extraArgs['selectedTemplate'])

            totalEmails = allEmails.count()
            sent = 0
            failed = 0

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            ## Compose Message
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            import re

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            emailJob = EmailJobs(owner=emailMessage, date=time.strftime("%I-%M-%S-%a-%b-%Y"),
                                 host=self.extraArgs['host'], totalEmails=totalEmails,
                                 sent=sent, failed=failed
                                 )
            emailJob.save()

            for items in allEmails:
                try:
                    message = MIMEMultipart('alternative')
                    message['Subject'] = emailMessage.subject
                    message['From'] = emailMessage.fromEmail
                    message['reply-to'] = emailMessage.replyTo

                    if (items.verificationStatus == 'Verified' or self.extraArgs[
                        'verificationCheck']) and not items.verificationStatus == 'REMOVED':
                        try:
                            port = ProcessUtilities.fetchCurrentPort()
                            removalLink = "https:\/\/" + ipAddress + ":%s\/emailMarketing\/remove\/" % (port) + self.extraArgs[
                                'listName'] + "\/" + items.email
                            messageText = emailMessage.emailMessage.encode('utf-8', 'replace')
                            message['To'] = items.email

                            if re.search(b'<html', messageText, re.IGNORECASE) and re.search(b'<body', messageText,
                                                                                             re.IGNORECASE):
                                finalMessage = messageText.decode()

                                self.extraArgs['unsubscribeCheck'] = 0
                                if self.extraArgs['unsubscribeCheck']:
                                    messageFile = open(tempPath, 'w')
                                    messageFile.write(finalMessage)
                                    messageFile.close()

                                    command = "sudo sed -i 's/{{ unsubscribeCheck }}/" + removalLink + "/g' " + tempPath
                                    ProcessUtilities.executioner(command, 'cyberpanel')

                                    messageFile = open(tempPath, 'r')
                                    finalMessage = messageFile.read()
                                    messageFile.close()

                                html = MIMEText(finalMessage, 'html')
                                message.attach(html)

                            else:
                                finalMessage = messageText

                                if self.extraArgs['unsubscribeCheck']:
                                    finalMessage = finalMessage.replace('{{ unsubscribeCheck }}', removalLink)

                                html = MIMEText(finalMessage, 'plain')
                                message.attach(html)

                            try:
                                status = self.smtpServer.noop()[0]
                                self.smtpServer.sendmail(message['From'], items.email, message.as_string())
                            except:  # smtplib.SMTPServerDisconnected
                                if self.setupSMTPConnection() == 0:
                                    logging.CyberCPLogFileWriter.writeToFile('SMTP Connection failed. [301]')
                                    return 0
                                self.smtpServer.sendmail(message['From'], items.email, message.as_string())


                            sent = sent + 1
                            emailJob.sent = sent
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ' Failed: ' + str(
                                                                          failed))
                        except BaseException as msg:
                            failed = failed + 1
                            emailJob.failed = failed
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ', Failed: ' + str(failed))
                            if self.setupSMTPConnection() == 0:
                                logging.CyberCPLogFileWriter.writeToFile(
                                    'SMTP Connection failed. Error: %s. [392]' % (str(msg)))
                                return 0
                except BaseException as msg:
                            failed = failed + 1
                            emailJob.failed = failed
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ', Failed: ' + str(failed))
                            if self.setupSMTPConnection() == 0:
                                logging.CyberCPLogFileWriter.writeToFile('SMTP Connection failed. Error: %s. [399]' % (str(msg)))
                                return 0


            emailJob.sent = sent
            emailJob.failed = failed
            emailJob.save()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Email job completed. [200]')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(msg) + '. [404]')
            return 0