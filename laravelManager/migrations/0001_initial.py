# Mindset Laravel Manager - Initial Migration
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('websiteFunctions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LaravelSite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('laravel_version', models.CharField(default='12.x', max_length=20)),
                ('php_version', models.CharField(choices=[('8.1', 'PHP 8.1'), ('8.2', 'PHP 8.2'), ('8.3', 'PHP 8.3')], default='8.3', max_length=10)),
                ('deployment_strategy', models.CharField(choices=[('zero-downtime', 'Zero Downtime'), ('standard', 'Standard'), ('maintenance', 'Maintenance Mode')], default='zero-downtime', max_length=20)),
                ('keep_releases', models.IntegerField(default=5)),
                ('auto_migrate', models.BooleanField(default=True)),
                ('auto_npm_build', models.BooleanField(default=True)),
                ('git_repository', models.CharField(blank=True, max_length=500, null=True)),
                ('git_branch', models.CharField(default='main', max_length=100)),
                ('git_deploy_key', models.TextField(blank=True, null=True)),
                ('horizon_enabled', models.BooleanField(default=False)),
                ('octane_enabled', models.BooleanField(default=False)),
                ('octane_server', models.CharField(choices=[('none', 'Disabled'), ('roadrunner', 'RoadRunner'), ('swoole', 'Swoole')], default='none', max_length=20)),
                ('scheduler_enabled', models.BooleanField(default=False)),
                ('env_encrypted', models.BooleanField(default=False)),
                ('last_deployed', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('website', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='laravel_config', to='websiteFunctions.websites')),
            ],
            options={
                'verbose_name': 'Laravel Site',
                'verbose_name_plural': 'Laravel Sites',
                'db_table': 'laravel_sites',
            },
        ),
        migrations.CreateModel(
            name='Deployment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('release_id', models.CharField(max_length=50)),
                ('git_commit', models.CharField(blank=True, max_length=40, null=True)),
                ('git_branch', models.CharField(blank=True, max_length=100, null=True)),
                ('git_message', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('failed', 'Failed'), ('rolled_back', 'Rolled Back')], default='pending', max_length=20)),
                ('log', models.TextField(blank=True, null=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('triggered_by', models.CharField(default='manual', max_length=100)),
                ('triggered_by_user', models.CharField(blank=True, max_length=100, null=True)),
                ('laravel_site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deployments', to='laravelManager.laravelsite')),
            ],
            options={
                'verbose_name': 'Deployment',
                'verbose_name_plural': 'Deployments',
                'db_table': 'laravel_deployments',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='QueueWorker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('queue', models.CharField(default='default', max_length=100)),
                ('connection', models.CharField(default='redis', max_length=50)),
                ('processes', models.IntegerField(default=1)),
                ('tries', models.IntegerField(default=3)),
                ('timeout', models.IntegerField(default=60)),
                ('sleep', models.IntegerField(default=3)),
                ('max_jobs', models.IntegerField(default=1000)),
                ('max_time', models.IntegerField(default=3600)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('laravel_site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queue_workers', to='laravelManager.laravelsite')),
            ],
            options={
                'verbose_name': 'Queue Worker',
                'verbose_name_plural': 'Queue Workers',
                'db_table': 'laravel_queue_workers',
                'unique_together': {('laravel_site', 'name')},
            },
        ),
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.CharField(max_length=255)),
                ('expression', models.CharField(max_length=100)),
                ('last_run_at', models.DateTimeField(blank=True, null=True)),
                ('last_run_status', models.CharField(blank=True, max_length=20, null=True)),
                ('last_run_output', models.TextField(blank=True, null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('laravel_site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_tasks', to='laravelManager.laravelsite')),
            ],
            options={
                'verbose_name': 'Scheduled Task',
                'verbose_name_plural': 'Scheduled Tasks',
                'db_table': 'laravel_scheduled_tasks',
            },
        ),
        migrations.CreateModel(
            name='EnvironmentVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=255)),
                ('value', models.TextField()),
                ('encrypted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('laravel_site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='env_variables', to='laravelManager.laravelsite')),
            ],
            options={
                'verbose_name': 'Environment Variable',
                'verbose_name_plural': 'Environment Variables',
                'db_table': 'laravel_env_variables',
                'unique_together': {('laravel_site', 'key')},
            },
        ),
    ]
