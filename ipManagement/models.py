# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from loginSystem.models import Administrator
from hypervisor.models import HyberVisors
# Create your models here.

class IPPool(models.Model):
    hv = models.ForeignKey(HyberVisors, on_delete=models.CASCADE)
    poolName = models.CharField(unique=True, max_length = 50)
    gateway = models.CharField(max_length = 50)
    netmask = models.CharField(max_length=50)


class IPAddresses(models.Model):
    pool = models.ForeignKey(IPPool, on_delete=models.CASCADE)
    ipAddr = models.CharField(max_length=50, unique=True)
    used = models.IntegerField(default=0)
    macAddress = models.CharField(max_length=50, default='Auto')
