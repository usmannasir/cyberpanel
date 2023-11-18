from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preBackupSite(request):
        return pluginManagerGlobal.globalPlug(request, preBackupSite)

    @staticmethod
    def postBackupSite(request, response):
        return pluginManagerGlobal.globalPlug(request, postBackupSite, response)

    @staticmethod
    def preRestoreSite(request):
        return pluginManagerGlobal.globalPlug(request, preRestoreSite)

    @staticmethod
    def postRestoreSite(request, response):
        return pluginManagerGlobal.globalPlug(request, postRestoreSite, response)

    @staticmethod
    def preSubmitBackupCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitBackupCreation)

    @staticmethod
    def preBackupStatus(request):
        return pluginManagerGlobal.globalPlug(request, preBackupStatus)

    @staticmethod
    def postBackupStatus(request, response):
        return pluginManagerGlobal.globalPlug(request, postBackupStatus, response)

    @staticmethod
    def preDeleteBackup(request):
        return pluginManagerGlobal.globalPlug(request, preDeleteBackup)

    @staticmethod
    def postDeleteBackup(request, response):
        return pluginManagerGlobal.globalPlug(request, postDeleteBackup, response)

    @staticmethod
    def preSubmitRestore(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitRestore)

    @staticmethod
    def preSubmitDestinationCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitDestinationCreation)

    @staticmethod
    def postSubmitDestinationCreation(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitDestinationCreation, response)

    @staticmethod
    def preDeleteDestination(request):
        return pluginManagerGlobal.globalPlug(request, preDeleteDestination)

    @staticmethod
    def postDeleteDestination(request, response):
        return pluginManagerGlobal.globalPlug(request, postDeleteDestination, response)

    @staticmethod
    def preSubmitBackupSchedule(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitBackupSchedule)

    @staticmethod
    def postSubmitBackupSchedule(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitBackupSchedule, response)

    @staticmethod
    def preScheduleDelete(request):
        return pluginManagerGlobal.globalPlug(request, preScheduleDelete)

    @staticmethod
    def postScheduleDelete(request, response):
        return pluginManagerGlobal.globalPlug(request, postScheduleDelete, response)

    @staticmethod
    def preSubmitRemoteBackups(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitRemoteBackups)

    @staticmethod
    def postSubmitRemoteBackups(request, response):
        return pluginManagerGlobal.globalPlug(request, postSubmitRemoteBackups, response)

    @staticmethod
    def preStarRemoteTransfer(request):
        return pluginManagerGlobal.globalPlug(request, preStarRemoteTransfer)

    @staticmethod
    def postStarRemoteTransfer(request, response):
        return pluginManagerGlobal.globalPlug(request, postStarRemoteTransfer, response)

    @staticmethod
    def preRemoteBackupRestore(request):
        return pluginManagerGlobal.globalPlug(request, preRemoteBackupRestore)

    @staticmethod
    def postRemoteBackupRestore(request, response):
        return pluginManagerGlobal.globalPlug(request, postRemoteBackupRestore, response)

    @staticmethod
    def postDeleteBackup(request, response):
        return pluginManagerGlobal.globalPlug(request, postRemoteBackupRestore, response)
