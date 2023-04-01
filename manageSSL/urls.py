from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadSSLHome, name='loadSSLHome'),

    url(r'^manageSSL', views.manageSSL, name='manageSSL'),
    url(r'^issueSSL', views.issueSSL, name='issueSSL'),

    url(r'^sslForHostName', views.sslForHostName, name='sslForHostName'),
    url(r'^obtainHostNameSSL$', views.obtainHostNameSSL, name='obtainHostNameSSL'),

    url(r'^sslForMailServer', views.sslForMailServer, name='sslForMailServer'),
    url(r'^obtainMailServerSSL', views.obtainMailServerSSL, name='obtainMailServerSSL'),

    ## v2 functions

    url(r'^v2ManageSSL', views.v2ManageSSL, name='v2ManageSSL'),
    url(r'^v2IssueSSL', views.v2IssueSSL, name='v2IssueSSL'),
]