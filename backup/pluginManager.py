from signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preSubmitBackupCreation(request):
        return pluginManagerGlobal.globalPlug(request, preSubmitBackupCreation)

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