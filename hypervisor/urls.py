from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.loadHVHome, name='loadHVHome'),
    url(r'^createHypervisor$', views.createHypervisor, name='createHypervisor'),
    url(r'^submitCreateHyperVisor$', views.submitCreateHyperVisor, name='submitCreateHyperVisor'),
    url(r'^listHVs$', views.listHVs, name='listHVs'),
    url(r'^submitHyperVisorChanges$', views.submitHyperVisorChanges, name='submitHyperVisorChanges'),
    url(r'^controlCommands$', views.controlCommands, name='controlCommands'),
]

