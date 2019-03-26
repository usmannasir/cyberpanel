from django.db import models

# Create your models here.

class FirewallRules(models.Model):
    name = models.CharField(unique=True, max_length=32)  # Field name made lowercase.
    proto = models.CharField(max_length=10)
    port = models.CharField(max_length=25)
    ipAddress = models.CharField(max_length=30,default="0.0.0.0/0")
