from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.packagesHome, name='packagesHome'),
    url(r'^createPackage$', views.createPacakge, name='createPackage'),
    url(r'^V2/createPackageV2$', views.createPacakgeV2, name='createPackageV2'),
    url(r'^deletePacakge$', views.deletePacakge, name='deletePackage'),
    url(r'^V2/deletePacakgeV2$', views.deletePacakgeV2, name='deletePackageV2'),
    url(r'^modifyPackage$', views.modifyPackage, name='modifyPackage'),
    url(r'^V2/modifyPackageV2$', views.modifyPackageV2, name='modifyPackageV2'),
    url(r'^listPackages$', views.listPackages, name='listPackages'),
    url(r'^V2/listPackagesV2$', views.listPackagesV2, name='listPackagesV2'),
    url(r'^fetchPackagesTable$', views.fetchPackagesTable, name='fetchPackagesTable'),

    # Pacakge Modification URLs

    url(r'^submitPackage', views.submitPackage, name='submitPackage'),
    url(r'^submitDelete', views.submitDelete, name='submitDelete'),
    url(r'^submitModify', views.submitModify, name='submitModify'),
    url(r'^saveChanges', views.saveChanges, name='saveChanges'),

]
