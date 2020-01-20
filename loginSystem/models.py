# -*- coding: utf-8 -*-


from django.db import models

# Create your models here.

class ACL(models.Model):
   name = models.CharField(unique=True,max_length = 50)
   adminStatus = models.IntegerField(default=0)

   ## Version Management
   versionManagement = models.IntegerField(default=0)

   ## User Management
   createNewUser = models.IntegerField(default=0)
   listUsers = models.IntegerField(default=0)
   deleteUser = models.IntegerField(default=0)
   resellerCenter = models.IntegerField(default=0)
   changeUserACL = models.IntegerField(default=0)

   ## Website Management

   createWebsite = models.IntegerField(default=0)
   modifyWebsite = models.IntegerField(default=0)
   suspendWebsite = models.IntegerField(default=0)
   deleteWebsite = models.IntegerField(default=0)

   ## Package Management

   createPackage = models.IntegerField(default=0)
   listPackages = models.IntegerField(default=0)
   deletePackage = models.IntegerField(default=0)
   modifyPackage = models.IntegerField(default=0)

   ## Database Management

   createDatabase = models.IntegerField(default=1)
   deleteDatabase = models.IntegerField(default=1)
   listDatabases = models.IntegerField(default=1)

   ## DNS Management

   createNameServer = models.IntegerField(default=0)
   createDNSZone = models.IntegerField(default=1)
   deleteZone = models.IntegerField(default=1)
   addDeleteRecords = models.IntegerField(default=1)

   ## Email Management

   createEmail = models.IntegerField(default=1)
   listEmails = models.IntegerField(default=1)
   deleteEmail = models.IntegerField(default=1)
   emailForwarding = models.IntegerField(default=1)
   changeEmailPassword = models.IntegerField(default=1)
   dkimManager = models.IntegerField(default=1)

   ## FTP Management

   createFTPAccount = models.IntegerField(default=1)
   deleteFTPAccount = models.IntegerField(default=1)
   listFTPAccounts = models.IntegerField(default=1)

   ## Backup Management

   createBackup = models.IntegerField(default=1)
   restoreBackup = models.IntegerField(default=0)
   addDeleteDestinations = models.IntegerField(default=0)
   scheDuleBackups = models.IntegerField(default=0)
   remoteBackups = models.IntegerField(default=0)

   ## SSL Management

   manageSSL = models.IntegerField(default=1)
   hostnameSSL = models.IntegerField(default=0)
   mailServerSSL = models.IntegerField(default=0)

class Administrator(models.Model):
   userName = models.CharField(unique=True,max_length = 50)
   password = models.CharField(max_length = 200)
   firstName = models.CharField(max_length = 20,default="None")
   lastName = models.CharField(max_length = 20,default="None")
   email = models.CharField(max_length=50)
   type = models.IntegerField()
   owner = models.IntegerField(default=1)
   token = models.CharField(max_length=500, default='None')
   api = models.IntegerField(default=0)
   securityLevel = models.IntegerField(default=0)
   state = models.CharField(max_length=10, default='ACTIVE')


   initWebsitesLimit = models.IntegerField(default=0)
   acl = models.ForeignKey(ACL, default=1, on_delete=models.PROTECT)









