from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadPHPHome, name='loadPHPHome'),
    path('installExtensions', views.installExtensions, name='installExtensions'),
    path('getExtensionsInformation', views.getExtensionsInformation, name='getExtensionsInformation'),
    path('submitExtensionRequest', views.submitExtensionRequest, name='submitExtensionRequest'),
    path('getRequestStatus', views.getRequestStatus, name='getRequestStatus'),
    path('editPHPConfigs', views.editPHPConfigs, name='editPHPConfigs'),
    path('getCurrentPHPConfig', views.getCurrentPHPConfig, name='getCurrentPHPConfig'),
    path('savePHPConfigBasic', views.savePHPConfigBasic, name='savePHPConfigBasic'),
    path('getCurrentAdvancedPHPConfig', views.getCurrentAdvancedPHPConfig, name='getCurrentAdvancedPHPConfig'),
    path('savePHPConfigAdvance', views.savePHPConfigAdvance, name='savePHPConfigAdvance'),
    path('restartPHP', views.restartPHP, name='restartPHP'),
]
