from django.http import HttpResponse
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class pluginManagerGlobal:
    @staticmethod
    def globalPlug(request, eventInQuest, response = None):
        if response == None:
            hookReturn = eventInQuest.send(sender=None, request=request)
        else:
            hookReturn = eventInQuest.send(sender=None, request=request, response = response)
        for items in hookReturn:
            if type(items[1] == HttpResponse):
                return items[1]
            else:
                if items[1] == 200:
                    return items[1]
                else:
                    logging.writeToFile('Something wrong with : ' + str(items[0]) + ' on ' + str(eventInQuest))
                    return 200
        return 200