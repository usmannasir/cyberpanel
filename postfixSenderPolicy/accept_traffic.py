#!/usr/bin/env python2.7
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from policyConstraint import policyConstraints
from emailPremium.models import DomainLimits, EmailLimits, EmailLogs
from mailServer.models import Domains, EUsers
import time
from cacheManager import cacheManager

limitThreads = multi.BoundedSemaphore(10)

class HandleRequest(multi.Thread):
    def __init__(self, conn):
        multi.Thread.__init__(self)
        self.connection = conn

    def run(self):
        limitThreads.acquire()
        dataComplete = ""
        try:
            try:

                while True:
                    Data = self.connection.recv(64)
                    if Data:
                        if len(Data) < 64:
                            dataComplete = dataComplete + Data

                            if dataComplete.find('cyberpanelCleaner') > -1:
                                logging.writeToFile(dataComplete)
                                cacheManager.handlePurgeRequest(dataComplete)
                            else:
                                self.manageRequest(dataComplete)

                            dataComplete = ''
                        else:
                            dataComplete = dataComplete + Data
                    else:
                        self.connection.close()
            finally:
            # Clean up the connection
                self.connection.close()

        finally:
            limitThreads.release()

    def manageRequest(self, completeData):
        try:
            completeData = completeData.split('\n')

            for items in completeData:
                tempData = items.split('=')
                if tempData[0] == 'client_name':
                    domainName = tempData[1]
                elif tempData[0] == 'sender':
                    emailAddress = tempData[1]
                elif tempData[0] == 'recipient':
                    destination = tempData[1]

            if domainName in cacheManager.domains:
                domainObj = cacheManager.domains[domainName]
                emailObj = domainObj.findEmailOBJ(emailAddress)
            else:
                domain = Domains.objects.get(domain=domainName)
                domainLTS = DomainLimits.objects.get(domain=domain)

                newDomain = policyConstraints(domainName, domainLTS.monthlyLimit, domainLTS.monthlyUsed, domainLTS.limitStatus)
                cacheManager.domains[domainName] = newDomain
                domainObj = newDomain

                emailObj = newDomain.findEmailOBJ(emailAddress)

            #logging.writeToFile('Domain Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Monthly Limit: ' + str(emailObj.monthlyLimits))
            #logging.writeToFile('Email Monthly Used: ' + str(emailObj.monthlyUsed))

            if domainObj.limitStatus == 1 and emailObj.limitStatus == 1:
                if emailObj.monthlyLimits < emailObj.monthlyUsed or emailObj.hourlyLimits < emailObj.hourlyUsed:
                    logging.writeToFile(emailAddress + ' either exceeded monthly or hourly sending limit.')
                    self.connection.sendall('action=defer_if_permit Service temporarily unavailable\n\n')
                else:
                    email = EUsers.objects.get(email=emailAddress)
                    if emailObj.logStatus == 1:
                        logEntry = EmailLogs(email=email, destination=destination, timeStamp=time.strftime("%I-%M-%S-%a-%b-%Y"))
                        logEntry.save()
                    emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                    emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                    self.connection.sendall('action=dunno\n\n')
            else:
                email = EUsers.objects.get(email=emailAddress)
                if emailObj.logStatus == 1:
                    logEntry = EmailLogs(email=email, destination=destination,
                                         timeStamp=time.strftime("%I-%M-%S-%a-%b-%Y"))
                    logEntry.save()
                emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                self.connection.sendall('action=dunno\n\n')


        except BaseException, msg:
            self.connection.sendall('action=dunno\n\n')
            logging.writeToFile(str(msg))
