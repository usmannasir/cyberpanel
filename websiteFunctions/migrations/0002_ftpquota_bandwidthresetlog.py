# Generated migration for FTP Quota and Bandwidth Reset Log models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('websiteFunctions', '0001_initial'),
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FTPQuota',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ftp_user', models.CharField(max_length=255, unique=True)),
                ('quota_size_mb', models.IntegerField(default=0)),
                ('quota_used_mb', models.IntegerField(default=0)),
                ('quota_files', models.IntegerField(default=0)),
                ('quota_files_used', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('domain', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='websiteFunctions.websites')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'FTP Quota',
                'verbose_name_plural': 'FTP Quotas',
                'db_table': 'ftp_quotas',
            },
        ),
        migrations.CreateModel(
            name='BandwidthResetLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reset_type', models.CharField(choices=[('manual', 'Manual Reset'), ('scheduled', 'Scheduled Reset'), ('individual', 'Individual Domain Reset')], max_length=20)),
                ('domains_affected', models.IntegerField(default=0)),
                ('bandwidth_reset_mb', models.BigIntegerField(default=0)),
                ('notes', models.TextField(blank=True, null=True)),
                ('reset_at', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='websiteFunctions.websites')),
                ('reset_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'Bandwidth Reset Log',
                'verbose_name_plural': 'Bandwidth Reset Logs',
                'db_table': 'bandwidth_reset_logs',
                'ordering': ['-reset_at'],
            },
        ),
    ]
