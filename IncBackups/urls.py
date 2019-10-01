from django.conf.urls import url
import views

urlpatterns = [
    url(r'^createBackup$', views.createBackup, name='createBackupInc'),
    url(r'^backupDestinations$', views.backupDestinations, name='backupDestinationsInc'),
    url(r'^addDestination$', views.addDestination, name='addDestinationInc'),
    url(r'^populateCurrentRecords$', views.populateCurrentRecords, name='populateCurrentRecordsInc'),
    url(r'^removeDestination$', views.removeDestination, name='removeDestinationInc'),

]