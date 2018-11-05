from django.conf.urls import url
import views

urlpatterns = [
    url(r'^changePermissions$',views.changePermissions, name='changePermissions'),
    url(r'^downloadFile$',views.downloadFile, name='downloadFile'),
    url(r'^createTemporaryFile$',views.createTemporaryFile, name='createTemporaryFile'),
    url(r'^(?P<domain>(.*))$', views.loadFileManagerHome, name='loadFileManagerHome'),

]

