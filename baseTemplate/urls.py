from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.renderBase, name='index'),
    path('getSystemStatus', views.getSystemStatus, name='getSystemInformation'),
    path('getAdminStatus', views.getAdminStatus, name='getSystemInformation'),
    path('getLoadAverage', views.getLoadAverage, name='getLoadAverage'),
    path('versionManagment', views.versionManagement, name='versionManagement'),
    path('design', views.design, name='design'),
    path('getthemedata', views.getthemedata, name='getthemedata'),

    # Add this URL pattern for 'upgrade_cyberpanel'
    path('upgrade_cyberpanel', views.upgrade_cyberpanel, name='upgrade_cyberpanel'),

    path('UpgradeStatus', views.upgradeStatus, name='UpgradeStatus'),
    path('upgradeVersion', views.upgradeVersion, name='upgradeVersion'),
]
