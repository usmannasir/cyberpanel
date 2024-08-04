from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.cHome, name='cHome'),
    re_path(r'^submitContainerInstall$', views.submitContainerInstall, name='submitContainerInstall'),
    re_path(r'^manage/(?P<domain>.*)$', views.websiteContainerLimit, name='websiteContainerLimit'),
    re_path(r'^fetchWebsiteLimits$', views.fetchWebsiteLimits, name='fetchWebsiteLimits'),
    re_path(r'^saveWebsiteLimits$', views.saveWebsiteLimits, name='saveWebsiteLimits'),
    re_path(r'^getUsageData$', views.getUsageData, name='getUsageData'),
]
