from django.db import models
from loginSystem.models import Administrator


class CyberMailAccount(models.Model):
    admin = models.OneToOneField(Administrator, on_delete=models.CASCADE, related_name='cybermail_account')
    platform_account_id = models.IntegerField(null=True)
    api_key = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255)
    plan_name = models.CharField(max_length=100, default='Free')
    plan_slug = models.CharField(max_length=50, default='free')
    emails_per_month = models.IntegerField(default=15000)
    is_connected = models.BooleanField(default=False)
    relay_enabled = models.BooleanField(default=False)
    smtp_credential_id = models.IntegerField(null=True)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_host = models.CharField(max_length=255, default='mail.cyberpersons.com')
    smtp_port = models.IntegerField(default=587)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cybermail_accounts'

    def __str__(self):
        return f"CyberMail Account for {self.admin.userName}"


class CyberMailDomain(models.Model):
    account = models.ForeignKey(CyberMailAccount, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(max_length=255)
    platform_domain_id = models.IntegerField(null=True)
    status = models.CharField(max_length=50, default='pending')
    spf_verified = models.BooleanField(default=False)
    dkim_verified = models.BooleanField(default=False)
    dmarc_verified = models.BooleanField(default=False)
    dns_configured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cybermail_domains'

    def __str__(self):
        return f"CyberMail Domain: {self.domain}"
