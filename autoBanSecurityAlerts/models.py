# -*- coding: utf-8 -*-
from django.db import models


class AutoBanConfig(models.Model):
    """Configuration for Auto Ban Security Alerts plugin."""
    PAYMENT_METHOD_CHOICES = [
        ('patreon', 'Patreon Subscription'),
        ('paypal', 'PayPal Payment'),
        ('both', 'Check Both (Patreon or PayPal)'),
    ]
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='both',
        help_text="Choose which payment method to use for verification."
    )
    activation_key = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Validated activation key - grants access without re-entering."
    )
    entitlement_token = models.TextField(
        blank=True,
        default='',
        help_text="Short-lived token from api.newstargeted.com; premium requires phone-home refresh."
    )
    entitlement_expires_at = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Unix timestamp when entitlement_token expires (from API)."
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable auto-banning of IPs from Security Alerts."
    )
    ban_duration = models.CharField(
        max_length=20,
        default='permanent',
        choices=[
            ('1h', '1 Hour'),
            ('24h', '24 Hours'),
            ('7d', '7 Days'),
            ('30d', '30 Days'),
            ('permanent', 'Permanent'),
        ],
        help_text="Default ban duration for auto-banned IPs."
    )
    ban_reason = models.CharField(
        max_length=255,
        default='Auto-banned from Security Alerts Detected',
        help_text="Default reason for auto-banned IPs."
    )
    check_interval = models.IntegerField(
        default=60,
        help_text="Check interval in seconds for monitoring Security Alerts (minimum 30 seconds)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Auto Ban Configuration"
        verbose_name_plural = "Auto Ban Configurations"

    def __str__(self):
        return "Auto Ban Security Alerts Configuration"

    @classmethod
    def get_config(cls):
        """Get or create the singleton config instance."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1
        # Ensure minimum check interval
        if self.check_interval < 30:
            self.check_interval = 30
        super().save(*args, **kwargs)


class WhitelistedIP(models.Model):
    """Whitelisted IP addresses that should never be auto-banned."""
    ip_address = models.GenericIPAddressField(
        unique=True,
        help_text="IP address to whitelist."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Optional description for this whitelisted IP."
    )
    is_system_ip = models.BooleanField(
        default=False,
        help_text="System IP (CyberPanel machine IP) - cannot be deleted."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Whitelisted IP"
        verbose_name_plural = "Whitelisted IPs"
        ordering = ['-is_system_ip', 'ip_address']

    def __str__(self):
        return f"{self.ip_address} {'(System IP)' if self.is_system_ip else ''}"


class AutoBanLog(models.Model):
    """Log of auto-banned IPs for tracking and auditing."""
    ip_address = models.GenericIPAddressField(
        help_text="IP address that was auto-banned."
    )
    ban_reason = models.CharField(
        max_length=255,
        help_text="Reason for the ban."
    )
    ban_duration = models.CharField(
        max_length=20,
        help_text="Duration of the ban."
    )
    security_alert_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of security alert that triggered the ban."
    )
    banned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auto Ban Log"
        verbose_name_plural = "Auto Ban Logs"
        ordering = ['-banned_at']
        indexes = [
            models.Index(fields=['-banned_at']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.banned_at}"
