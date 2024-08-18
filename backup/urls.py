from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.loadBackupHome, name='loadBackupHome'),
    re_path(r'^getCurrentBackups$', views.getCurrentBackups, name='getCurrentBackups'),
    re_path(r'^OneClickBackups$', views.OneClickBackups, name='OneClickBackups'),
    re_path(r'^ManageOCBackups$', views.ManageOCBackups, name='ManageOCBackups'),
    re_path(r'^RestoreOCBackups$', views.RestoreOCBackups, name='RestoreOCBackups'),
    re_path(r'^fetchOCSites$', views.fetchOCSites, name='fetchOCSites'),
    re_path(r'^StartOCRestore$', views.StartOCRestore, name='StartOCRestore'),
    re_path(r'^DeployAccount$', views.DeployAccount, name='DeployAccount'),

    re_path(r'^backupSite$', views.backupSite, name='backupSite'),
    re_path(r'^restoreSite$', views.restoreSite, name='restoreSite'),
    re_path(r'^gDrive$', views.gDrive, name='gDrive'),
    re_path(r'^gDriveSetup$', views.gDriveSetup, name='gDriveSetup'),
    re_path(r'^fetchgDriveSites$', views.fetchgDriveSites, name='fetchgDriveSites'),
    re_path(r'^addSitegDrive$', views.addSitegDrive, name='addSitegDrive'),
    re_path(r'^deleteAccountgDrive$', views.deleteAccountgDrive, name='deleteAccountgDrive'),
    re_path(r'^changeAccountFrequencygDrive$', views.changeAccountFrequencygDrive, name='changeAccountFrequencygDrive'),
    re_path(r'^changeFileRetention$', views.changeFileRetention, name='changeFileRetention'),
    re_path(r'^deleteSitegDrive$', views.deleteSitegDrive, name='deleteSitegDrive'),
    re_path(r'^fetchDriveLogs$', views.fetchDriveLogs, name='fetchDriveLogs'),

    re_path(r'^submitBackupCreation$', views.submitBackupCreation, name='submitBackupCreation'),
    re_path(r'^cancelBackupCreation$', views.cancelBackupCreation, name='cancelBackupCreation'),
    re_path(r'^backupStatus$', views.backupStatus, name='backupStatus'),
    re_path(r'^deleteBackup$', views.deleteBackup, name='deleteBackup'),

    re_path(r'^restoreStatus$', views.restoreStatus, name='restoreStatus'),

    re_path(r'^submitRestore$', views.submitRestore, name='submitRestore'),

    re_path(r'^backupDestinations$', views.backupDestinations, name='backupDestinations'),

    re_path(r'^getCurrentBackupDestinations$', views.getCurrentBackupDestinations, name='getCurrentBackupDestinations'),

    re_path(r'^submitDestinationCreation$', views.submitDestinationCreation, name='submitDestinationCreation'),

    re_path(r'^getConnectionStatus$', views.getConnectionStatus, name='getConnectionStatus'),

    re_path(r'^deleteDestination$', views.deleteDestination, name='deleteDestination'),

    re_path(r'^scheduleBackup$', views.scheduleBackup, name='scheduleBackup'),

    re_path(r'^getCurrentBackupSchedules$', views.getCurrentBackupSchedules, name='getCurrentBackupSchedules'),

    re_path(r'^submitBackupSchedule$', views.submitBackupSchedule, name='submitBackupSchedule'),

    re_path(r'^scheduleDelete$', views.scheduleDelete, name='scheduleDelete'),

    re_path(r'^remoteBackups$', views.remoteBackups, name='remoteBackups'),
    re_path(r'^submitRemoteBackups$', views.submitRemoteBackups, name='submitRemoteBackups'),
    re_path(r'^getRemoteTransferStatus$', views.getRemoteTransferStatus, name='getRemoteTransferStatus'),
    re_path(r'^remoteBackupRestore$', views.remoteBackupRestore, name='remoteBackupRestore'),
    re_path(r'^starRemoteTransfer$', views.starRemoteTransfer, name='starRemoteTransfer'),
    re_path(r'^localRestoreStatus$', views.localRestoreStatus, name='localRestoreStatus'),

    re_path(r'^cancelRemoteBackup$', views.cancelRemoteBackup, name='cancelRemoteBackup'),

    re_path(r'^localInitiate$', views.localInitiate, name='localInitiate'),

    re_path(r'^backupLogs$', views.backupLogs, name='backupLogs'),
    re_path(r'^fetchLogs$', views.fetchLogs, name='fetchLogs'),
    re_path(r'^fetchgNormalSites$', views.fetchgNormalSites, name='fetchgNormalSites'),
    re_path(r'^fetchNormalJobs$', views.fetchNormalJobs, name='fetchNormalJobs'),
    re_path(r'^addSiteNormal$', views.addSiteNormal, name='addSiteNormal'),
    re_path(r'^deleteSiteNormal$', views.deleteSiteNormal, name='deleteSiteNormal'),
    re_path(r'^changeAccountFrequencyNormal$', views.changeAccountFrequencyNormal, name='changeAccountFrequencyNormal'),
    re_path(r'^deleteAccountNormal$', views.deleteAccountNormal, name='deleteAccountNormal'),
    re_path(r'^fetchNormalLogs$', views.fetchNormalLogs, name='fetchNormalLogs'),
]
