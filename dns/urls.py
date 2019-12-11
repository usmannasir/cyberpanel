from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadDNSHome, name='dnsHome'),
    url(r'^createNameserver', views.createNameserver, name='createNameserver'),
    url(r'^configureDefaultNameServers$', views.configureDefaultNameServers, name='configureDefaultNameServers'),
    url(r'^createDNSZone', views.createDNSZone, name='createDNSZone'),
    url(r'^addDeleteDNSRecords', views.addDeleteDNSRecords, name='addDeleteDNSRecords'),

    # JS Functions
    url(r'^NSCreation',views.NSCreation,name="NSCreation"),
    url(r'^zoneCreation', views.zoneCreation, name='zoneCreation'),
    url(r'^getCurrentRecordsForDomain',views.getCurrentRecordsForDomain,name='getCurrentRecordsForDomain'),
    url(r'^addDNSRecord',views.addDNSRecord,name='addDNSRecord'),
    url(r'^deleteDNSRecord',views.deleteDNSRecord,name='deleteDNSRecord'),
    url(r'^deleteDNSZone',views.deleteDNSZone,name='deleteDNSZone'),
    url(r'^submitZoneDeletion',views.submitZoneDeletion,name='submitZoneDeletion'),
    url(r'^saveNSConfigurations$', views.saveNSConfigurations, name='saveNSConfigurations'),
]