from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.loadDNSHome, name='dnsHome'),
    re_path(r'^createNameserver$', views.createNameserver, name='createNameserver'),
    re_path(r'^configureDefaultNameServers$', views.configureDefaultNameServers, name='configureDefaultNameServers'),
    re_path(r'^createDNSZone$', views.createDNSZone, name='createDNSZone'),
    re_path(r'^addDeleteDNSRecords$', views.addDeleteDNSRecords, name='addDeleteDNSRecords'),
    re_path(r'^addDeleteDNSRecordsCloudFlare$', views.addDeleteDNSRecordsCloudFlare, name='addDeleteDNSRecordsCloudFlare'),
    re_path(r'^ResetDNSConfigurations$', views.ResetDNSConfigurations, name='ResetDNSConfigurations'),
    re_path(r'^resetDNSnow$', views.resetDNSnow, name='resetDNSnow'),
    re_path(r'^getresetstatus$', views.getresetstatus, name='getresetstatus'),

    # JS Functions
    re_path(r'^NSCreation$', views.NSCreation, name='NSCreation'),
    re_path(r'^zoneCreation$', views.zoneCreation, name='zoneCreation'),
    re_path(r'^getCurrentRecordsForDomain$', views.getCurrentRecordsForDomain, name='getCurrentRecordsForDomain'),
    re_path(r'^addDNSRecord$', views.addDNSRecord, name='addDNSRecord'),
    re_path(r'^deleteDNSRecord$', views.deleteDNSRecord, name='deleteDNSRecord'),
    re_path(r'^deleteDNSZone$', views.deleteDNSZone, name='deleteDNSZone'),
    re_path(r'^submitZoneDeletion$', views.submitZoneDeletion, name='submitZoneDeletion'),
    re_path(r'^saveNSConfigurations$', views.saveNSConfigurations, name='saveNSConfigurations'),
    re_path(r'^saveCFConfigs$', views.saveCFConfigs, name='saveCFConfigs'),
    re_path(r'^updateRecord$', views.updateRecord, name='updateRecord'),

    re_path(r'^getCurrentRecordsForDomainCloudFlare$', views.getCurrentRecordsForDomainCloudFlare, name='getCurrentRecordsForDomainCloudFlare'),
    re_path(r'^deleteDNSRecordCloudFlare$', views.deleteDNSRecordCloudFlare, name='deleteDNSRecordCloudFlare'),
    re_path(r'^addDNSRecordCloudFlare$', views.addDNSRecordCloudFlare, name='addDNSRecordCloudFlare'),
    re_path(r'^syncCF$', views.syncCF, name='syncCF'),
    re_path(r'^enableProxy$', views.enableProxy, name='enableProxy'),
]
