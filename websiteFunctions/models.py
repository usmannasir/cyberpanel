# -*- coding: utf-8 -*-


from django.db import models
from packages.models import Package
from loginSystem.models import Administrator

# Create your models here.


class Websites(models.Model):
    admin = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    domain = models.CharField(max_length=50,unique=True)
    adminEmail = models.CharField(max_length=50)
    phpSelection = models.CharField(max_length=10)
    ssl = models.IntegerField()
    state = models.IntegerField(default=1)
    externalApp = models.CharField(max_length=10, default=None)

class ChildDomains(models.Model):
    master = models.ForeignKey(Websites,on_delete=models.CASCADE)
    domain = models.CharField(max_length=50, unique=True)
    path = models.CharField(max_length=200,default=None)
    ssl = models.IntegerField()
    phpSelection = models.CharField(max_length=10,default=None)


class Backups(models.Model):
    website = models.ForeignKey(Websites,on_delete=models.CASCADE)
    fileName = models.CharField(max_length=50)
    date = models.CharField(max_length=50)
    size = models.CharField(max_length=50)
    status = models.IntegerField(default=0)


class dest(models.Model):
    destLoc = models.CharField(unique=True,max_length=18)


class backupSchedules(models.Model):
    dest = models.ForeignKey(dest, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=15)


class aliasDomains(models.Model):
    master = models.ForeignKey(Websites, on_delete=models.CASCADE)
    aliasDomain = models.CharField(max_length=75)

