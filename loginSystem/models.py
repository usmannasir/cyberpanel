# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class Administrator(models.Model):
   userName = models.CharField(unique=True,max_length = 50)
   password = models.CharField(max_length = 200)
   firstName = models.CharField(max_length = 20,default="None")
   lastName = models.CharField(max_length = 20,default="None")
   email = models.CharField(max_length=50)
   type = models.IntegerField()
   owner = models.IntegerField(default=1)

   initUserAccountsLimit = models.IntegerField(default=0)
   initWebsitesLimit = models.IntegerField(default=0)