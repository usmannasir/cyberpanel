# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class PDNSStatus(models.Model):
    serverStatus = models.IntegerField(default=1)
    type = models.CharField(max_length=6, default='NATIVE')
    allow_axfr_ips = models.CharField(max_length=500, default='')
    also_notify = models.CharField(max_length=500, default='')