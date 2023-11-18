from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.cHome, name='cHome'),
    url(r'^submitContainerInstall$', views.submitContainerInstall, name='submitContainerInstall'),
    url(r'^manage/(?P<domain>(.*))$', views.websiteContainerLimit, name='websiteContainerLimit'),
    url(r'^fetchWebsiteLimits$', views.fetchWebsiteLimits, name='fetchWebsiteLimits'),
    url(r'^saveWebsiteLimits$', views.saveWebsiteLimits, name='saveWebsiteLimits'),
    url(r'^getUsageData$', views.getUsageData, name='getUsageData'),
]