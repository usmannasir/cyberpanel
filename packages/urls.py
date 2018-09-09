from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.packagesHome, name='packagesHome'),
    url(r'^VMM$', views.packagesHomeVMM, name='packagesHomeVMM'),
    url(r'^createPackage$', views.createPacakge, name='createPackage'),
    url(r'^deletePacakge$', views.deletePacakge, name='deletePackage'),
    url(r'^modifyPackage$', views.modifyPackage, name='modifyPackage'),


    # Pacakge Modification URLs

    url(r'^submitPackage$', views.submitPackage, name='submitPackage'),
    url(r'^submitDelete$', views.submitDelete, name='submitDelete'),
    url(r'^submitModify$', views.submitModify, name='submitModify'),
    url(r'^saveChanges$', views.saveChanges, name='saveChanges'),

    ###

    url(r'^createPackageVMM$', views.createPacakgeVMM, name='createPackageVMM'),
    url(r'^deletePacakgeVMM$', views.deletePacakgeVMM, name='deletePackageVMM'),
    url(r'^modifyPackageVMM$', views.modifyPackageVMM, name='modifyPackageVMM'),


    # Pacakge Modification URLs

    url(r'^submitPackageVMM$', views.submitPackageVMM, name='submitPackageVMM'),
    url(r'^submitDeleteVMM$', views.submitDeleteVMM, name='submitDeleteVMM'),
    url(r'^submitModifyVMM$', views.submitModifyVMM, name='submitModifyVMM'),
    url(r'^saveChangesVMM$', views.saveChangesVMM, name='saveChangesVMM'),


]