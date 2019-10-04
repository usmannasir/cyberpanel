from __future__ import unicode_literals

from django.db import models
from websiteFunctions.models import Websites
from datetime import datetime

class IncJob(models.Model):
    website = models.ForeignKey(Websites)
    date = models.DateTimeField(default=datetime.now, blank=True)

class JobSnapshots(models.Model):
    job = models.ForeignKey(IncJob)
    type = models.CharField(max_length=50)
    snapshotid = models.CharField(max_length=50)