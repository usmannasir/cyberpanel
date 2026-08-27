from django.db import models


class Fail2banSettings(models.Model):
    """
    Global fail2ban plugin settings (singleton row pk=1).
    Live DB has no user_id column; keep this aligned with CyberPanel MariaDB.
    """
    email_notifications = models.BooleanField(default=True)
    auto_ban_threshold = models.IntegerField(default=5)
    ban_duration = models.IntegerField(default=3600)  # seconds
    whitelist_ips = models.TextField(default='', blank=True)
    blacklist_ips = models.TextField(default='', blank=True)
    enabled_jails = models.TextField(default='sshd,openlitespeed,cyberpanel', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fail2ban_settings'

    @classmethod
    def get_config(cls):
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'email_notifications': True,
                'auto_ban_threshold': 5,
                'ban_duration': 3600,
                'whitelist_ips': '',
                'blacklist_ips': '',
                'enabled_jails': 'sshd,openlitespeed,cyberpanel',
            },
        )
        return obj


class Fail2banAutoBanConfig(models.Model):
    """
    Global auto-ban settings for dashboard SSH Security Alerts.
    Singleton row (pk=1). When enabled, a background worker bans alert IPs
    via fail2ban + firewall without requiring the Ban All button.
    """
    enabled = models.BooleanField(default=False)
    permanent = models.BooleanField(default=True)
    check_interval = models.PositiveIntegerField(default=60)
    jail = models.CharField(max_length=64, default='sshd')
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_banned_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fail2ban_autoban_config'

    @classmethod
    def get_config(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SecurityEvent(models.Model):
    """Log security events and attacks"""
    EVENT_TYPES = [
        ('ban', 'IP Banned'),
        ('unban', 'IP Unbanned'),
        ('attack', 'Attack Detected'),
        ('whitelist', 'IP Whitelisted'),
        ('blacklist', 'IP Blacklisted'),
    ]

    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    jail_name = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=20, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fail2ban_security_events'
        ordering = ['-created_at']


class BannedIP(models.Model):
    """Track currently banned IPs"""
    ip_address = models.GenericIPAddressField(unique=True)
    jail_name = models.CharField(max_length=100)
    ban_reason = models.TextField(blank=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'fail2ban_banned_ips'
        ordering = ['-banned_at']
