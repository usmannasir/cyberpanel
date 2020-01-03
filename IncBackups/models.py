

from django.db import models
from websiteFunctions.models import Websites
from datetime import datetime

class IncJob(models.Model):
    website = models.ForeignKey(Websites, on_delete=models.CASCADE)
    date = models.DateTimeField(default=datetime.now, blank=True)

class JobSnapshots(models.Model):
    job = models.ForeignKey(IncJob, on_delete=models.CASCADE)
    type = models.CharField(max_length=300)
    snapshotid = models.CharField(max_length=50)
    destination = models.CharField(max_length=200, default='')


class BackupJob(models.Model):
    destination = models.CharField(max_length=300)
    frequency = models.CharField(max_length=50)
    websiteData = models.IntegerField()
    websiteDatabases = models.IntegerField()
    websiteDataEmails = models.IntegerField()


class JobSites(models.Model):
    job = models.ForeignKey(BackupJob, on_delete=models.CASCADE)
    website = models.CharField(max_length=300)


