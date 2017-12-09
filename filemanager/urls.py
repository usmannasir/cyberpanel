from django.conf.urls import url
import views

urlpatterns = [
    url(r'^(?P<domain>([\da-z\.-]+\.[a-z\.]{2,6}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?)$', views.loadFileManagerHome, name='loadFileManagerHome'),
]

