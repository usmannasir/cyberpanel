# -*- coding: utf-8 -*-


from django.db import models
from mailServer.models import Domains, EUsers
# Create your models here.

class DomainLimits(models.Model):
    domain = models.ForeignKey(Domains, on_delete=models.CASCADE)
    limitStatus = models.IntegerField(default=0)
    monthlyLimit = models.IntegerField(default=10000)
    monthlyUsed = models.IntegerField(default=0)

class EmailLimits(models.Model):
    email = models.ForeignKey(EUsers, on_delete=models.CASCADE)
    limitStatus = models.IntegerField(default=0)
    monthlyLimits = models.IntegerField(default=2000)
    monthlyUsed = models.IntegerField(default=0)
    hourlyLimit = models.IntegerField(default=50)
    hourlyUsed = models.IntegerField(default=0)
    emailLogs = models.IntegerField(default=0)

class EmailLogs(models.Model):
    email = models.ForeignKey(EUsers, on_delete=models.CASCADE)
    destination = models.CharField(max_length=200)
    timeStamp = models.CharField(max_length=200)

