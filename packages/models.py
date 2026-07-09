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
    enforceDiskLimits = models.IntegerField(default=0)

    # Resource Limits - enforced via cgroups v2 and OpenLiteSpeed
    memoryLimitMB = models.IntegerField(default=1024, help_text="Memory limit in MB")
    cpuCores = models.IntegerField(default=1, help_text="Number of CPU cores")
    ioLimitMBPS = models.IntegerField(default=10, help_text="I/O limit in MB/s")
    inodeLimit = models.IntegerField(default=400000, help_text="Maximum number of files/directories")
    maxConnections = models.IntegerField(default=10, help_text="Max concurrent PHP connections")
    procSoftLimit = models.IntegerField(default=400, help_text="Soft process limit")
    procHardLimit = models.IntegerField(default=500, help_text="Hard process limit")
