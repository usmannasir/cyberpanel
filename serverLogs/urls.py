from django.urls import path
from . import views

urlpatterns = [
    path('', views.logsHome, name='logsHome'),
    path('accessLogs', views.accessLogs, name='accessLogs'),
    path('errorLogs', views.errorLogs, name='errorLogs'),
    path('emaillogs', views.emailLogs, name='emaillogs'),
    path('ftplogs', views.ftplogs, name='ftplogs'),
    path('modSecAuditLogs', views.modSecAuditLogs, name='modSecAuditLogs'),
    path('getLogsFromFile', views.getLogsFromFile, name='getLogsFromFile'),
    path('clearLogFile', views.clearLogFile, name='clearLogFile'),
    path('serverMail', views.serverMail, name='serverMail'),
    path('saveSMTPSettings', views.saveSMTPSettings, name='saveSMTPSettings'),
]
