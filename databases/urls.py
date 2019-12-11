from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadDatabaseHome, name='loadDatabaseHome'),
    url(r'^createDatabase', views.createDatabase, name='createDatabase'),
    url(r'^submitDBCreation', views.submitDBCreation, name='submitDBCreation'),
    url(r'^deleteDatabase', views.deleteDatabase, name='deleteDatabase'),
    url(r'^fetchDatabases', views.fetchDatabases, name='fetchDatabases'),


    url(r'^submitDatabaseDeletion', views.submitDatabaseDeletion, name='submitDatabaseDeletion'),

    url(r'^listDBs', views.listDBs, name='listDBs'),

    url(r'^changePassword', views.changePassword, name='changePassword'),
    url(r'^phpMyAdmin$', views.phpMyAdmin, name='phpMyAdmin'),
    url(r'^setupPHPMYAdminSession$', views.setupPHPMYAdminSession, name='setupPHPMYAdminSession'),
]