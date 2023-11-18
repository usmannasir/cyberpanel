# -*- coding: utf-8 -*-


from django.db import models
from websiteFunctions.models import Websites

# Create your models here.

class Trash(models.Model):
    website = models.ForeignKey(Websites,on_delete=models.CASCADE)
    originalPath = models.CharField(max_length=500,default=None)
    fileName = models.CharField(max_length=200, default=None)
