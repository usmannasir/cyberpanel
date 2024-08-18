from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^CreatePackage$', views.CreatePackage, name='CreatePackageCL'),
    re_path(r'^listPackages$', views.listPackages, name='listPackagesCL'),
    re_path(r'^monitorUsage$', views.monitorUsage, name='monitorUsage'),
    re_path(r'^CageFS$', views.CageFS, name='CageFS'),
    re_path(r'^submitCageFSInstall$', views.submitCageFSInstall, name='submitCageFSInstall'),

    # re_path(r'^submitWebsiteListing$', views.getFurtherAccounts, name='submitWebsiteListing'),
    # re_path(r'^enableOrDisable$', views.enableOrDisable, name='enableOrDisable'),
    # re_path(r'^submitCreatePackage$', views.submitCreatePackage, name='submitCreatePackageCL'),
    # re_path(r'^fetchPackages$', views.fetchPackages, name='fetchPackagesCL'),
    # re_path(r'^deleteCLPackage$', views.deleteCLPackage, name='deleteCLPackage'),
    # re_path(r'^saveSettings$', views.saveSettings, name='saveSettings'),
    # re_path(r'^manage/(?P<domain>(.*))$', views.websiteContainerLimit, name='websiteContainerLimitCL'),
    # re_path(r'^getUsageData$', views.getUsageData, name='getUsageData'),
]
