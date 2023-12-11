# -*- coding: utf-8 -*-


from django.db import models
from loginSystem.models import Administrator
from websiteFunctions.website import Websites

# Create your models here.
class Containers(models.Model):
    name = models.CharField(max_length=50,unique=True)
    cid = models.CharField(max_length=64, default='')
    admin = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    image = models.CharField(max_length=50, default='unknown')
    tag = models.CharField(max_length=50, default='unknown')
    memory = models.IntegerField(default=0)
    ports = models.TextField(default="{}")
    volumes = models.TextField(default="{}")
    env = models.TextField(default="{}")
    startOnReboot = models.IntegerField(default=0)

# Takes
# ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
# port, SitePath, CPUsSite, MemorySite, SiteName
# finalURL, blogTitle, adminUser, adminPassword, adminEmail

### Site Type 0=wp, further tbd later

class DockerSites(models.Model):
    admin = models.ForeignKey(Websites, on_delete=models.CASCADE)
    ComposePath = models.TextField()
    SitePath = models.TextField()
    MySQLPath = models.TextField()
    state = models.IntegerField(default=1)
    SiteType = models.IntegerField(default=0) ## WP, Joomla etc
    MySQLDBName = models.CharField(max_length=100)
    MySQLDBNUser = models.CharField(max_length=100)
    CPUsMySQL = models.CharField(max_length=100)
    MemoryMySQL = models.CharField(max_length=100)
    port = models.CharField(max_length=100)
    CPUsSite = models.CharField(max_length=100)
    MemorySite = models.CharField(max_length=100)
    SiteName = models.TextField()
    finalURL = models.TextField()
    blogTitle = models.TextField()
    adminUser = models.CharField(max_length=100)
    adminEmail = models.CharField(max_length=100)