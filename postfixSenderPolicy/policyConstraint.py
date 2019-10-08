from emailPremium.models import DomainLimits, EmailLimits, EmailLogs
from mailServer.models import Domains, EUsers

class emailConstraints:
    def __init__(self, emailAddress, monthlyLimits, monthlyUsed, hourlyLimits, hourlyUsed, limitStatus, logStatus):
        self.emailAddress = emailAddress
        self.monthlyLimits = monthlyLimits
        self.monthlyUsed = monthlyUsed
        self.hourlyLimits = hourlyLimits
        self.hourlyUsed = hourlyUsed
        self.limitStatus = limitStatus
        self.logStatus = logStatus

class policyConstraints:
    def __init__(self, domain, monthlyLimits, monthlyUsed, limitStatus):
        self.domain = domain
        self.emails = {}
        self.monthlyLimits = monthlyLimits
        self.monthlyUsed = monthlyUsed
        self.limitStatus = limitStatus


    def findEmailOBJ(self, emailAddress):
        if emailAddress in self.emails:
            return self.emails[emailAddress]
        else:
            email = EUsers.objects.get(email=emailAddress)
            emailLTS = EmailLimits.objects.get(email=email)
            newEmail = emailConstraints(emailAddress, emailLTS.monthlyLimits, emailLTS.monthlyUsed, emailLTS.hourlyLimit,
                                        emailLTS.hourlyUsed, emailLTS.limitStatus, emailLTS.emailLogs)
            self.emails[emailAddress] = newEmail
            return newEmail