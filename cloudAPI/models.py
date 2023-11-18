# -*- coding: utf-8 -*-

from django.db import models
from websiteFunctions.models import Websites
# Create your models here.
class WPDeployments(models.Model):
   owner = models.ForeignKey(Websites, on_delete=models.CASCADE)
   config = models.TextField()