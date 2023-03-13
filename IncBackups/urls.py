from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^createBackup$', views.create_backup, name='createBackupInc'),
    url(r'^restoreRemoteBackups$', views.restore_remote_backups, name='restoreRemoteBackupsInc'),
    url(r'^backupDestinations$', views.backup_destinations, name='backupDestinationsInc'),
    url(r'^addDestination$', views.add_destination, name='addDestinationInc'),
    url(r'^populateCurrentRecords$', views.populate_current_records, name='populateCurrentRecordsInc'),
    url(r'^removeDestination$', views.remove_destination, name='removeDestinationInc'),
    url(r'^fetchCurrentBackups$', views.fetch_current_backups, name='fetchCurrentBackupsInc'),
    url(r'^submitBackupCreation$', views.submit_backup_creation, name='submitBackupCreationInc'),
    url(r'^getBackupStatus$', views.get_backup_status, name='getBackupStatusInc'),
    url(r'^deleteBackup$', views.delete_backup, name='deleteBackupInc'),
    url(r'^fetchRestorePoints$', views.fetch_restore_points, name='fetchRestorePointsInc'),
    url(r'^restorePoint$', views.restore_point, name='restorePointInc'),
    url(r'^scheduleBackups$', views.schedule_backups, name='scheduleBackupsInc'),
    url(r'^submitBackupSchedule$', views.submit_backup_schedule, name='submitBackupScheduleInc'),
    url(r'^scheduleDelete$', views.schedule_delete, name='scheduleDeleteInc'),
    url(r'^getCurrentBackupSchedules$', views.get_current_backup_schedules, name='getCurrentBackupSchedulesInc'),
    url(r'^fetchSites$', views.fetch_sites, name='fetchSites'),
    url(r'^saveChanges$', views.save_changes, name='saveChanges'),
    url(r'^removeSite$', views.remove_site, name='removeSite'),
    url(r'^addWebsite$', views.add_website, name='addWebsite'),
    ### V2 Backups URls

    url(r'^CreateV2Backup$', views.CreateV2Backup, name='CreateV2Backup'),
    url(r'^ConfigureV2Backup$', views.ConfigureV2Backup, name='ConfigureV2Backup'),
    url(r'^createV2BackupSetup$', views.createV2BackupSetup, name='createV2BackupSetup'),
    url(r'^RestoreV2backupSite$', views.RestoreV2backupSite, name='RestoreV2backupSite'),
    url(r'^selectwebsiteRetorev2$', views.selectwebsiteRetorev2, name='selectwebsiteRetorev2'),
    url(r'^selectreporestorev2$', views.selectreporestorev2, name='selectreporestorev2'),
    url(r'^RestorePathV2$', views.RestorePathV2, name='RestorePathV2'),
    url(r'^CreateV2BackupButton$', views.CreateV2BackupButton, name='CreateV2BackupButton'),

]