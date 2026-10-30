#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
import socket
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .policyConstraint import policyConstraints
from emailPremium.models import DomainLimits, EmailLogs
from mailServer.models import Domains, EUsers
import time
from .cacheManager import cacheManager

limitThreads = multi.BoundedSemaphore(10)
# Cache lookups, limit checks and increments must be one transaction.
policyLock = multi.RLock()

class HandleRequest(multi.Thread):
    cleaningPath = '/home/cyberpanel/purgeCache'
    def __init__(self, conn):
        multi.Thread.__init__(self)
        self.connection = conn

    def __del__(self):
        try:
            self.connection.close()
        except Exception as msg:
            logging.writeToFile(str(msg) + ' [HandleRequest.__del__]')

    requestTimeout = 30
    maxRequestBytes = 64 * 1024

    def run(self):
        limitThreads.acquire()
        dataComplete = b""
        try:
            self.connection.settimeout(self.requestTimeout)
            while True:
                data = self.connection.recv(4096)
                if not data:
                    break
                dataComplete += data
                # Stream read boundaries have no relationship to request boundaries.
                while b"\n\n" in dataComplete:
                    request, dataComplete = dataComplete.split(b"\n\n", 1)
                    if len(request) > self.maxRequestBytes:
                        raise ValueError("Policy request exceeds size limit")
                    with policyLock:
                        self._purgeCache()
                        self.manageRequest(request.decode('utf-8'))
                if len(dataComplete) > self.maxRequestBytes:
                    raise ValueError("Policy request exceeds size limit")
        except Exception as msg:
            logging.writeToFile(str(msg) + ' [HandleRequest.run]')
            # Do not send an unsolicited reply on an idle persistent connection.
            if not isinstance(msg, socket.timeout) or dataComplete:
                try:
                    self.connection.sendall(b'action=defer_if_permit Service temporarily unavailable\n\n')
                except OSError:
                    pass
        finally:
            self.connection.close()
            limitThreads.release()

    @staticmethod
    def _purgeCache():
        try:
            if os.path.exists(HandleRequest.cleaningPath):
                with open(HandleRequest.cleaningPath, 'r') as source:
                    cacheManager.handlePurgeRequest(source.read())
                os.remove(HandleRequest.cleaningPath)
                cacheManager.flushCache()
        except Exception as msg:
            logging.writeToFile(str(msg) + ' [HandleRequest._purgeCache]')

    def manageRequest(self, completeData):
        try:
            attributes = {}
            for line in completeData.split('\n'):
                if not line or '=' not in line or '\x00' in line:
                    raise ValueError("Malformed policy request")
                key, value = line.split('=', 1)
                attributes[key] = value
            if attributes.get('request') != 'smtpd_access_policy':
                raise ValueError("Unsupported policy request")
            emailAddress = attributes.get('sasl_username', '')
            if not emailAddress:
                self.connection.sendall(b'action=dunno\n\n')
                return
            if '@' not in emailAddress:
                raise ValueError("Invalid authenticated email address")
            domainName = emailAddress.rsplit('@', 1)[1]
            # Postfix omits recipient at DATA when there are multiple recipients.
            # Sending limits still apply; there is no individual destination to log.
            destination = attributes.get('recipient', '')

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
                except (Domains.DoesNotExist, DomainLimits.DoesNotExist):
                    self.connection.sendall(b'action=dunno\n\n')
                    return

            #logging.writeToFile('Domain Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Limit Status: ' + str(domainObj.limitStatus))
            #logging.writeToFile('Email Monthly Limit: ' + str(emailObj.monthlyLimits))
            #logging.writeToFile('Email Monthly Used: ' + str(emailObj.monthlyUsed))

            if domainObj.limitStatus == 1 and emailObj.limitStatus == 1:

                if domainObj.monthlyLimits <= domainObj.monthlyUsed or emailObj.monthlyLimits <= emailObj.monthlyUsed or emailObj.hourlyLimits <= emailObj.hourlyUsed:
                    logging.writeToFile(emailAddress + ' either exceeded monthly or hourly sending limit.')
                    self.connection.sendall(b'action=defer_if_permit Service temporarily unavailable\n\n')
                    return
                else:
                    email = EUsers.objects.get(email=emailAddress)
                    if emailObj.logStatus == 1:
                        logEntry = EmailLogs(email=email, destination=destination, timeStamp=time.strftime("%m.%d.%Y_%H-%M-%S"))
                        logEntry.save()
                    emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                    emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                    domainObj.monthlyUsed = domainObj.monthlyUsed + 1
                    self.connection.sendall(b'action=dunno\n\n')
            else:
                email = EUsers.objects.get(email=emailAddress)
                if emailObj.logStatus == 1:
                    logEntry = EmailLogs(email=email, destination=destination,
                                         timeStamp=time.strftime("%m.%d.%Y_%H-%M-%S"))
                    logEntry.save()

                emailObj.monthlyUsed = emailObj.monthlyUsed + 1
                emailObj.hourlyUsed = emailObj.hourlyUsed + 1
                domainObj.monthlyUsed = domainObj.monthlyUsed + 1
                self.connection.sendall(b'action=dunno\n\n')


        except Exception as msg:
            logging.writeToFile(str(msg) + " [HandleRequest.manageRequest]")
            self.connection.sendall(b'action=defer_if_permit Service temporarily unavailable\n\n')
