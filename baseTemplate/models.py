# -*- coding: utf-8 -*-


from django.db import models

# Create your models here.


class version(models.Model):
    currentVersion = models.CharField(max_length=50)
    build = models.IntegerField()