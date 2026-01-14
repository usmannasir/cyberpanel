# Mindset Laravel Manager - Database Models
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from django.db import models
from django.utils import timezone
from websiteFunctions.models import Websites


class LaravelSite(models.Model):
    """Laravel application configuration and metadata"""

    DEPLOYMENT_STRATEGIES = [
        ('zero-downtime', 'Zero Downtime'),
        ('standard', 'Standard'),
        ('maintenance', 'Maintenance Mode'),
    ]

    PHP_VERSIONS = [
        ('8.1', 'PHP 8.1'),
        ('8.2', 'PHP 8.2'),
        ('8.3', 'PHP 8.3'),
    ]

    OCTANE_SERVERS = [
        ('none', 'Disabled'),
        ('roadrunner', 'RoadRunner'),
        ('swoole', 'Swoole'),
    ]

    # Link to base website
    website = models.OneToOneField(
        Websites,
        on_delete=models.CASCADE,
        related_name='laravel_config'
    )

    # Laravel configuration
    laravel_version = models.CharField(max_length=20, default='12.x')
    php_version = models.CharField(max_length=10, choices=PHP_VERSIONS, default='8.3')

    # Deployment settings
    deployment_strategy = models.CharField(
        max_length=20,
        choices=DEPLOYMENT_STRATEGIES,
        default='zero-downtime'
    )
    keep_releases = models.IntegerField(default=5)
    auto_migrate = models.BooleanField(default=True)
    auto_npm_build = models.BooleanField(default=True)

    # Git settings
    git_repository = models.CharField(max_length=500, null=True, blank=True)
    git_branch = models.CharField(max_length=100, default='main')
    git_deploy_key = models.TextField(null=True, blank=True)

    # Feature flags
    horizon_enabled = models.BooleanField(default=False)
    octane_enabled = models.BooleanField(default=False)
    octane_server = models.CharField(max_length=20, choices=OCTANE_SERVERS, default='none')
    scheduler_enabled = models.BooleanField(default=False)

    # Security
    env_encrypted = models.BooleanField(default=False)

    # Timestamps
    last_deployed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'laravel_sites'
        verbose_name = 'Laravel Site'
        verbose_name_plural = 'Laravel Sites'

    def __str__(self):
        return f"Laravel: {self.website.domain}"

    @property
    def site_path(self):
        """Get the site's filesystem path"""
        return f"/home/{self.website.externalApp}/{self.website.domain}"

    @property
    def current_release_path(self):
        """Get the current active release path"""
        return f"{self.site_path}/current"

    @property
    def shared_path(self):
        """Get the shared resources path"""
        return f"{self.site_path}/shared"


class Deployment(models.Model):
    """Deployment history and logs"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ]

    laravel_site = models.ForeignKey(
        LaravelSite,
        on_delete=models.CASCADE,
        related_name='deployments'
    )

    # Deployment identification
    release_id = models.CharField(max_length=50)  # e.g., 20240115120000

    # Git information
    git_commit = models.CharField(max_length=40, null=True, blank=True)
    git_branch = models.CharField(max_length=100, null=True, blank=True)
    git_message = models.TextField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Logs
    log = models.TextField(null=True, blank=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    triggered_by = models.CharField(max_length=100, default='manual')  # manual, webhook, api
    triggered_by_user = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'laravel_deployments'
        ordering = ['-started_at']
        verbose_name = 'Deployment'
        verbose_name_plural = 'Deployments'

    def __str__(self):
        return f"Deploy {self.release_id} - {self.status}"

    @property
    def duration(self):
        """Get deployment duration in seconds"""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class QueueWorker(models.Model):
    """Queue worker configuration for Horizon/Supervisor"""

    laravel_site = models.ForeignKey(
        LaravelSite,
        on_delete=models.CASCADE,
        related_name='queue_workers'
    )

    # Worker configuration
    name = models.CharField(max_length=100)
    queue = models.CharField(max_length=100, default='default')
    connection = models.CharField(max_length=50, default='redis')

    # Process settings
    processes = models.IntegerField(default=1)
    tries = models.IntegerField(default=3)
    timeout = models.IntegerField(default=60)
    sleep = models.IntegerField(default=3)
    max_jobs = models.IntegerField(default=1000)
    max_time = models.IntegerField(default=3600)

    # Status
    enabled = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'laravel_queue_workers'
        unique_together = ['laravel_site', 'name']
        verbose_name = 'Queue Worker'
        verbose_name_plural = 'Queue Workers'

    def __str__(self):
        return f"{self.name} ({self.laravel_site.website.domain})"


class ScheduledTask(models.Model):
    """Cron/Scheduler task tracking"""

    laravel_site = models.ForeignKey(
        LaravelSite,
        on_delete=models.CASCADE,
        related_name='scheduled_tasks'
    )

    # Task identification
    command = models.CharField(max_length=255)
    expression = models.CharField(max_length=100)  # Cron expression

    # Execution tracking
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=20, null=True, blank=True)
    last_run_output = models.TextField(null=True, blank=True)

    # Status
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'laravel_scheduled_tasks'
        verbose_name = 'Scheduled Task'
        verbose_name_plural = 'Scheduled Tasks'

    def __str__(self):
        return f"{self.command} ({self.expression})"


class EnvironmentVariable(models.Model):
    """Environment variables with optional encryption"""

    laravel_site = models.ForeignKey(
        LaravelSite,
        on_delete=models.CASCADE,
        related_name='env_variables'
    )

    key = models.CharField(max_length=255)
    value = models.TextField()
    encrypted = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'laravel_env_variables'
        unique_together = ['laravel_site', 'key']
        verbose_name = 'Environment Variable'
        verbose_name_plural = 'Environment Variables'

    def __str__(self):
        return f"{self.key}={'*****' if self.encrypted else self.value[:20]}"
