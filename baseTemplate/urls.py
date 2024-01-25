from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.renderBase, name='index'),
    url(r'^getSystemStatus$',views.getSystemStatus, name='getSystemInformation'),
    url(r'^getAdminStatus',views.getAdminStatus, name='getSystemInformation'),
    url(r'^getLoadAverage',views.getLoadAverage, name='getLoadAverage'),
    url(r'^versionManagment',views.versionManagment, name='versionManagment'),
    url(r'^design', views.design, name='design'),
    url(r'^getthemedata', views.getthemedata, name='getthemedata'),

    url(r'^upgrade',views.upgrade, name='upgrade'),
    url(r'^onboarding$', views.onboarding, name='onboarding'),
    url(r'^RestartCyberPanel$', views.RestartCyberPanel, name='RestartCyberPanel'),
    url(r'^runonboarding', views.runonboarding, name='runonboarding'),

    url(r'^UpgradeStatus',views.upgradeStatus, name='UpgradeStatus'),
    url(r'^upgradeVersion',views.upgradeVersion, name='upgradeVersion'),

]