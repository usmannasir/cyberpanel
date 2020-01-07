# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.

from django.db import models
from websiteFunctions.models import Websites, ChildDomains


class Domains(models.Model):
    domainOwner = models.ForeignKey(Websites,on_delete=models.CASCADE, null=True)
    childOwner = models.ForeignKey(ChildDomains, on_delete=models.CASCADE, null=True)
    domain = models.CharField(primary_key=True, max_length=50)

    class Meta:
        db_table = 'e_domains'


class EUsers(models.Model):
    emailOwner = models.ForeignKey(Domains, on_delete=models.CASCADE)
    email = models.CharField(primary_key=True, max_length=80)
    password = models.CharField(max_length=200)
    mail = models.CharField(max_length=200, default='')


    class Meta:
        db_table = 'e_users'

class Forwardings(models.Model):
    source = models.CharField(max_length=80)
    destination = models.TextField()

    class Meta:
        db_table = 'e_forwardings'


class Transport(models.Model):
    domain = models.CharField(unique=True, max_length=128)
    transport = models.CharField(max_length=128)

    class Meta:
        db_table = 'e_transport'


class Pipeprograms(models.Model):
    source = models.CharField(max_length=80)
    destination = models.TextField()
