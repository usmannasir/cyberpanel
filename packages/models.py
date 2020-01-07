# -*- coding: utf-8 -*-

from loginSystem.models import Administrator

from django.db import models

# Create your models here.

class Package(models.Model):
    admin = models.ForeignKey(Administrator,on_delete=models.CASCADE)
    packageName = models.CharField(max_length=50,unique=True)
    diskSpace = models.IntegerField()
    bandwidth = models.IntegerField()
    emailAccounts = models.IntegerField(null=True)
    dataBases = models.IntegerField(default=0)
    ftpAccounts = models.IntegerField(default=0)
    allowedDomains = models.IntegerField(default=0)
    allowFullDomain = models.IntegerField(default=1)
