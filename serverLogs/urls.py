from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.logsHome, name='logsHome'),
    url(r'^accessLogs', views.accessLogs, name='accessLogs'),
    url(r'^errorLogs', views.errorLogs, name='errorLogs'),
    url(r'^emaillogs', views.emailLogs, name='emaillogs'),
    url(r'^ftplogs', views.ftplogs, name='ftplogs'),
    url(r'^modSecAuditLogs', views.modSecAuditLogs, name='modSecAuditLogs'),
    url(r'^getLogsFromFile',views.getLogsFromFile, name="getLogsFromFile"),
    url(r'^clearLogFile',views.clearLogFile, name="clearLogFile"),

]