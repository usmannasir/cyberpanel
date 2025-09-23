# Add FTP quota models to existing models.py

# Add these models to the existing file
class FTPQuota(models.Model):
    """
    FTP User Quota Management
    """
    user = models.ForeignKey('loginSystem.Administrator', on_delete=models.CASCADE)
    ftp_user = models.CharField(max_length=255, unique=True)
    domain = models.ForeignKey(Websites, on_delete=models.CASCADE, null=True, blank=True)
    quota_size_mb = models.IntegerField(default=0)  # 0 = unlimited
    quota_used_mb = models.IntegerField(default=0)
    quota_files = models.IntegerField(default=0)  # 0 = unlimited
    quota_files_used = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ftp_quotas'
        verbose_name = 'FTP Quota'
        verbose_name_plural = 'FTP Quotas'
    
    def __str__(self):
        return f"{self.ftp_user} - {self.quota_size_mb}MB"
    
    def get_quota_percentage(self):
        """Calculate quota usage percentage"""
        if self.quota_size_mb == 0:
            return 0
        return (self.quota_used_mb / self.quota_size_mb) * 100
    
    def is_quota_exceeded(self):
        """Check if quota is exceeded"""
        if self.quota_size_mb == 0:
            return False
        return self.quota_used_mb >= self.quota_size_mb

class BandwidthResetLog(models.Model):
    """
    Bandwidth Reset Log
    """
    RESET_TYPES = [
        ('manual', 'Manual Reset'),
        ('scheduled', 'Scheduled Reset'),
        ('individual', 'Individual Domain Reset'),
    ]
    
    reset_type = models.CharField(max_length=20, choices=RESET_TYPES)
    domain = models.ForeignKey(Websites, on_delete=models.CASCADE, null=True, blank=True)
    reset_by = models.ForeignKey('loginSystem.Administrator', on_delete=models.CASCADE)
    reset_at = models.DateTimeField(auto_now_add=True)
    domains_affected = models.IntegerField(default=0)
    bandwidth_reset_mb = models.BigIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'bandwidth_reset_logs'
        verbose_name = 'Bandwidth Reset Log'
        verbose_name_plural = 'Bandwidth Reset Logs'
        ordering = ['-reset_at']
    
    def __str__(self):
        return f"{self.reset_type} - {self.domain or 'All Domains'} - {self.reset_at}"