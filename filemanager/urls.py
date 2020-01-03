from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^upload$',views.upload, name='upload'),
    url(r'^changePermissions$',views.changePermissions, name='changePermissions'),
    url(r'^controller$',views.controller, name='controller'),
    url(r'^downloadFile$',views.downloadFile, name='downloadFile'),
    url(r'^(?P<domain>(.*))$', views.loadFileManagerHome, name='loadFileManagerHome'),

]

