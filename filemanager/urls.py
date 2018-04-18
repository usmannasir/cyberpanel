from django.conf.urls import url
import views

urlpatterns = [
    url(r'^(?P<domain>([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?)$', views.loadFileManagerHome, name='loadFileManagerHome'),
    url(r'^changePermissions',views.changePermissions, name='changePermissions'),
    url(r'^downloadFile',views.downloadFile, name='downloadFile'),
    url(r'^createTemporaryFile',views.createTemporaryFile, name='createTemporaryFile'),

]

