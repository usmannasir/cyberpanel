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
]