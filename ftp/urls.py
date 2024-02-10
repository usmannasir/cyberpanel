from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadFTPHome, name='loadFTPHome'),
    url(r'^createFTPAccount', views.createFTPAccount, name='createFTPAccount'),
    url(r'^V2/createFTPAccountV2', views.createFTPAccountV2, name='createFTPAccountV2'),
    url(r'^submitFTPCreation', views.submitFTPCreation, name='ftpHome'),

    url(r'^deleteFTPAccount', views.deleteFTPAccount, name='deleteFTPAccount'),
    url(r'^V2/deleteFTPAccountV2', views.deleteFTPAccountV2, name='deleteFTPAccountV2'),

    url(r'^fetchFTPAccounts', views.fetchFTPAccounts, name='fetchFTPAccounts'),
    url(r'^submitFTPDelete', views.submitFTPDelete, name='submitFTPDelete'),

    url(r'^listFTPAccounts', views.listFTPAccounts, name='listFTPAccounts'),
    url(r'^V2/listFTPAccountsV2', views.listFTPAccountsV2, name='listFTPAccountsV2'),

    url(r'^getAllFTPAccounts', views.getAllFTPAccounts, name='getAllFTPAccounts'),

    url(r'^changePassword', views.changePassword, name='changePassword'),
]
