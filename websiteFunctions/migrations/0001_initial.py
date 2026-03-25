# -*- coding: utf-8 -*-
# limitedPhpmyAdmin-websiteFunctions-stub
"""
State-only registration for legacy Websites table (CyberPanel has no prior
django_migrations for websiteFunctions). Allows plugin FKs to resolve without
creating or altering the existing websiteFunctions_websites table.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Websites',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
            ],
            options={
                'db_table': 'websiteFunctions_websites',
                'managed': False,
            },
        ),
    ]
