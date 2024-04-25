from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.logsHome, name='logsHome'),
    url(r'^V2/accessLogs', views.accessLogs, name='accessLogs'),
    url(r'^accessLogsV2', views.accessLogsV2, name='accessLogsV2'),
    url(r'^V2/errorLogs', views.errorLogs, name='errorLogs'),
    url(r'^errorLogsV2', views.errorLogsV2, name='errorLogsV2'),
    url(r'^emaillogs', views.emailLogs, name='emaillogs'),
    url(r'^V2/emaillogsV2', views.emailLogsV2, name='emaillogsV2'),
    url(r'^ftplogs', views.ftplogs, name='ftplogs'),
    url(r'^V2/ftplogsV2', views.ftplogsV2, name='ftplogsV2'),
    url(r'^modSecAuditLogs', views.modSecAuditLogs, name='modSecAuditLogs'),
    url(r'^V2/modSecAuditLogsV2', views.modSecAuditLogsV2, name='modSecAuditLogsV2'),
    url(r'^getLogsFromFile', views.getLogsFromFile, name="getLogsFromFile"),
    url(r'^clearLogFile', views.clearLogFile, name="clearLogFile"),
    url(r'^serverMail$', views.serverMail, name="serverMail"),
    url(r'^serverMailV2$', views.serverMailV2, name="serverMailV2"),
    url(r'^saveSMTPSettings$', views.saveSMTPSettings, name="saveSMTPSettings"),
]
