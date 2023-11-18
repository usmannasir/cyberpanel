from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadBackupHome, name='loadBackupHome'),
    url(r'^getCurrentBackups', views.getCurrentBackups, name='getCurrentBackups'),
    url(r'^backupSite', views.backupSite, name='backupSite'),
    url(r'^restoreSite', views.restoreSite, name='restoreSite'),
    url(r'^gDrive$', views.gDrive, name='gDrive'),
    url(r'^gDriveSetup$', views.gDriveSetup, name='gDriveSetup'),
    url(r'^fetchgDriveSites$', views.fetchgDriveSites, name='fetchgDriveSites'),
    url(r'^addSitegDrive$', views.addSitegDrive, name='addSitegDrive'),
    url(r'^deleteAccountgDrive$', views.deleteAccountgDrive, name='deleteAccountgDrive'),
    url(r'^changeAccountFrequencygDrive$', views.changeAccountFrequencygDrive, name='changeAccountFrequencygDrive'),
    url(r'^changeFileRetention$', views.changeFileRetention, name='changeFileRetention'),
    url(r'^deleteSitegDrive$', views.deleteSitegDrive, name='deleteSitegDrive'),
    url(r'^fetchDriveLogs$', views.fetchDriveLogs, name='fetchDriveLogs'),


    url(r'^submitBackupCreation', views.submitBackupCreation, name='submitBackupCreation'),
    url(r'^cancelBackupCreation', views.cancelBackupCreation, name='cancelBackupCreation'),
    url(r'^backupStatus', views.backupStatus, name='backupStatus'),
    url(r'^deleteBackup', views.deleteBackup, name='deleteBackup'),

    url(r'^restoreStatus', views.restoreStatus, name='restoreStatus'),

    url(r'^submitRestore', views.submitRestore, name='submitRestore'),

    url(r'^backupDestinations', views.backupDestinations, name='backupDestinations'),

    url(r'^getCurrentBackupDestinations', views.getCurrentBackupDestinations, name='getCurrentBackupDestinations'),

    url(r'^submitDestinationCreation', views.submitDestinationCreation, name='submitDestinationCreation'),

    url(r'^getConnectionStatus', views.getConnectionStatus, name='getConnectionStatus'),

    url(r'^deleteDestination', views.deleteDestination, name='deleteDestination'),

    url(r'^scheduleBackup', views.scheduleBackup, name='scheduleBackup'),

    url(r'^getCurrentBackupSchedules', views.getCurrentBackupSchedules, name='getCurrentBackupSchedules'),

    url(r'^submitBackupSchedule', views.submitBackupSchedule, name='submitBackupSchedule'),


    url(r'^scheduleDelete', views.scheduleDelete, name='scheduleDelete'),


    url(r'^remoteBackups', views.remoteBackups, name='remoteBackups'),
    url(r'^submitRemoteBackups', views.submitRemoteBackups, name='submitRemoteBackups'),
    url(r'^getRemoteTransferStatus', views.getRemoteTransferStatus, name='getRemoteTransferStatus'),
    url(r'^remoteBackupRestore', views.remoteBackupRestore, name='remoteBackupRestore'),
    url(r'^starRemoteTransfer', views.starRemoteTransfer, name='starRemoteTransfer'),
    url(r'^localRestoreStatus', views.localRestoreStatus, name='localRestoreStatus'),

    url(r'^cancelRemoteBackup', views.cancelRemoteBackup, name='cancelRemoteBackup'),

    url(r'^localInitiate$', views.localInitiate, name='localInitiate'),

    url(r'^backupLogs$', views.backupLogs, name='backupLogs'),
    url(r'^fetchLogs$', views.fetchLogs, name='fetchLogs'),
    url(r'^fetchgNormalSites$', views.fetchgNormalSites, name='fetchgNormalSites'),
    url(r'^fetchNormalJobs$', views.fetchNormalJobs, name='fetchNormalJobs'),
    url(r'^addSiteNormal$', views.addSiteNormal, name='addSiteNormal'),
    url(r'^deleteSiteNormal$', views.deleteSiteNormal, name='deleteSiteNormal'),
    url(r'^changeAccountFrequencyNormal$', views.changeAccountFrequencyNormal, name='changeAccountFrequencyNormal'),
    url(r'^deleteAccountNormal$', views.deleteAccountNormal, name='deleteAccountNormal'),
    url(r'^fetchNormalLogs$', views.fetchNormalLogs, name='fetchNormalLogs'),

]