#!/usr/local/CyberCP/bin/python
import os, sys

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging



class UserManager(multi.Thread):

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs


    def run(self):
        try:
            if self.function == 'controlUserState':
                self.controlUserState()
        except:
            pass

    def controlUserState(self):
        try:
            websites = ACLManager.findAllSites(self.extraArgs['currentACL'],self.extraArgs['user'].pk)
            from websiteFunctions.website import WebsiteManager

            wm = WebsiteManager()

            if self.extraArgs['state'] == 'SUSPEND':
                for items in websites:
                    data = {'websiteName': items, 'state': 'Suspend'}
                    wm.submitWebsiteStatus(self.extraArgs['user'].pk, data)
            else:
                for items in websites:
                    data = {'websiteName': items, 'state': 'UN-Suspend'}
                    wm.submitWebsiteStatus(self.extraArgs['user'].pk, data)


        except BaseException as msg:
            logging.writeToFile(str(msg) + '[Error:UserManager:32]')