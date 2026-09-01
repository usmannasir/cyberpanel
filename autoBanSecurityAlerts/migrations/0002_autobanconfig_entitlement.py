# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autoBanSecurityAlerts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='autobanconfig',
            name='entitlement_token',
            field=models.TextField(blank=True, default='', help_text='Short-lived token from api.newstargeted.com; premium requires phone-home refresh.'),
        ),
        migrations.AddField(
            model_name='autobanconfig',
            name='entitlement_expires_at',
            field=models.PositiveIntegerField(blank=True, help_text='Unix timestamp when entitlement_token expires (from API).', null=True),
        ),
    ]
