from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preCreatePacakge(request):
        return pluginManagerGlobal.globalPlug(request, preCreatePacakge)

    @staticmethod
    def postCreatePacakge(request, response):
        return pluginManagerGlobal.globalPlug(request, postCreatePacakge, response)

    @staticmethod
    def preSubmitPackage(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitPackage)

    @staticmethod
    def postSubmitPackage(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitPackage, response)

    @staticmethod
    def preSubmitDelete(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitDelete)

    @staticmethod
    def postSubmitDelete(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitDelete, response)

    @staticmethod
    def preSaveChanges(request):
        return pluginManagerGlobal.globalPlug(request, preSaveChanges)

    @staticmethod
    def postSaveChanges(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveChanges, response)