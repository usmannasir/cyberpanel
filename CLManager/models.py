# -*- coding: utf-8 -*-


from django.db import models
from packages.models import Package

# Create your models here.

class CLPackages(models.Model):
    owner = models.ForeignKey(Package, on_delete=models.CASCADE)
    name = models.CharField(max_length=50,unique=True)
    speed = models.CharField(max_length=50)
    vmem = models.CharField(max_length=50)
    pmem = models.CharField(max_length=50)
    io = models.CharField(max_length=50)
    iops = models.CharField(max_length=50)
    ep = models.CharField(max_length=50)
    nproc = models.CharField(max_length=50)
    inodessoft = models.CharField(max_length=50)
    inodeshard = models.CharField(max_length=50)