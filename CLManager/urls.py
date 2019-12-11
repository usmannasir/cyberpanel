from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^CageFS$', views.CageFS, name='CageFS'),
    url(r'^submitCageFSInstall$', views.submitCageFSInstall, name='submitCageFSInstall'),
    url(r'^submitWebsiteListing$', views.getFurtherAccounts, name='submitWebsiteListing'),
    url(r'^enableOrDisable$', views.enableOrDisable, name='enableOrDisable'),
    url(r'^CreatePackage$', views.CreatePackage, name='CreatePackageCL'),
    url(r'^submitCreatePackage$', views.submitCreatePackage, name='submitCreatePackageCL'),
    url(r'^listPackages$', views.listPackages, name='listPackagesCL'),
    url(r'^fetchPackages$', views.fetchPackages, name='fetchPackagesCL'),
    url(r'^deleteCLPackage$', views.deleteCLPackage, name='deleteCLPackage'),
    url(r'^saveSettings$', views.saveSettings, name='saveSettings'),
    url(r'^monitorUsage$', views.monitorUsage, name='monitorUsage'),
    url(r'^manage/(?P<domain>(.*))$', views.websiteContainerLimit, name='websiteContainerLimitCL'),
    url(r'^getUsageData$', views.getUsageData, name='getUsageData'),
]