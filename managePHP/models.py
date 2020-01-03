# -*- coding: utf-8 -*-


from django.db import models

# Create your models here.


class PHP(models.Model):
    phpVers = models.CharField(max_length=5,unique=True)

class installedPackages(models.Model):
    phpVers = models.ForeignKey(PHP, on_delete=models.CASCADE)
    extensionName = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    status = models.IntegerField()


class ApachePHP(models.Model):
    phpVers = models.CharField(max_length=5,unique=True)

class installedPackagesApache(models.Model):
    phpVers = models.ForeignKey(ApachePHP, on_delete=models.CASCADE)
    extensionName = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    status = models.IntegerField()

