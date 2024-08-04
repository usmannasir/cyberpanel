from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.loadDatabaseHome, name='loadDatabaseHome'),
    re_path(r'^createDatabase$', views.createDatabase, name='createDatabase'),
    re_path(r'^submitDBCreation$', views.submitDBCreation, name='submitDBCreation'),
    re_path(r'^deleteDatabase$', views.deleteDatabase, name='deleteDatabase'),
    re_path(r'^fetchDatabases$', views.fetchDatabases, name='fetchDatabases'),
    re_path(r'^MysqlManager$', views.MySQLManager, name='MysqlManager'),
    re_path(r'^OptimizeMySQL$', views.OptimizeMySQL, name='OptimizeMySQL'),
    re_path(r'^upgrademysqlnow$', views.upgrademysqlnow, name='upgrademysqlnow'),
    re_path(r'^UpgradeMySQL$', views.UpgradeMySQL, name='UpgradeMySQL'),
    re_path(r'^upgrademysqlstatus$', views.upgrademysqlstatus, name='upgrademysqlstatus'),
    re_path(r'^getMysqlstatus$', views.getMysqlstatus, name='getMysqlstatus'),
    re_path(r'^restartMySQL$', views.restartMySQL, name='restartMySQL'),
    re_path(r'^generateRecommendations$', views.generateRecommendations, name='generateRecommendations'),
    re_path(r'^applyMySQLChanges$', views.applyMySQLChanges, name='applyMySQLChanges'),
    re_path(r'^submitDatabaseDeletion$', views.submitDatabaseDeletion, name='submitDatabaseDeletion'),
    re_path(r'^listDBs$', views.listDBs, name='listDBs'),
    re_path(r'^changePassword$', views.changePassword, name='changePassword'),
    re_path(r'^remoteAccess$', views.remoteAccess, name='remoteAccess'),
    re_path(r'^allowRemoteIP$', views.allowRemoteIP, name='allowRemoteIP'),
    re_path(r'^phpMyAdmin$', views.phpMyAdmin, name='phpMyAdmin'),
    re_path(r'^generateAccess$', views.generateAccess, name='generateAccess'),
    re_path(r'^fetchDetailsPHPMYAdmin$', views.fetchDetailsPHPMYAdmin, name='fetchDetailsPHPMYAdmin'),
]
