from django.db import models
from loginSystem.models import Administrator
import json

# Import the status update model
from .status_models import ScanStatusUpdate


class AIScannerSettings(models.Model):
    """Store AI scanner configuration and API keys for administrators"""
    admin = models.OneToOneField(Administrator, on_delete=models.CASCADE, related_name='ai_scanner_settings')
    api_key = models.CharField(max_length=255, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    is_payment_configured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_scanner_settings'

    def __str__(self):
        return f"AI Scanner Settings for {self.admin.userName}"


class ScanHistory(models.Model):
    """Store scan history and results"""
    SCAN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    SCAN_TYPE_CHOICES = [
        ('full', 'Full Scan'),
        ('quick', 'Quick Scan'),
        ('custom', 'Custom Scan'),
    ]

    admin = models.ForeignKey(Administrator, on_delete=models.CASCADE, related_name='scan_history')
    scan_id = models.CharField(max_length=100, unique=True)
    domain = models.CharField(max_length=255)
    scan_type = models.CharField(max_length=20, choices=SCAN_TYPE_CHOICES, default='full')
    status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='pending')
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    files_scanned = models.IntegerField(default=0)
    issues_found = models.IntegerField(default=0)
    findings_json = models.TextField(blank=True, null=True)  # Store JSON findings
    summary_json = models.TextField(blank=True, null=True)  # Store JSON summary
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_scanner_history'
        ordering = ['-started_at']

    def __str__(self):
        return f"Scan {self.scan_id} - {self.domain} ({self.status})"

    @property
    def findings(self):
        """Parse findings JSON"""
        if self.findings_json:
            try:
                return json.loads(self.findings_json)
            except json.JSONDecodeError:
                return []
        return []

    @property
    def summary(self):
        """Parse summary JSON"""
        if self.summary_json:
            try:
                return json.loads(self.summary_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_findings(self, findings_list):
        """Set findings from list/dict"""
        self.findings_json = json.dumps(findings_list)

    def set_summary(self, summary_dict):
        """Set summary from dict"""
        self.summary_json = json.dumps(summary_dict)


class FileAccessToken(models.Model):
    """Temporary tokens for file access during scans"""
    token = models.CharField(max_length=100, unique=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE, related_name='access_tokens')
    domain = models.CharField(max_length=255)
    wp_path = models.CharField(max_length=500)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ai_scanner_file_tokens'

    def __str__(self):
        return f"Access token {self.token} for {self.domain}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class ScheduledScan(models.Model):
    """Store scheduled scan configurations"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    SCAN_TYPE_CHOICES = [
        ('full', 'Full Scan'),
        ('quick', 'Quick Scan'),
        ('custom', 'Custom Scan'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('disabled', 'Disabled'),
    ]
    
    admin = models.ForeignKey(Administrator, on_delete=models.CASCADE, related_name='scheduled_scans')
    name = models.CharField(max_length=200, help_text="Name for this scheduled scan")
    domains = models.TextField(help_text="JSON array of domains to scan")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    scan_type = models.CharField(max_length=20, choices=SCAN_TYPE_CHOICES, default='full')
    time_of_day = models.TimeField(help_text="Time of day to run the scan (UTC)")
    day_of_week = models.IntegerField(null=True, blank=True, help_text="Day of week for weekly scans (0=Monday, 6=Sunday)")
    day_of_month = models.IntegerField(null=True, blank=True, help_text="Day of month for monthly scans (1-31)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    notification_emails = models.TextField(blank=True, help_text="JSON array of email addresses")
    notify_on_threats = models.BooleanField(default=True)
    notify_on_completion = models.BooleanField(default=False)
    notify_on_failure = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ai_scanner_scheduled_scans'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Scheduled Scan: {self.name} ({self.frequency})"
    
    @property
    def domain_list(self):
        """Parse domains JSON"""
        if self.domains:
            try:
                return json.loads(self.domains)
            except json.JSONDecodeError:
                return []
        return []
    
    @property
    def notification_email_list(self):
        """Parse notification emails JSON"""
        if self.notification_emails:
            try:
                return json.loads(self.notification_emails)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_domains(self, domain_list):
        """Set domains from list"""
        self.domains = json.dumps(domain_list)
    
    def set_notification_emails(self, email_list):
        """Set notification emails from list"""
        self.notification_emails = json.dumps(email_list)
    
    def calculate_next_run(self):
        """Calculate next run time based on frequency"""
        from django.utils import timezone
        from datetime import datetime, timedelta
        import calendar
        
        now = timezone.now()
        
        if self.frequency == 'daily':
            # Daily: next run is tomorrow at specified time
            next_run = now.replace(hour=self.time_of_day.hour, minute=self.time_of_day.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.frequency == 'weekly':
            # Weekly: next run is on specified day of week at specified time
            days_ahead = self.day_of_week - now.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=self.time_of_day.hour, minute=self.time_of_day.minute, second=0, microsecond=0)
        
        elif self.frequency == 'monthly':
            # Monthly: next run is on specified day of month at specified time
            year = now.year
            month = now.month
            day = min(self.day_of_month, calendar.monthrange(year, month)[1])
            
            next_run = now.replace(day=day, hour=self.time_of_day.hour, minute=self.time_of_day.minute, second=0, microsecond=0)
            
            if next_run <= now:
                # Move to next month
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                day = min(self.day_of_month, calendar.monthrange(year, month)[1])
                next_run = next_run.replace(year=year, month=month, day=day)
        
        elif self.frequency == 'quarterly':
            # Quarterly: next run is 3 months from now
            next_run = now.replace(hour=self.time_of_day.hour, minute=self.time_of_day.minute, second=0, microsecond=0)
            month = now.month
            year = now.year
            
            # Add 3 months
            month += 3
            if month > 12:
                year += 1
                month -= 12
            
            day = min(self.day_of_month or 1, calendar.monthrange(year, month)[1])
            next_run = next_run.replace(year=year, month=month, day=day)
            
            if next_run <= now:
                # Add another 3 months
                month += 3
                if month > 12:
                    year += 1
                    month -= 12
                day = min(self.day_of_month or 1, calendar.monthrange(year, month)[1])
                next_run = next_run.replace(year=year, month=month, day=day)
        
        else:
            # Default to weekly
            next_run = now + timedelta(weeks=1)
        
        return next_run
    
    def save(self, *args, **kwargs):
        """Override save to calculate next_run"""
        if not self.next_run or self.status == 'active':
            self.next_run = self.calculate_next_run()
        super().save(*args, **kwargs)


class ScheduledScanExecution(models.Model):
    """Track individual executions of scheduled scans"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    scheduled_scan = models.ForeignKey(ScheduledScan, on_delete=models.CASCADE, related_name='executions')
    execution_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    domains_scanned = models.TextField(blank=True, help_text="JSON array of domains that were scanned")
    total_scans = models.IntegerField(default=0)
    successful_scans = models.IntegerField(default=0)
    failed_scans = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    scan_ids = models.TextField(blank=True, help_text="JSON array of scan IDs created")
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_scanner_scheduled_executions'
        ordering = ['-execution_time']

    def __str__(self):
        return f"Execution of {self.scheduled_scan.name} at {self.execution_time}"

    @property
    def scanned_domains(self):
        """Parse domains scanned JSON"""
        if self.domains_scanned:
            try:
                return json.loads(self.domains_scanned)
            except json.JSONDecodeError:
                return []
        return []

    @property
    def scan_id_list(self):
        """Parse scan IDs JSON"""
        if self.scan_ids:
            try:
                return json.loads(self.scan_ids)
            except json.JSONDecodeError:
                return []
        return []

    def set_scanned_domains(self, domain_list):
        """Set scanned domains from list"""
        self.domains_scanned = json.dumps(domain_list)

    def set_scan_ids(self, scan_id_list):
        """Set scan IDs from list"""
        self.scan_ids = json.dumps(scan_id_list)


class ScannerFileOperation(models.Model):
    """Audit log for file operations performed by scanner"""
    OPERATION_CHOICES = [
        ('backup', 'Backup'),
        ('read', 'Read'),
        ('replace', 'Replace'),
        ('rename', 'Rename'),
        ('delete', 'Delete'),
    ]

    scan_id = models.CharField(max_length=255, db_index=True)
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    file_path = models.CharField(max_length=500)
    backup_path = models.CharField(max_length=500, blank=True, null=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'scanner_file_operations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scan_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.operation} - {self.file_path} ({'success' if self.success else 'failed'})"


class ScannerAPIRateLimit(models.Model):
    """Rate limiting for scanner API endpoints"""
    scan_id = models.CharField(max_length=255)
    endpoint = models.CharField(max_length=100)
    request_count = models.IntegerField(default=0)
    last_request_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scanner_api_rate_limits'
        unique_together = ['scan_id', 'endpoint']
        indexes = [
            models.Index(fields=['scan_id', 'endpoint']),
        ]

    def __str__(self):
        return f"{self.scan_id} - {self.endpoint}: {self.request_count} requests"
