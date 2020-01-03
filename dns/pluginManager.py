from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preNSCreation(request):
        return pluginManagerGlobal.globalPlug(request, preNSCreation)

    @staticmethod
    def postNSCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postNSCreation, response)

    @staticmethod
    def preZoneCreation(request):
        return pluginManagerGlobal.globalPlug(request, preZoneCreation)

    @staticmethod
    def postZoneCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postZoneCreation, response)

    @staticmethod
    def preAddDNSRecord(request):
        return pluginManagerGlobal.globalPlug(request, preAddDNSRecord)

    @staticmethod
    def postAddDNSRecord(request, response):
        return pluginManagerGlobal.globalPlug(request, postAddDNSRecord, response)

    @staticmethod
    def preDeleteDNSRecord(request):
        return pluginManagerGlobal.globalPlug(request, preDeleteDNSRecord)

    @staticmethod
    def postDeleteDNSRecord(request, response):
        return pluginManagerGlobal.globalPlug(request, postDeleteDNSRecord, response)

    @staticmethod
    def preSubmitZoneDeletion(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitZoneDeletion)

    @staticmethod
    def postSubmitZoneDeletion(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitZoneDeletion, response)