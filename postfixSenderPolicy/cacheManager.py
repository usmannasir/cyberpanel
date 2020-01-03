#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
sys.path.append('/usr/local/CyberCP')
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from emailPremium.models import EmailLimits, DomainLimits, Domains, EUsers

class cacheManager:
    domains = {}

    @staticmethod
    def flushCache():
        try:

            for domain, domainOBJ in cacheManager.domains.items():
                domaindb = Domains.objects.get(domain=domain)
                dbDomain = DomainLimits.objects.get(domain=domaindb)

                dbDomain.monthlyUsed = domainOBJ.monthlyUsed
                dbDomain.save()

                for email, emailOBJ in domainOBJ.emails.items():
                    emailID = EUsers.objects.get(email=email)
                    dbEmail = EmailLimits.objects.get(email=emailID)

                    dbEmail.monthlyUsed = emailOBJ.monthlyUsed
                    dbEmail.hourlyUsed = emailOBJ.hourlyUsed
                    dbEmail.save()

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.flushCache]')

    @staticmethod
    def disableEnableLogs(self, emailAddress, operationValue):
        try:
            domainName = emailAddress.split('@')[1]

            if domainName in cacheManager.domains:
                domainOBJ = cacheManager.domains[domainName]
                if emailAddress in domainOBJ.emails:
                    emailOBJ = domainOBJ.emails[emailAddress]
                    emailOBJ.logStatus = operationValue

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.disableEnableLogs]')

    @staticmethod
    def purgeLog(command):
        try:
            email = command[2]
            operationVal = int(command[3])
            domain = email.split('@')[1]

            if domain in cacheManager.domains:
                domainOBJ = cacheManager.domains[domain]
                emailOBJ = domainOBJ.emails[email]
                emailOBJ.logStatus = operationVal

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.purgeLog]')

    @staticmethod
    def purgeLimit(command):
        try:
            email = command[2]
            operationVal = int(command[3])
            domain = email.split('@')[1]

            if domain in cacheManager.domains:
                domainOBJ = cacheManager.domains[domain]
                emailOBJ = domainOBJ.emails[email]
                emailOBJ.limitStatus = operationVal

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.purgeLimit]')

    @staticmethod
    def purgeLimitDomain(command):
        try:
            domain = command[2]
            operationVal = int(command[3])

            if domain in cacheManager.domains:
                domainOBJ = cacheManager.domains[domain]
                domainOBJ.limitStatus = operationVal

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.purgeLimitDomain]')

    @staticmethod
    def updateDomainLimit(command):
        try:
            domain = command[2]
            newLimit = int(command[3])

            if domain in cacheManager.domains:
                domainOBJ = cacheManager.domains[domain]
                domainOBJ.monthlyLimits = newLimit

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.updateDomainLimit]')

    @staticmethod
    def purgeLimitEmail(command):
        try:
            email = command[2]
            monthlyLimit = int(command[3])
            hourlyLimit = int(command[4])
            domain = email.split('@')[1]

            if domain in cacheManager.domains:
                domainOBJ = cacheManager.domains[domain]
                emailOBJ = domainOBJ.emails[email]
                emailOBJ.monthlyLimits = monthlyLimit
                emailOBJ.hourlyLimits = hourlyLimit

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.purgeLimitEmail]')

    @staticmethod
    def hourlyCleanUP():
        try:
            for domain, domainOBJ in cacheManager.domains.items():
                for email, emailOBJ in domainOBJ.emails.items():

                    emailID = EUsers.objects.get(email=email)
                    dbEmail = EmailLimits.objects.get(email=emailID)

                    dbEmail.hourlyUsed = 0
                    dbEmail.save()

                    dbEmail.hourlyUsed = 0
                    emailOBJ.hourlyUsed = 0

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.hourlyCleanUP]')

    @staticmethod
    def monthlyCleanUP():
        try:

            for domain, domainOBJ in cacheManager.domains.items():
                domaindb = Domains.objects.get(domain=domain)
                dbDomain = DomainLimits.objects.get(domain=domaindb)


                for email, emailOBJ in domainOBJ.emails.items():
                    emailID = EUsers.objects.get(email=email)
                    dbEmail = EmailLimits.objects.get(email=emailID)

                    dbEmail.monthlyUsed = 0
                    emailOBJ.monthlyUsed = 0
                    dbEmail.hourlyUsed = 0
                    emailOBJ.hourlyUsed = 0
                    dbEmail.save()

                dbDomain.monthlyUsed = 0
                dbDomain.save()

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.monthlyCleanUP]')


    @staticmethod
    def cleanUP(*args):
        cacheManager.flushCache()
        logging.writeToFile('Email Cleanup Service')
        os._exit(0)

    @staticmethod
    def handlePurgeRequest(command):
        try:
            finalCommand = command.split(' ')

            if finalCommand[1] == 'purgeLog':
                cacheManager.purgeLog(finalCommand)
            elif finalCommand[1] == 'purgeLimit':
                cacheManager.purgeLimit(finalCommand)
            elif finalCommand[1] == 'purgeLimitDomain':
                cacheManager.purgeLimitDomain(finalCommand)
            elif finalCommand[1] == 'updateDomainLimit':
                cacheManager.updateDomainLimit(finalCommand)
            elif finalCommand[1] == 'purgeLimitEmail':
                cacheManager.purgeLimitEmail(finalCommand)
            elif finalCommand[1] == 'hourlyCleanup':
                cacheManager.hourlyCleanUP()
            elif finalCommand[1] == 'monthlyCleanup':
                cacheManager.monthlyCleanUP()


        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cacheManager.handlePurgeRequest]')

