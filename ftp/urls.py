from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadFTPHome, name='loadFTPHome'),
    path('createFTPAccount', views.createFTPAccount, name='createFTPAccount'),
    path('submitFTPCreation', views.submitFTPCreation, name='ftpHome'),
    path('ResetFTPConfigurations', views.ResetFTPConfigurations, name='ResetFTPConfigurations'),
    path('resetftpnow', views.resetftpnow, name='resetftpnow'),
    path('getresetstatus', views.getresetstatus, name='getresetstatus'),

    path('deleteFTPAccount', views.deleteFTPAccount, name='deleteFTPAccount'),
    path('fetchFTPAccounts', views.fetchFTPAccounts, name='fetchFTPAccounts'),
    path('submitFTPDelete', views.submitFTPDelete, name='submitFTPDelete'),
    path('listFTPAccounts', views.listFTPAccounts, name='listFTPAccounts'),
    path('getAllFTPAccounts', views.getAllFTPAccounts, name='getAllFTPAccounts'),
    path('changePassword', views.changePassword, name='changePassword'),
]
