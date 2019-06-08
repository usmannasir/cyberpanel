from django.db import models
from websiteFunctions.models import Websites


class Users(models.Model):
    domain = models.ForeignKey(Websites,on_delete=models.CASCADE)
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    user = models.CharField(db_column='User', unique=True, max_length=32)  # Field name made lowercase.
    password = models.CharField(db_column='Password', max_length=64)  # Field name made lowercase.
    uid = models.IntegerField(db_column='Uid')  # Field name made lowercase.
    gid = models.IntegerField(db_column='Gid')  # Field name made lowercase.
    dir = models.CharField(db_column='Dir', max_length=255)  # Field name made lowercase.
    quotasize = models.IntegerField(db_column='QuotaSize')  # Field name made lowercase.
    status = models.CharField(db_column='Status', max_length=1)  # Field name made lowercase.
    ulbandwidth = models.IntegerField(db_column='ULBandwidth')  # Field name made lowercase.
    dlbandwidth = models.IntegerField(db_column='DLBandwidth')  # Field name made lowercase.
    date = models.DateField(db_column='Date')  # Field name made lowercase.
    lastmodif = models.CharField(db_column='LastModif', max_length=255)  # Field name made lowercase.

    class Meta:
        db_table = 'users'