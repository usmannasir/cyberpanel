from django.db import models
from websiteFunctions.models import Websites
from loginSystem.models import Administrator
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
    retention = models.IntegerField(default=0) # 0 being unlimited retention


class JobSites(models.Model):
    job = models.ForeignKey(BackupJob, on_delete=models.CASCADE)
    website = models.CharField(max_length=300)


class OneClickBackups(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    planName = models.CharField(max_length=100)
    months = models.CharField(max_length=100)
    price = models.CharField(max_length=100)
    customer = models.CharField(max_length=300)
    subscription = models.CharField(max_length=300, unique=True)
    sftpUser = models.CharField(max_length=100)
    config = models.TextField(default='{}')
    date = models.DateTimeField(default=datetime.now, blank=True)
    state = models.IntegerField(default=0)



