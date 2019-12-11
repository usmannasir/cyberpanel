#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .policyConstraint import policyConstraints
from emailPremium.models import DomainLimits, EmailLogs
from mailServer.models import Domains, EUsers
import time
from .cacheManager import cacheManager

limitThreads = multi.BoundedSemaphore(10)

class HandleRequest(multi.Thread):
    cleaningPath = '/home/cyberpanel/purgeCache'
    def __init__(self, conn):
        multi.Thread.__init__(self)
        self.connection = conn

    def __del__(self):
        try:
            self.connection.close()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [HandleRequest.__del__]')

    def run(self):
        limitThreads.acquire()
        dataComplete = ""

        try:
            while True:

                Data = self.connection.recv(64)
                # Wait for a connection

                try:
                    if os.path.exists(HandleRequest.cleaningPath):

                        readFromFile = open(HandleRequest.cleaningPath, 'r')
                        command = readFromFile.read()

                        cacheManager.handlePurgeRequest(command)

                        readFromFile.close()

                        os.remove(HandleRequest.cleaningPath)
                        cacheManager.flushCache()
                except:
                    pass

                if Data:
                    if len(Data) < 64:
                        dataComplete = dataComplete + Data
                        self.manageRequest(dataComplete)
                        dataComplete = ''
                    else:
                        dataComplete = dataComplete + Data
                else:
                    self.connection.close()
                    break

        except BaseException as msg:
            logging.writeToFile( str(msg) + ' [HandleRequest.run]')
        finally:
            limitThreads.release()

    def manageRequest(self, completeData):
        try:
            completeData = completeData.split('\n')
            for items in completeData:
                tempData = items.split('=')
                if tempData[0] == 'sasl_username':
                    if len(tempData[1]) == 0:
                        self.connection.sendall('action=dunno\n\n')
                        return
                    emailAddress = tempData[1]
                    domainName = emailAddress.split('@')[1]
                elif tempData[0] == 'recipient':
                    if len(tempData[1]) == 0:
                        self.connection.sendall('action=dunno\n\n')
                        return
                    destination = tempData[1]



            if domainName in cacheManager.domains:
                domainObj = cacheManager.domains[domainName]
                emailObj = domainObj.findEmailOBJ(emailAddress)
            else:
                try:
                    domain = Domains.objects.get(domain=domainName)
                    domainLTS = DomainLimits.objects.get(domain=domain)

                    newDomain = policyConstraints(domainName, domainLTS.monthlyLimit, domainLTS.monthlyUsed, domainLTS.limitStatus)
                    cacheManager.domains[domainName] = newDomain
                    domainObj = newDomain

                    emailObj = newDomain.findEmailOBJ(emailAddress)
                except:
                    self.connection.sendall('action=dunno\n\n')
                    return

            #logging.writeToFile('Domain Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Monthly Limit: ' + str(emailObj.monthlyLimits))
            #logging.writeToFile('Email Monthly Used: ' + str(emailObj.monthlyUsed))

            if domainObj.limitStatus == 1 and emailObj.limitStatus == 1:

                if domainObj.monthlyLimits <= domainObj.monthlyUsed or emailObj.monthlyLimits <= emailObj.monthlyUsed or emailObj.hourlyLimits <= emailObj.hourlyUsed:
                    logging.writeToFile(emailAddress + ' either exceeded monthly or hourly sending limit.')
                    self.connection.sendall('action=defer_if_permit Service temporarily unavailable\n\n')
                    return
                else:
                    email = EUsers.objects.get(email=emailAddress)
                    if emailObj.logStatus == 1:
                        logEntry = EmailLogs(email=email, destination=destination, timeStamp=time.strftime("%m.%d.%Y_%H-%M-%S"))
                        logEntry.save()
                    emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                    emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                    domainObj.monthlyUsed = domainObj.monthlyUsed + 1
                    self.connection.sendall('action=dunno\n\n')
            else:
                email = EUsers.objects.get(email=emailAddress)
                if emailObj.logStatus == 1:
                    logEntry = EmailLogs(email=email, destination=destination,
                                         timeStamp=time.strftime("%m.%d.%Y_%H-%M-%S"))
                    logEntry.save()

                emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                domainObj.monthlyUsed = domainObj.monthlyUsed + 1
                self.connection.sendall('action=dunno\n\n')


        except BaseException as msg:
            logging.writeToFile(str(msg) + " [HandleRequest.manageRequest]")
            self.connection.sendall('action=defer_if_permit Service temporarily unavailable\n\n')
