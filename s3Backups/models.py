# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from loginSystem.models import Administrator
# Create your models here.

class BackupPlan(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)
    bucket = models.CharField(max_length=50, default='NONE')
    freq = models.CharField(max_length=50)
    retention = models.IntegerField()
    type = models.CharField(max_length=5, default='AWS')
    lastRun = models.CharField(max_length=50, default='0:0:0')

class WebsitesInPlan(models.Model):
    owner = models.ForeignKey(BackupPlan,on_delete=models.CASCADE)
    domain = models.CharField(max_length=100)


class BackupLogs(models.Model):
    owner = models.ForeignKey(BackupPlan,on_delete=models.CASCADE)
    timeStamp = models.CharField(max_length=200)
    level = models.CharField(max_length=5)
    msg = models.CharField(max_length=500)