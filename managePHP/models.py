# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


class PHP(models.Model):
    phpVers = models.CharField(max_length=5,unique=True)

class installedPackages(models.Model):
    phpVers = models.ForeignKey(PHP, on_delete=models.CASCADE)
    extensionName = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    status = models.IntegerField()

