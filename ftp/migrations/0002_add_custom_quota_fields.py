# Generated migration for FTP custom quota fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ftp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='custom_quota_enabled',
            field=models.BooleanField(default=False, help_text='Enable custom quota for this FTP user'),
        ),
        migrations.AddField(
            model_name='users',
            name='custom_quota_size',
            field=models.IntegerField(default=0, help_text='Custom quota size in MB (0 = use package default)'),
        ),
    ]
