from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadSSLHome, name='loadSSLHome'),

    path('manageSSL', views.manageSSL, name='manageSSL'),
    path('issueSSL', views.issueSSL, name='issueSSL'),

    path('sslForHostName', views.sslForHostName, name='sslForHostName'),
    path('obtainHostNameSSL', views.obtainHostNameSSL, name='obtainHostNameSSL'),

    path('sslForMailServer', views.sslForMailServer, name='sslForMailServer'),
    path('obtainMailServerSSL', views.obtainMailServerSSL, name='obtainMailServerSSL'),

    # v2 functions
    path('v2ManageSSL', views.v2ManageSSL, name='v2ManageSSL'),
    path('v2IssueSSL', views.v2IssueSSL, name='v2IssueSSL'),
]
