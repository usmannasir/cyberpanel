from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^managePowerDNS$', views.managePowerDNS, name='managePowerDNS'),
    url(r'^managePostfix$', views.managePostfix, name='managePostfix'),
    url(r'^managePureFtpd$', views.managePureFtpd, name='managePureFtpd'),


    url(r'^fetchStatus$', views.fetchStatus, name='fetchStatus'),
    url(r'^saveStatus$', views.saveStatus, name='saveStatus'),

    url(r'^manageApplications$', views.manageApplications, name='manageApplications'),
    url(r'^removeInstall$', views.removeInstall, name='removeInstall'),
]