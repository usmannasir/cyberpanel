# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from loginSystem.models import Administrator
from packages.models import VMPackage as Package
from ipManagement.models import IPAddresses
from hypervisor.models import HyberVisors

# Create your models here.

class VPS(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.PROTECT, default=1)
    hypervisor = models.ForeignKey(HyberVisors, on_delete=models.PROTECT, default=1)
    ipAddr = models.ForeignKey(IPAddresses, on_delete=models.PROTECT, default=1)
    package = models.ForeignKey(Package, on_delete=models.PROTECT, default=1)
    hostName = models.CharField(unique=True, max_length = 50)
    networkSpeed = models.CharField(max_length = 50)
    vncPort = models.IntegerField()
    vncPassword = models.CharField(max_length = 100, default='None')
    websocketPort = models.IntegerField(default=5700)


class SSHKeys(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    keyName = models.CharField(max_length=10, default='None')
    key = models.CharField(max_length=500)


class Snapshots(models.Model):
    vps = models.ForeignKey(VPS, on_delete=models.CASCADE)
    name = models.CharField(max_length = 50)
    creationTime = models.CharField(max_length = 70)