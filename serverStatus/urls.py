from django.urls import path
from . import views

urlpatterns = [
    path('', views.serverStatusHome, name='serverStatusHome'),
    path('litespeedStatus', views.litespeedStatus, name='litespeedStatus'),
    path('startorstopLitespeed', views.stopOrRestartLitespeed, name='startorstopLitespeed'),
    path('cyberCPMainLogFile', views.cyberCPMainLogFile, name='cyberCPMainLogFile'),
    path('getFurtherDataFromLogFile', views.getFurtherDataFromLogFile, name='getFurtherDataFromLogFile'),

    path('servicesStatus', views.servicesStatus, name='servicesStatus'),
    path('servicesAction', views.servicesAction, name='servicesAction'),
    path('services', views.services, name='services'),
    path('switchTOLSWS', views.switchTOLSWS, name='switchTOLSWS'),
    path('switchTOLSWSStatus', views.switchTOLSWSStatus, name='switchTOLSWSStatus'),
    path('licenseStatus', views.licenseStatus, name='licenseStatus'),
    path('changeLicense', views.changeLicense, name='changeLicense'),
    path('refreshLicense', views.refreshLicense, name='refreshLicense'),
    path('topProcesses', views.topProcesses, name='topProcesses'),
    path('topProcessesStatus', views.topProcessesStatus, name='topProcessesStatus'),
    path('killProcess', views.killProcess, name='killProcess'),
    path('packageManager', views.packageManager, name='packageManager'),
    path('fetchPackages', views.fetchPackages, name='fetchPackages'),
    path('fetchPackageDetails', views.fetchPackageDetails, name='fetchPackageDetails'),
    path('updatePackage', views.updatePackage, name='updatePackage'),
    path('lockStatus', views.lockStatus, name='lockStatus'),
    path('CyberPanelPort', views.CyberPanelPort, name='CyberPanelPort'),
    path('submitPortChange', views.submitPortChange, name='submitPortChange'),

    path('Switchoffsecurity', views.Switchoffsecurity, name='Switchoffsecurity'),
    path('securityruleUpdate', views.securityruleUpdate, name='securityruleUpdate'),
]
