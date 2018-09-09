"""

CyberTron URL Configuration

"""
from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.listIPHome, name='listIPHome'),
    url(r'^createIPPool$', views.createIPPool, name='createIPPool'),
    url(r'^submitIPPoolCreation$', views.submitIPPoolCreation, name='submitIPPoolCreation'),

    url(r'^listIPPools$', views.listIPPools, name='listIPPools'),
    url(r'^fetchIPsInPool$', views.fetchIPsInPool, name='fetchIPsInPool'),
    url(r'^submitNewMac$', views.submitNewMac, name='submitNewMac'),
    url(r'^deleteIP$', views.deleteIP, name='deleteIP'),
    url(r'^deletePool$', views.deletePool, name='deletePool'),
    url(r'^addSingleIP$', views.addSingleIP, name='addSingleIP'),
    url(r'^addMultipleIP$', views.addMultipleIP, name='addMultipleIP'),


]
