# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from websiteFunctions.models import Websites

# Create your models here.

class Databases(models.Model):
    website = models.ForeignKey(Websites)
    dbName = models.CharField(max_length=50,unique=True)
    dbUser = models.CharField(max_length=50, unique=True)
