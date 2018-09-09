from django.conf.urls import url
import views

urlpatterns = [

    url(r'^$', views.vpsHome, name='vpsHome'),
    url(r'^createVPS$', views.createVPS, name='createVPS'),
    url(r'^submitVPSCreation$', views.submitVPSCreation, name='submitVPSCreation'),
    url(r'^listVPSs$', views.listVPSs, name='listVPSs'),
    url(r'^fetchVPS$', views.fetchVPS, name='fetchVPS'),
    url(r'^deleteVPS$', views.deleteVPS, name='deleteVPS'),
    url(r'^restartVPS$', views.restartVPS, name='restartVPS'),
    url(r'^shutdownVPS$', views.shutdownVPS, name='shutdownVPS'),

    url(r'^getVPSDetails$', views.getVPSDetails, name='getVPSDetails'),
    url(r'^changeHostname$', views.changeHostname, name='changeHostname'),
    url(r'^changeRootPassword$', views.changeRootPassword, name='changeRootPassword'),
    url(r'^reInstallOS$', views.reInstallOS, name='reInstallOS'),

    ##

    url(r'^sshKeys$', views.sshKeys, name='sshKeys'),
    url(r'^addKey$', views.addKey, name='addKey'),
    url(r'^fetchKeys$', views.fetchKeys, name='fetchKeys'),
    url(r'^deleteKey$', views.deleteKey, name='deleteKey'),
    url(r'^findIPs$', views.findIPs, name='findIPs'),
    url(r'^startWebsocketServer$', views.startWebsocketServer, name='startWebsocketServer'),

    ##

    url(r'^(?P<hostName>(.*))$', views.manageVPS, name='manageVPS'),




]