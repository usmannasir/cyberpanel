from django.conf.urls import url
import views
from xterm_django.views import ssh_with_websocket

urlpatterns = [
    url(r'^$', views.loadLoginPage, name='adminLogin'),
    url(r'^verifyLogin$', views.verifyLogin, name='verifyLogin'),
    url(r'^logout$', views.logout, name='logout'),
]