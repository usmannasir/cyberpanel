from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.packagesHome, name='packagesHome'),
    url(r'^createPackage$', views.createPacakge, name='createPackage'),
    url(r'^deletePacakge$', views.deletePacakge, name='deletePackage'),
    url(r'^modifyPackage$', views.modifyPackage, name='modifyPackage'),
    url(r'^listPackages$', views.listPackages, name='listPackages'),
    url(r'^fetchPackagesTable$', views.fetchPackagesTable, name='fetchPackagesTable'),

    # Pacakge Modification URLs

    url(r'^submitPackage', views.submitPackage, name='submitPackage'),
    url(r'^submitDelete', views.submitDelete, name='submitDelete'),
    url(r'^submitModify', views.submitModify, name='submitModify'),
    url(r'^saveChanges', views.saveChanges, name='saveChanges'),


]