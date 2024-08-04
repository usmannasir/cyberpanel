from django.urls import path, re_path

from . import views
from websiteFunctions.views import Dockersitehome

urlpatterns = [
    re_path(r'^$', views.loadDockerHome, name='dockerHome'),
    # re_path(r'^images$', views.loadImages, name='loadImages'),
    re_path(r'^getTags$', views.getTags, name='getTags'),
    re_path(r'^runContainer$', views.runContainer, name='runContainer'),
    re_path(r'^submitContainerCreation$', views.submitContainerCreation, name='submitContainerCreation'),
    re_path(r'^listContainers$', views.listContainers, name='listContainers'),
    re_path(r'^getContainerList$', views.getContainerList, name='getContainerList'),
    re_path(r'^getContainerLogs$', views.getContainerLogs, name='getContainerLogs'),
    re_path(r'^installImage$', views.installImage, name='installImage'),
    re_path(r'^delContainer$', views.delContainer, name='delContainer'),
    re_path(r'^doContainerAction$', views.doContainerAction, name='doContainerAction'),
    re_path(r'^getContainerStatus$', views.getContainerStatus, name='getContainerStatus'),
    re_path(r'^exportContainer$', views.exportContainer, name='exportContainer'),
    re_path(r'^saveContainerSettings$', views.saveContainerSettings, name='saveContainerSettings'),
    re_path(r'^getContainerTop$', views.getContainerTop, name='getContainerTop'),
    re_path(r'^assignContainer$', views.assignContainer, name='assignContainer'),
    re_path(r'^searchImage$', views.searchImage, name='searchImage'),
    re_path(r'^manageImages$', views.manageImages, name='manageImages'),
    re_path(r'^getImageHistory$', views.getImageHistory, name='getImageHistory'),
    re_path(r'^removeImage$', views.removeImage, name='removeImage'),
    re_path(r'^recreateContainer$', views.recreateContainer, name='recreateContainer'),
    re_path(r'^installDocker$', views.installDocker, name='installDocker'),
    re_path(r'^images$', views.images, name='containerImage'),
    re_path(r'^view/(?P<name>.+)$', views.viewContainer, name='viewContainer'),

    path('manage/<int:dockerapp>/app', Dockersitehome, name='Dockersitehome'),
    path('getDockersiteList', views.getDockersiteList, name='getDockersiteList'),
    path('getContainerAppinfo', views.getContainerAppinfo, name='getContainerAppinfo'),
    path('getContainerApplog', views.getContainerApplog, name='getContainerApplog'),
    path('recreateappcontainer', views.recreateappcontainer, name='recreateappcontainer'),
    path('RestartContainerAPP', views.RestartContainerAPP, name='RestartContainerAPP'),
    path('StopContainerAPP', views.StopContainerAPP, name='StopContainerAPP'),
]
