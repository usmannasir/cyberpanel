from django.conf.urls import url
import views

urlpatterns = [
    url(r'^createWebsite', views.createWebsite, name='createWebsiteAPI'),
    url(r'^deleteWebsite', views.deleteWebsite, name='deleteWebsiteAPI'),
    url(r'^submitWebsiteStatus', views.submitWebsiteStatus, name='submitWebsiteStatusAPI'),

    url(r'^verifyConn', views.verifyConn, name='verifyConnAPI'),

    url(r'^loginAPI', views.loginAPI, name='loginAPI'),

    url(r'^changeUserPassAPI', views.changeUserPassAPI, name='changeUserPassAPI'),
    url(r'^changePackageAPI', views.changePackageAPI, name='changePackageAPI'),
    url(r'^fetchSSHkey', views.fetchSSHkey, name='fetchSSHkey'),
    url(r'^remoteTransfer', views.remoteTransfer, name='remoteTransfer'),
    url(r'^fetchAccountsFromRemoteServer', views.fetchAccountsFromRemoteServer, name='fetchAccountsFromRemoteServer'),
]