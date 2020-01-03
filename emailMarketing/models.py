# -*- coding: utf-8 -*-


from django.db import models
from websiteFunctions.models import Websites
from loginSystem.models import Administrator

# Create your models here.

class EmailMarketing(models.Model):
    userName = models.CharField(max_length=50, unique=True)

class EmailLists(models.Model):
    owner = models.ForeignKey(Websites, on_delete=models.PROTECT)
    listName = models.CharField(max_length=50, unique=True)
    dateCreated = models.CharField(max_length=200)


class EmailsInList(models.Model):
    owner = models.ForeignKey(EmailLists, on_delete=models.CASCADE)
    email = models.CharField(max_length=50)
    firstName = models.CharField(max_length=20, default='')
    lastName = models.CharField(max_length=20, default='')
    verificationStatus = models.CharField(max_length=100)
    dateCreated = models.CharField(max_length=200)

class SMTPHosts(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    host = models.CharField(max_length=150, unique= True)
    port = models.CharField(max_length=10)
    userName = models.CharField(max_length=50)
    password = models.CharField(max_length=50)


class EmailTemplate(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    name = models.CharField(unique=True, max_length=100)
    subject = models.CharField(max_length=1000)
    fromName = models.CharField(max_length=100)
    fromEmail = models.CharField(max_length=150)
    replyTo = models.CharField(max_length=150)
    emailMessage = models.TextField(max_length=65532)

class EmailJobs(models.Model):
    owner = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    date = models.CharField(max_length=200)
    host = models.CharField(max_length=1000)
    totalEmails = models.IntegerField()
    sent = models.IntegerField()
    failed = models.IntegerField()

