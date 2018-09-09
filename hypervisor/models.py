# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from loginSystem.models import Administrator

class HyberVisors(models.Model):
    hypervisorOwner = models.ForeignKey(Administrator)
    hypervisorName = models.CharField(max_length=50, unique=True)
    hypervisorIP = models.CharField(max_length=50, unique=True)
    hypervisorUserName = models.CharField(max_length=50)
    hypervisorPassword = models.CharField(max_length=100)
    hypervisorStoragePath = models.CharField(max_length=500)
