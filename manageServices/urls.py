from django.conf.urls import url
import views

urlpatterns = [
    url(r'^managePowerDNS$', views.managePowerDNS, name='managePowerDNS'),
    url(r'^fetchStatus$', views.fetchStatus, name='fetchStatus'),
    url(r'^saveStatus$', views.saveStatus, name='saveStatus'),
]