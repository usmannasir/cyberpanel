from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.serverStatusHome, name='serverStatusHome'),
    url(r'^litespeedStatus', views.litespeedStatus, name='litespeedStatus'),
    url(r'^startorstopLitespeed', views.stopOrRestartLitespeed, name='startorstopLitespeed'),
    url(r'^cyberCPMainLogFile', views.cyberCPMainLogFile, name='cyberCPMainLogFile'),
    url(r'^getFurtherDataFromLogFile',views.getFurtherDataFromLogFile,name='getFurtherDataFromLogFile'),



]