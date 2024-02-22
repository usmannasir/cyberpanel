from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadSSLHome, name='loadSSLHome'),

    url(r'^manageSSL', views.manageSSL, name='manageSSL'),
    url(r'^V2/manageSSLV2', views.manageSSLV2, name='manageSSLV2'),
    url(r'^issueSSL', views.issueSSL, name='issueSSL'),

    url(r'^sslForHostName', views.sslForHostName, name='sslForHostName'),
    url(r'^V2/sslForHostNameV2', views.sslForHostNameV2, name='sslForHostNameV2'),
    url(r'^obtainHostNameSSL$', views.obtainHostNameSSL, name='obtainHostNameSSL'),

    url(r'^sslForMailServer', views.sslForMailServer, name='sslForMailServer'),
    url(r'^V2/sslForMailServerV2', views.sslForMailServerV2, name='sslForMailServerV2'),
    url(r'^obtainMailServerSSL', views.obtainMailServerSSL, name='obtainMailServerSSL'),

    ## v2 functions

    url(r'^v2ManageSSL', views.v2ManageSSL, name='v2ManageSSL'),
    url(r'^V2/v2ManageSSLV2', views.v2ManageSSLV2, name='v2ManageSSLV2'),
    url(r'^v2IssueSSL', views.v2IssueSSL, name='v2IssueSSL'),
]
