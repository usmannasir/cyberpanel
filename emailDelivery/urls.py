from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='emailDeliveryHome'),
    path('connect/', views.connect, name='emailDeliveryConnect'),
    path('status/', views.getStatus, name='emailDeliveryStatus'),
    path('disconnect/', views.disconnect, name='emailDeliveryDisconnect'),
    # Domains
    path('domains/add/', views.addDomain, name='emailDeliveryAddDomain'),
    path('domains/list/', views.listDomains, name='emailDeliveryListDomains'),
    path('domains/verify/', views.verifyDomain, name='emailDeliveryVerifyDomain'),
    path('domains/dns-records/', views.getDnsRecords, name='emailDeliveryDnsRecords'),
    path('domains/auto-configure-dns/', views.autoConfigureDns, name='emailDeliveryAutoConfigureDns'),
    path('domains/remove/', views.removeDomain, name='emailDeliveryRemoveDomain'),
    # SMTP Credentials
    path('smtp/create/', views.createSmtpCredential, name='emailDeliverySmtpCreate'),
    path('smtp/list/', views.listSmtpCredentials, name='emailDeliverySmtpList'),
    path('smtp/rotate/', views.rotateSmtpPassword, name='emailDeliverySmtpRotate'),
    path('smtp/delete/', views.deleteSmtpCredential, name='emailDeliverySmtpDelete'),
    # Relay
    path('relay/enable/', views.enableRelay, name='emailDeliveryRelayEnable'),
    path('relay/disable/', views.disableRelay, name='emailDeliveryRelayDisable'),
    # Stats & Logs
    path('stats/', views.getStats, name='emailDeliveryStats'),
    path('stats/domains/', views.getDomainStats, name='emailDeliveryDomainStats'),
    path('logs/', views.getLogs, name='emailDeliveryLogs'),
    # Health
    path('health/', views.checkStatus, name='emailDeliveryHealth'),
]
