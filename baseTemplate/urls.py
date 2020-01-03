from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.renderBase, name='index'),
    url(r'^getSystemStatus$',views.getSystemStatus, name='getSystemInformation'),
    url(r'^getAdminStatus',views.getAdminStatus, name='getSystemInformation'),
    url(r'^getLoadAverage',views.getLoadAverage, name='getLoadAverage'),
    url(r'^versionManagment',views.versionManagment, name='versionManagment'),

    #url(r'^upgrade',views.upgrade, name='upgrade'),

    url(r'^UpgradeStatus',views.upgradeStatus, name='UpgradeStatus'),
    url(r'^upgradeVersion',views.upgradeVersion, name='upgradeVersion'),



]