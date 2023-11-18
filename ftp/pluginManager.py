from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preCreateFTPAccount(request):
        return pluginManagerGlobal.globalPlug(request, preCreateFTPAccount)

    @staticmethod
    def postCreateFTPAccount(request, response):
        return pluginManagerGlobal.globalPlug(request, postCreateFTPAccount, response)

    @staticmethod
    def preSubmitFTPCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitFTPCreation)

    @staticmethod
    def postSubmitFTPCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitFTPCreation, response)

    @staticmethod
    def preSubmitFTPDelete(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitFTPDelete)

    @staticmethod
    def postSubmitFTPDelete(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitFTPDelete, response)

    @staticmethod
    def preChangePassword(request):
        return pluginManagerGlobal.globalPlug(request, preChangePassword)

    @staticmethod
    def postChangePassword(request, response):
        return pluginManagerGlobal.globalPlug(request, postChangePassword, response)