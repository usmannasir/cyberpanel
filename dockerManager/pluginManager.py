from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preDockerInstallation(request):
        return pluginManagerGlobal.globalPlug(request, preDockerInstallation)

    @staticmethod
    def postDockerInstallation(request, response):
        return pluginManagerGlobal.globalPlug(request, postDockerInstallation, response)