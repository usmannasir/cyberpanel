from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preSubmitEmailCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitEmailCreation)

    @staticmethod
    def postSubmitEmailCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitEmailCreation, response)

    @staticmethod
    def preSubmitEmailDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitEmailDeletion)

    @staticmethod
    def postSubmitEmailDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitEmailDeletion, response)

    @staticmethod
    def preSubmitForwardDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitForwardDeletion)

    @staticmethod
    def postSubmitForwardDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitForwardDeletion, response)

    @staticmethod
    def preSubmitEmailForwardingCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitEmailForwardingCreation)

    @staticmethod
    def postSubmitEmailForwardingCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitEmailForwardingCreation, response)

    @staticmethod
    def preSubmitPasswordChange(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitPasswordChange)

    @staticmethod
    def postSubmitPasswordChange(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitPasswordChange, response)

    @staticmethod
    def preGenerateDKIMKeys(request):
        return pluginManagerGlobal.globalPlug(request, preGenerateDKIMKeys)

    @staticmethod
    def postGenerateDKIMKeys(request, response):
        return pluginManagerGlobal.globalPlug(request, postGenerateDKIMKeys, response)