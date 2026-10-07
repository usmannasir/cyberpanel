# Generated migration for firewall app - BannedIP model
# Primary storage for banned IPs is the database; JSON is used only for export/import.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BannedIP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(db_index=True, unique=True, verbose_name='IP Address')),
                ('reason', models.CharField(max_length=255, verbose_name='Ban Reason')),
                ('duration', models.CharField(default='permanent', max_length=50, verbose_name='Duration')),
                ('banned_on', models.DateTimeField(auto_now_add=True, verbose_name='Banned On')),
                ('expires', models.BigIntegerField(blank=True, null=True, verbose_name='Expires Timestamp')),
                ('active', models.BooleanField(db_index=True, default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Banned IP',
                'verbose_name_plural': 'Banned IPs',
                'db_table': 'firewall_bannedips',
            },
        ),
        migrations.AddIndex(
            model_name='bannedip',
            index=models.Index(fields=['ip_address', 'active'], name='fw_bannedip_ip_active_idx'),
        ),
        migrations.AddIndex(
            model_name='bannedip',
            index=models.Index(fields=['active', 'expires'], name='fw_bannedip_active_exp_idx'),
        ),
    ]
