from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^createWebsite$', views.createWebsite, name='createWebsiteAPI'),
    re_path(r'^deleteWebsite$', views.deleteWebsite, name='deleteWebsiteAPI'),
    re_path(r'^submitWebsiteStatus$', views.submitWebsiteStatus, name='submitWebsiteStatusAPI'),
    re_path(r'^deleteFirewallRule$', views.deleteFirewallRule, name='deleteFirewallRule'),
    re_path(r'^addFirewallRule$', views.addFirewallRule, name='addFirewallRule'),

    re_path(r'^verifyConn$', views.verifyConn, name='verifyConnAPI'),

    re_path(r'^loginAPI$', views.loginAPI, name='loginAPI'),

    re_path(r'^getUserInfo$', views.getUserInfo, name='getUserInfo'),
    re_path(r'^changeUserPassAPI$', views.changeUserPassAPI, name='changeUserPassAPI'),
    re_path(r'^submitUserDeletion$', views.submitUserDeletion, name='submitUserDeletion'),


    re_path(r'^listPackage$', views.getPackagesListAPI, name='getPackagesListAPI'),
    re_path(r'^changePackageAPI$', views.changePackageAPI, name='changePackageAPI'),
    re_path(r'^fetchSSHkey$', views.fetchSSHkey, name='fetchSSHkey'),
    re_path(r'^remoteTransfer$', views.remoteTransfer, name='remoteTransfer'),
    re_path(r'^fetchAccountsFromRemoteServer$', views.fetchAccountsFromRemoteServer, name='fetchAccountsFromRemoteServer'),
    re_path(r'^FetchRemoteTransferStatus$', views.FetchRemoteTransferStatus, name='FetchRemoteTransferStatus'),

    re_path(r'^cancelRemoteTransfer$', views.cancelRemoteTransfer, name='cancelRemoteTransfer'),

    re_path(r'^cyberPanelVersion$', views.cyberPanelVersion, name='cyberPanelVersion'),
    re_path(r'^runAWSBackups$', views.runAWSBackups, name='runAWSBackups'),
    re_path(r'^submitUserCreation$', views.submitUserCreation, name='submitUserCreation'),
]
