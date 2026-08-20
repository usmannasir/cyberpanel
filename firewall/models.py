from django.db import models
from django.utils import timezone
from django.utils.timezone import now
import time


# Create your models here.

class FirewallRules(models.Model):
    name = models.CharField(unique=True, max_length=32)  # Field name made lowercase.
    proto = models.CharField(max_length=10)
    port = models.CharField(max_length=25)
    ipAddress = models.CharField(max_length=30,default="0.0.0.0/0")
    # Display / apply order for Firewall Rules table (1 = top). Independent of auto-increment PK.
    sortOrder = models.IntegerField(default=0, db_index=True)


class BannedIP(models.Model):
    """
    Model to store banned IP addresses
    """
    ip_address = models.GenericIPAddressField(unique=True, db_index=True, verbose_name="IP Address")
    reason = models.CharField(max_length=255, verbose_name="Ban Reason")
    duration = models.CharField(max_length=50, default='permanent', verbose_name="Duration")
    banned_on = models.DateTimeField(auto_now_add=True, verbose_name="Banned On")
    expires = models.BigIntegerField(null=True, blank=True, verbose_name="Expires Timestamp")
    # expires can be: null (never expires), or Unix timestamp
    active = models.BooleanField(default=True, db_index=True, verbose_name="Active")
    
    class Meta:
        db_table = 'firewall_bannedips'
        verbose_name = "Banned IP"
        verbose_name_plural = "Banned IPs"
        indexes = [
            models.Index(fields=['ip_address', 'active']),
            models.Index(fields=['active', 'expires']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.reason}"
    
    def is_expired(self):
        """
        Check if the ban has expired
        Returns True if expired, False if still active
        """
        if self.expires is None:
            # Never expires
            return False
        current_time = int(time.time())
        return self.expires <= current_time
    
    def get_expires_display(self):
        """
        Get human-readable expiration date
        """
        if self.expires is None:
            return "Never"
        return timezone.datetime.fromtimestamp(self.expires).strftime('%Y-%m-%d %H:%M:%S')
    
    def get_banned_on_display(self):
        """
        Get human-readable banned on date
        """
        if self.banned_on:
            if hasattr(self.banned_on, 'strftime'):
                return self.banned_on.strftime('%Y-%m-%d %H:%M:%S')
            return str(self.banned_on)
        return timezone.now().strftime('%Y-%m-%d %H:%M:%S')
