from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadFTPHome, name='loadFTPHome'),
    url(r'^createFTPAccount', views.createFTPAccount, name='createFTPAccount'),
    url(r'^submitFTPCreation', views.submitFTPCreation, name='ftpHome'),

    url(r'^deleteFTPAccount', views.deleteFTPAccount, name='deleteFTPAccount'),

    url(r'^fetchFTPAccounts', views.fetchFTPAccounts, name='fetchFTPAccounts'),
    url(r'^submitFTPDelete', views.submitFTPDelete, name='submitFTPDelete'),

    url(r'^listFTPAccounts', views.listFTPAccounts, name='listFTPAccounts'),

    url(r'^getAllFTPAccounts', views.getAllFTPAccounts, name='getAllFTPAccounts'),

    url(r'^changePassword', views.changePassword, name='changePassword'),
]

