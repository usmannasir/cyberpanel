# Generated manually for Fail2ban auto-ban config

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fail2ban', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Fail2banAutoBanConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False)),
                ('permanent', models.BooleanField(default=True)),
                ('check_interval', models.PositiveIntegerField(default=60)),
                ('jail', models.CharField(default='sshd', max_length=64)),
                ('last_run_at', models.DateTimeField(blank=True, null=True)),
                ('last_banned_count', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True, default='')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'fail2ban_autoban_config',
            },
        ),
    ]
