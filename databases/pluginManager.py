from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preCreateDatabase(request):
        return pluginManagerGlobal.globalPlug(request, preCreateDatabase)

    @staticmethod
    def postCreateDatabase(request, response):
        return pluginManagerGlobal.globalPlug(request, postCreateDatabase, response)

    @staticmethod
    def preSubmitDBCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitDBCreation)

    @staticmethod
    def postSubmitDBCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitDBCreation, response)

    @staticmethod
    def preSubmitDatabaseDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitDatabaseDeletion)

    @staticmethod
    def postSubmitDatabaseDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitDatabaseDeletion, response)

    @staticmethod
    def preChangePassword(request):
        return pluginManagerGlobal.globalPlug(request, preChangePassword)

    @staticmethod
    def postChangePassword(request, response):
        return pluginManagerGlobal.globalPlug(request, postChangePassword, response)