

from django.db import models
from loginSystem.models import Administrator


class Domains(models.Model):
    admin = models.ForeignKey(Administrator,on_delete=models.CASCADE, default=1, null=True)
    name = models.CharField(unique=True, max_length=255)
    master = models.CharField(max_length=128, blank=True, null=True)
    last_check = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=6)
    notified_serial = models.IntegerField(blank=True, null=True)
    account = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        db_table = 'domains'


class Records(models.Model):
    domainOwner = models.ForeignKey(Domains, on_delete=models.CASCADE, null=True)
    id = models.BigAutoField(primary_key=True)
    domain_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=10, blank=True, null=True)
    content = models.CharField(max_length=64000, blank=True, null=True)
    ttl = models.IntegerField(blank=True, null=True)
    prio = models.IntegerField(blank=True, null=True)
    change_date = models.IntegerField(blank=True, null=True)
    disabled = models.IntegerField(blank=True, null=True)
    ordername = models.CharField(max_length=255, blank=True, null=True)
    auth = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'records'


class Comments(models.Model):
    domain_id = models.IntegerField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10)
    modified_at = models.IntegerField()
    account = models.CharField(max_length=40)
    comment = models.CharField(max_length=64000)

    class Meta:
        db_table = 'comments'


class Cryptokeys(models.Model):
    domain_id = models.IntegerField()
    flags = models.IntegerField()
    active = models.IntegerField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cryptokeys'


class Domainmetadata(models.Model):
    domain_id = models.IntegerField()
    kind = models.CharField(max_length=32, blank=True, null=True)
    content = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'domainmetadata'


class Supermasters(models.Model):
    ip = models.CharField(primary_key=True, max_length=64)
    nameserver = models.CharField(max_length=255)
    account = models.CharField(max_length=40)

    class Meta:
        db_table = 'supermasters'
        unique_together = (('ip', 'nameserver'),)


class Tsigkeys(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    algorithm = models.CharField(max_length=50, blank=True, null=True)
    secret = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'tsigkeys'
        unique_together = (('name', 'algorithm'),)
