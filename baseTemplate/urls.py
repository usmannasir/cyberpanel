from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.renderBase, name='index'),
    re_path(r'^getSystemStatus$', views.getSystemStatus, name='getSystemInformation'),
    re_path(r'^getAdminStatus$', views.getAdminStatus, name='getSystemInformation'),
    re_path(r'^getLoadAverage$', views.getLoadAverage, name='getLoadAverage'),
    re_path(r'^versionManagment$', views.versionManagment, name='versionManagment'),
    re_path(r'^design$', views.design, name='design'),
    re_path(r'^getthemedata$', views.getthemedata, name='getthemedata'),
    re_path(r'^upgrade$', views.upgrade, name='upgrade'),
    re_path(r'^onboarding$', views.onboarding, name='onboarding'),
    re_path(r'^RestartCyberPanel$', views.RestartCyberPanel, name='RestartCyberPanel'),
    re_path(r'^runonboarding$', views.runonboarding, name='runonboarding'),
    re_path(r'^UpgradeStatus$', views.upgradeStatus, name='UpgradeStatus'),
    re_path(r'^upgradeVersion$', views.upgradeVersion, name='upgradeVersion'),
]
