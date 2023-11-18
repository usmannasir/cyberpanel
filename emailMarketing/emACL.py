from .models import EmailMarketing, EmailTemplate, SMTPHosts, EmailLists, EmailJobs
from websiteFunctions.models import Websites

class emACL:

    @staticmethod
    def checkIfEMEnabled(userName):
        try:
            user = EmailMarketing.objects.get(userName=userName)
            return 0
        except:
            return 1

    @staticmethod
    def getEmailsLists(domain):
        website = Websites.objects.get(domain=domain)
        emailLists = website.emaillists_set.all()
        listNames = []

        for items in emailLists:
            listNames.append(items.listName)

        return listNames

    @staticmethod
    def allTemplates(currentACL, admin):
        if currentACL['admin'] == 1:
            allTemplates = EmailTemplate.objects.all()
        else:
            allTemplates = admin.emailtemplate_set.all()

        templateNames = []
        for items in allTemplates:
            templateNames.append(items.name)
        return templateNames

    @staticmethod
    def allSMTPHosts(currentACL, admin):
        if currentACL['admin'] == 1:
            allHosts = SMTPHosts.objects.all()
        else:
            allHosts = admin.smtphosts_set.all()
        hostNames = []

        for items in allHosts:
            hostNames.append(items.host)

        return hostNames

    @staticmethod
    def allEmailsLists(currentACL, admin):
        listNames = []
        emailLists = EmailLists.objects.all()

        if currentACL['admin'] == 1:
            for items in emailLists:
                listNames.append(items.listName)
        else:
            for items in emailLists:
                if items.owner.admin == admin:
                    listNames.append(items.listName)

        return listNames



