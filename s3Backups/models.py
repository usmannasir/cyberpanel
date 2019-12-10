# -*- coding: utf-8 -*-


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

class BackupPlanDO(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)
    bucket = models.CharField(max_length=50, default='NONE')
    freq = models.CharField(max_length=50)
    retention = models.IntegerField()
    type = models.CharField(max_length=5, default='DO')
    region = models.CharField(max_length=5)
    lastRun = models.CharField(max_length=50, default='0:0:0')

class WebsitesInPlanDO(models.Model):
    owner = models.ForeignKey(BackupPlanDO, on_delete=models.CASCADE)
    domain = models.CharField(max_length=100)


class BackupLogsDO(models.Model):
    owner = models.ForeignKey(BackupPlanDO, on_delete=models.CASCADE)
    timeStamp = models.CharField(max_length=200)
    level = models.CharField(max_length=5)
    msg = models.CharField(max_length=500)

class MINIONodes(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    endPointURL = models.CharField(max_length=200, unique=True)
    accessKey = models.CharField(max_length=200, unique=True)
    secretKey = models.CharField(max_length=200)


class BackupPlanMINIO(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    minioNode = models.ForeignKey(MINIONodes, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)
    freq = models.CharField(max_length=50)
    retention = models.IntegerField()
    lastRun = models.CharField(max_length=50, default='0:0:0')

class WebsitesInPlanMINIO(models.Model):
    owner = models.ForeignKey(BackupPlanMINIO, on_delete=models.CASCADE)
    domain = models.CharField(max_length=100)


class BackupLogsMINIO(models.Model):
    owner = models.ForeignKey(BackupPlanMINIO, on_delete=models.CASCADE)
    timeStamp = models.CharField(max_length=200)
    level = models.CharField(max_length=5)
    msg = models.CharField(max_length=500)