# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from loginSystem.models import Administrator

# Create your models here.
class Containers(models.Model):
    name = models.CharField(max_length=50,unique=True)
    cid = models.CharField(max_length=64, default='')
    admin = models.ForeignKey(Administrator)
    image = models.CharField(max_length=50, default='unknown')
    tag = models.CharField(max_length=50, default='unknown')
    memory = models.IntegerField(default=0)
    ports = models.TextField(default="{}")
    volumes = models.TextField(default="{}")
    env = models.TextField(default="{}")
    startOnReboot = models.IntegerField(default=0)
