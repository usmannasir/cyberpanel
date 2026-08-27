# -*- coding: utf-8 -*-
# Generated manually for Auto Ban Security Alerts Plugin

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AutoBanConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(choices=[('patreon', 'Patreon Subscription'), ('paypal', 'PayPal Payment'), ('both', 'Check Both (Patreon or PayPal)')], default='both', help_text='Choose which payment method to use for verification.', max_length=10)),
                ('activation_key', models.CharField(blank=True, default='', help_text='Validated activation key - grants access without re-entering.', max_length=64)),
                ('enabled', models.BooleanField(default=True, help_text='Enable/disable auto-banning of IPs from Security Alerts.')),
                ('ban_duration', models.CharField(choices=[('1h', '1 Hour'), ('24h', '24 Hours'), ('7d', '7 Days'), ('30d', '30 Days'), ('permanent', 'Permanent')], default='permanent', help_text='Default ban duration for auto-banned IPs.', max_length=20)),
                ('ban_reason', models.CharField(default='Auto-banned from Security Alerts Detected', help_text='Default reason for auto-banned IPs.', max_length=255)),
                ('check_interval', models.IntegerField(default=60, help_text='Check interval in seconds for monitoring Security Alerts (minimum 30 seconds).')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Auto Ban Configuration',
                'verbose_name_plural': 'Auto Ban Configurations',
            },
        ),
        migrations.CreateModel(
            name='AutoBanLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(help_text='IP address that was auto-banned.')),
                ('ban_reason', models.CharField(help_text='Reason for the ban.', max_length=255)),
                ('ban_duration', models.CharField(help_text='Duration of the ban.', max_length=20)),
                ('security_alert_type', models.CharField(blank=True, help_text='Type of security alert that triggered the ban.', max_length=100)),
                ('banned_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Auto Ban Log',
                'verbose_name_plural': 'Auto Ban Logs',
                'ordering': ['-banned_at'],
            },
        ),
        migrations.CreateModel(
            name='WhitelistedIP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(help_text='IP address to whitelist.', unique=True)),
                ('description', models.CharField(blank=True, default='', help_text='Optional description for this whitelisted IP.', max_length=255)),
                ('is_system_ip', models.BooleanField(default=False, help_text='System IP (CyberPanel machine IP) - cannot be deleted.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Whitelisted IP',
                'verbose_name_plural': 'Whitelisted IPs',
                'ordering': ['-is_system_ip', 'ip_address'],
            },
        ),
        migrations.AddIndex(
            model_name='autobanlog',
            index=models.Index(fields=['-banned_at'], name='autoBanSec_banned__idx'),
        ),
        migrations.AddIndex(
            model_name='autobanlog',
            index=models.Index(fields=['ip_address'], name='autoBanSec_ip_addr_idx'),
        ),
    ]
