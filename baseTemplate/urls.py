from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.renderBase, name='index'),
    url(r'^getSystemStatus$',views.getSystemStatus, name='getSystemInformation'),
    url(r'^getAdminStatus',views.getAdminStatus, name='getSystemInformation'),
    url(r'^getLoadAverage',views.getLoadAverage, name='getLoadAverage'),
    url(r'^versionManagment',views.versionManagement, name='versionManagment'),
    url(r'^design', views.design, name='design'),
    url(r'^getthemedata', views.getthemedata, name='getthemedata'),

    #url(r'^upgrade',views.upgrade, name='upgrade'),

    url(r'^UpgradeStatus',views.upgradeStatus, name='UpgradeStatus'),
    url(r'^upgradeVersion',views.upgradeVersion, name='upgradeVersion'),

    # Add this URL pattern for 'upgrade_cyberpanel'
    url(r'upgrade_cyberpanel', views.upgrade_cyberpanel, name='upgrade_cyberpanel'),
    url(r'UpgradeStatus', views.upgradeStatus, name='UpgradeStatus'),
    url(r'upgradeVersion', views.upgradeVersion, name='upgradeVersion'),

]