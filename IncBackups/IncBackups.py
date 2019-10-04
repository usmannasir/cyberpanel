#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.processUtilities import ProcessUtilities
import time
from .models import IncJob, JobSnapshots
from websiteFunctions.models import Websites

class IncJobs(multi.Thread):

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):

        if self.function == 'createBackup':
            self.createBackup()



    def createBackup(self):
        tempPath = self.extraArgs['tempPath']
        website = self.extraArgs['website']
        backupDestinations = self.extraArgs['backupDestinations']
        websiteData = self.extraArgs['websiteData']
        websiteEmails = self.extraArgs['websiteEmails']
        websiteSSLs = self.extraArgs['websiteSSLs']

        website = Websites.objects.get(domain=website)

        newJob = IncJob(website=website)
        newJob.save()

        writeToFile = open(tempPath, 'w')
        writeToFile.write('Completed')
        writeToFile.close()