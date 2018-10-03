from signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preWebsiteCreation(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteCreation)

    @staticmethod
    def postWebsiteCreation(request):
        return pluginManagerGlobal.globalPlug(request, postWebsiteCreation)

    @staticmethod
    def preDomainCreation(request):
        return pluginManagerGlobal.globalPlug(request, preDomainCreation)

    @staticmethod
    def postDomainCreation(request):
        return pluginManagerGlobal.globalPlug(request, postDomainCreation)

    @staticmethod
    def preWebsiteDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteDeletion)

    @staticmethod
    def postWebsiteDeletion(request):
        return pluginManagerGlobal.globalPlug(request, postWebsiteDeletion)

    @staticmethod
    def preDomainDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preDomainDeletion)

    @staticmethod
    def postDomainDeletion(request):
        return pluginManagerGlobal.globalPlug(request, postDomainDeletion)

    @staticmethod
    def preWebsiteSuspension(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteSuspension)

    @staticmethod
    def postWebsiteSuspension(request):
        return pluginManagerGlobal.globalPlug(request, postWebsiteSuspension)

    @staticmethod
    def preWebsiteModification(request):
        return pluginManagerGlobal.globalPlug(request, preWebsiteModification)

    @staticmethod
    def postWebsiteModification(request):
        return pluginManagerGlobal.globalPlug(request, postWebsiteModification)

    @staticmethod
    def preSaveConfigsToFile(request):
        return pluginManagerGlobal.globalPlug(request, preSaveConfigsToFile)

    @staticmethod
    def postSaveConfigsToFile(request):
        return pluginManagerGlobal.globalPlug(request, postSaveConfigsToFile)

    @staticmethod
    def preSaveRewriteRules(request):
        return pluginManagerGlobal.globalPlug(request, preSaveRewriteRules)

    @staticmethod
    def postSaveRewriteRules(request):
        return pluginManagerGlobal.globalPlug(request, postSaveRewriteRules)

    @staticmethod
    def preSaveSSL(request):
        return pluginManagerGlobal.globalPlug(request, preSaveSSL)

    @staticmethod
    def postSaveSSL(request):
        return pluginManagerGlobal.globalPlug(request, postSaveSSL)

    @staticmethod
    def preChangePHP(request):
        return pluginManagerGlobal.globalPlug(request, preChangePHP)

    @staticmethod
    def postChangePHP(request):
        return pluginManagerGlobal.globalPlug(request, postChangePHP)

    @staticmethod
    def preChangeOpenBasedir(request):
        return pluginManagerGlobal.globalPlug(request, preChangeOpenBasedir)

    @staticmethod
    def postChangeOpenBasedir(request):
        return pluginManagerGlobal.globalPlug(request, postChangeOpenBasedir)

    @staticmethod
    def preAddNewCron(request):
        return pluginManagerGlobal.globalPlug(request, preAddNewCron)

    @staticmethod
    def postAddNewCron(request):
        return pluginManagerGlobal.globalPlug(request, postAddNewCron)

    @staticmethod
    def preRemCronbyLine(request):
        return pluginManagerGlobal.globalPlug(request, preRemCronbyLine)

    @staticmethod
    def postRemCronbyLine(request):
        return pluginManagerGlobal.globalPlug(request, postRemCronbyLine)

    @staticmethod
    def preSubmitAliasCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitAliasCreation)

    @staticmethod
    def postSubmitAliasCreation(request):
        return pluginManagerGlobal.globalPlug(request, postSubmitAliasCreation)

    @staticmethod
    def preDelateAlias(request):
        return pluginManagerGlobal.globalPlug(request, preDelateAlias)

    @staticmethod
    def postDelateAlias(request):
        return pluginManagerGlobal.globalPlug(request, postDelateAlias)