from django.urls import path
from . import views

urlpatterns = [
    path('managePowerDNS', views.managePowerDNS, name='managePowerDNS'),
    path('managePostfix', views.managePostfix, name='managePostfix'),
    path('managePureFtpd', views.managePureFtpd, name='managePureFtpd'),

    path('fetchStatus', views.fetchStatus, name='fetchStatus'),
    path('saveStatus', views.saveStatus, name='saveStatus'),

    path('manageApplications', views.manageApplications, name='manageApplications'),
    path('removeInstall', views.removeInstall, name='removeInstall'),
]
