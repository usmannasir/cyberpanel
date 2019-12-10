# -*- coding: utf-8 -*-


from django.db import models

# Create your models here.

class PDNSStatus(models.Model):
    serverStatus = models.IntegerField(default=1)
    type = models.CharField(max_length=6, default='NATIVE')
    masterServer = models.CharField(max_length=200, default='')
    masterIP = models.CharField(max_length=200, default='')


class SlaveServers(models.Model):
    slaveServer = models.CharField(max_length=200, default='NATIVE')
    slaveServerIP = models.CharField(max_length=200, default='NATIVE')
