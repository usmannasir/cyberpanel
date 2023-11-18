from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preWebsiteCreation(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteCreation)

    @staticmethod
    def postWebsiteCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postWebsiteCreation, response)

    @staticmethod
    def preDomainCreation(request):
        return pluginManagerGlobal.globalPlug(request, preDomainCreation)

    @staticmethod
    def postDomainCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postDomainCreation, response)

    @staticmethod
    def preWebsiteDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteDeletion)

    @staticmethod
    def postWebsiteDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postWebsiteDeletion, response)

    @staticmethod
    def preDomainDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preDomainDeletion)

    @staticmethod
    def postDomainDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postDomainDeletion, response)

    @staticmethod
    def preWebsiteSuspension(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteSuspension)

    @staticmethod
    def postWebsiteSuspension(request, response):
        return pluginManagerGlobal.globalPlug(request, postWebsiteSuspension, response)

    @staticmethod
    def preWebsiteModification(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteModification)

    @staticmethod
    def postWebsiteModification(request, response):
        return pluginManagerGlobal.globalPlug(request, postWebsiteModification, response)

    @staticmethod
    def preDomain(request):
        return pluginManagerGlobal.globalPlug(request, preDomain)

    @staticmethod
    def postDomain(request, response):
        return pluginManagerGlobal.globalPlug(request, postDomain, response)

    @staticmethod
    def preSaveConfigsToFile(request):
        return pluginManagerGlobal.globalPlug(request, preSaveConfigsToFile)

    @staticmethod
    def postSaveConfigsToFile(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveConfigsToFile, response)

    @staticmethod
    def preSaveRewriteRules(request):
        return pluginManagerGlobal.globalPlug(request, preSaveRewriteRules)

    @staticmethod
    def postSaveRewriteRules(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveRewriteRules, response)

    @staticmethod
    def preSaveSSL(request):
        return pluginManagerGlobal.globalPlug(request, preSaveSSL)

    @staticmethod
    def postSaveSSL(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveSSL, response)

    @staticmethod
    def preChangePHP(request):
        return pluginManagerGlobal.globalPlug(request, preChangePHP)

    @staticmethod
    def postChangePHP(request, response):
        return pluginManagerGlobal.globalPlug(request, postChangePHP, response)

    @staticmethod
    def preChangeOpenBasedir(request):
        return pluginManagerGlobal.globalPlug(request, preChangeOpenBasedir)

    @staticmethod
    def postChangeOpenBasedir(request, response):
        return pluginManagerGlobal.globalPlug(request, postChangeOpenBasedir, response)

    @staticmethod
    def preAddNewCron(request):
        return pluginManagerGlobal.globalPlug(request, preAddNewCron)

    @staticmethod
    def postAddNewCron(request, response):
        return pluginManagerGlobal.globalPlug(request, postAddNewCron, response)

    @staticmethod
    def preRemCronbyLine(request):
        return pluginManagerGlobal.globalPlug(request, preRemCronbyLine)

    @staticmethod
    def postRemCronbyLine(request, response):
        return pluginManagerGlobal.globalPlug(request, postRemCronbyLine, response)

    @staticmethod
    def preSubmitAliasCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitAliasCreation)

    @staticmethod
    def postSubmitAliasCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitAliasCreation, response)

    @staticmethod
    def preDelateAlias(request):
        return pluginManagerGlobal.globalPlug(request, preDelateAlias)

    @staticmethod
    def postDelateAlias(request, response):
        return pluginManagerGlobal.globalPlug(request, postDelateAlias, response)