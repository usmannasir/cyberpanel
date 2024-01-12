from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadDatabaseHome, name='loadDatabaseHome'),
    url(r'^createDatabase', views.createDatabase, name='createDatabase'),
    url(r'^V2/createDatabaseV2', views.createDatabaseV2, name='createDatabaseV2'),
    url(r'^submitDBCreation', views.submitDBCreation, name='submitDBCreation'),
    url(r'^deleteDatabase', views.deleteDatabase, name='deleteDatabase'),
    url(r'^V2/deleteDatabaseV2', views.deleteDatabaseV2, name='deleteDatabaseV2'),
    url(r'^fetchDatabases', views.fetchDatabases, name='fetchDatabases'),

    url(r'^submitDatabaseDeletion', views.submitDatabaseDeletion, name='submitDatabaseDeletion'),

    url(r'^listDBs', views.listDBs, name='listDBs'),
    url(r'^V2/listDBsV2', views.listDBsV2, name='listDBsV2'),

    url(r'^changePassword$', views.changePassword, name='changePassword'),
    url(r'^remoteAccess$', views.remoteAccess, name='remoteAccess'),
    url(r'^allowRemoteIP$', views.allowRemoteIP, name='allowRemoteIP'),
    url(r'^phpMyAdmin$', views.phpMyAdmin, name='phpMyAdmin'),
    url(r'^V2/phpMyAdminV2$', views.phpMyAdminV2, name='phpMyAdminV2'),
    url(r'^generateAccess$', views.generateAccess, name='generateAccess'),
    url(r'^fetchDetailsPHPMYAdmin$', views.fetchDetailsPHPMYAdmin, name='fetchDetailsPHPMYAdmin'),
]
