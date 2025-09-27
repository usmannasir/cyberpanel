from django.db import models
from packages.models import Package
from loginSystem.models import Administrator
from datetime import datetime
import time

# Create your models here.

class Websites(models.Model):
    admin = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    domain = models.CharField(max_length=255,unique=True)
    adminEmail = models.CharField(max_length=255)
    phpSelection = models.CharField(max_length=10)
    ssl = models.IntegerField()
    state = models.IntegerField(default=1)
    externalApp = models.CharField(max_length=30, default=None)
    config = models.TextField(default='')
    BackupLock = models.IntegerField(default=0)

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



class ChildDomains(models.Model):
    master = models.ForeignKey(Websites,on_delete=models.CASCADE)
    domain = models.CharField(max_length=50, unique=True)
    path = models.CharField(max_length=200,default=None)
    ssl = models.IntegerField()
    phpSelection = models.CharField(max_length=10,default=None)
    alais = models.IntegerField(default=0)


class Backups(models.Model):
    website = models.ForeignKey(Websites,on_delete=models.CASCADE)
    fileName = models.CharField(max_length=200)
    date = models.CharField(max_length=50)
    size = models.CharField(max_length=50)
    status = models.IntegerField(default=0)

class dest(models.Model):
    destLoc = models.CharField(unique=True,max_length=18)

class backupSchedules(models.Model):
    dest = models.ForeignKey(dest, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=15)

class aliasDomains(models.Model):
    master = models.ForeignKey(Websites, on_delete=models.CASCADE)
    aliasDomain = models.CharField(max_length=75)

class GitLogs(models.Model):
    owner = models.ForeignKey(Websites, on_delete=models.CASCADE)
    date = models.DateTimeField(default=datetime.now, blank=True)
    type = models.CharField(max_length=5)
    message = models.TextField(max_length=65532)

class BackupJob(models.Model):
    logFile = models.CharField(max_length=1000)
    ipAddress = models.CharField(max_length=50)
    port = models.CharField(max_length=15)
    jobSuccessSites = models.IntegerField()
    jobFailedSites = models.IntegerField()
    location = models.IntegerField()

class BackupJobLogs(models.Model):
    owner = models.ForeignKey(BackupJob, on_delete=models.CASCADE)
    status = models.IntegerField()
    message = models.TextField()

class GDrive(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)
    auth = models.TextField(max_length=65532, default='Inactive')
    runTime = models.CharField(max_length=20, default='NEVER')

class GDriveSites(models.Model):
    owner = models.ForeignKey(GDrive, on_delete=models.CASCADE)
    domain = models.CharField(max_length=200)

class GDriveJobLogs(models.Model):
    owner = models.ForeignKey(GDrive, on_delete=models.CASCADE)
    status = models.IntegerField()
    message = models.TextField()


### Normal backup models

class NormalBackupDests(models.Model):
    name = models.CharField(max_length=25)
    config = models.TextField()

class NormalBackupJobs(models.Model):
    owner = models.ForeignKey(NormalBackupDests, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    config = models.TextField()

class NormalBackupSites(models.Model):
    owner = models.ForeignKey(NormalBackupJobs, on_delete=models.CASCADE)
    domain = models.ForeignKey(Websites, on_delete=models.CASCADE)

class NormalBackupJobLogs(models.Model):
    owner = models.ForeignKey(NormalBackupJobs, on_delete=models.CASCADE)
    status = models.IntegerField()
    message = models.TextField()

class wpplugins(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    Name = models.CharField(max_length=255, default='')
    config = models.TextField()

class WPSites(models.Model):
    owner = models.ForeignKey(Websites, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='')
    path = models.CharField(max_length=255, default='')
    FinalURL = models.CharField(max_length=255, default='')
    AutoUpdates = models.CharField(max_length=100, default='Disabled')
    PluginUpdates = models.CharField(max_length=15, default='Disabled')
    ThemeUpdates = models.CharField(max_length=15, default='Disabled')
    date = models.DateTimeField(default=datetime.now)
    WPLockState = models.IntegerField(default=1)

class WPStaging(models.Model):
    owner = models.ForeignKey(WPSites, on_delete=models.CASCADE)
    wpsite = models.ForeignKey(WPSites, on_delete=models.CASCADE, related_name='actual_wpsite')

class WPSitesBackup(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    WPSiteID = models.IntegerField(default=-1)
    WebsiteID = models.IntegerField(default=-1)
    config = models.TextField()

class RemoteBackupConfig(models.Model):
    owner = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    configtype = models.CharField(max_length=255, default='')
    config = models.TextField()

class RemoteBackupSchedule(models.Model):
    RemoteBackupConfig = models.ForeignKey(RemoteBackupConfig, on_delete=models.CASCADE)
    Name = models.CharField(max_length=255, default='')
    timeintervel = models.CharField(max_length=200)
    fileretention = models.CharField(max_length=200)
    lastrun = models.CharField(max_length=200)
    config = models.TextField()

class RemoteBackupsites(models.Model):
    owner = models.ForeignKey(RemoteBackupSchedule, on_delete=models.CASCADE)
    WPsites = models.IntegerField(null=True)
    database = models.IntegerField(null=True)

class Backupsv2(models.Model):
    website = models.ForeignKey(Websites, on_delete=models.CASCADE)
    fileName = models.CharField(max_length=255)
    status = models.IntegerField(default=0)
    timeStamp = models.CharField(max_length=255, default=str(time.time()))
    BasePath = models.TextField(default='')

class BackupsLogsv2(models.Model):
    owner = models.ForeignKey(Backupsv2, on_delete=models.CASCADE)
    timeStamp = models.CharField(max_length=255, default=str(time.time()))
    message = models.TextField(default='')


# Takes
# ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
# port, SitePath, CPUsSite, MemorySite, SiteName
# finalURL, blogTitle, adminUser, adminPassword, adminEmail

### Site Type 0=wp, further tbd later

class DockerSites(models.Model):
    admin = models.ForeignKey(Websites, on_delete=models.CASCADE)
    ComposePath = models.TextField()
    SitePath = models.TextField()
    MySQLPath = models.TextField()
    state = models.IntegerField(default=1)
    SiteType = models.IntegerField(default=0) ## WP, Joomla etc
    MySQLDBName = models.CharField(max_length=100)
    MySQLDBNUser = models.CharField(max_length=100)
    CPUsMySQL = models.CharField(max_length=100)
    MemoryMySQL = models.CharField(max_length=100)
    port = models.CharField(max_length=100)
    CPUsSite = models.CharField(max_length=100)
    MemorySite = models.CharField(max_length=100)
    SiteName = models.CharField(unique=True, max_length=255)
    finalURL = models.TextField()
    blogTitle = models.TextField()
    adminUser = models.CharField(max_length=100)
    adminEmail = models.CharField(max_length=100)

class DockerPackages(models.Model):
    Name = models.CharField(max_length=100, default='')
    CPUs = models.IntegerField()
    Ram = models.IntegerField()
    Bandwidth = models.TextField()
    DiskSpace = models.TextField()
    config = models.TextField()


class PackageAssignment(models.Model):
    user = models.ForeignKey(Administrator, on_delete=models.CASCADE)
    package = models.ForeignKey(DockerPackages, on_delete=models.CASCADE)