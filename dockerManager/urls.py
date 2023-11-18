from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadDockerHome, name='dockerHome'),
#     url(r'^images', views.loadImages, name='loadImages'),
    url(r'^getTags', views.getTags, name='getTags'),
    url(r'^runContainer', views.runContainer, name='runContainer'),
    url(r'^submitContainerCreation', views.submitContainerCreation, name='submitContainerCreation'),
    url(r'^listContainers', views.listContainers, name='listContainers'),
    url(r'^getContainerList', views.getContainerList, name='getContainerList'),
    url(r'^getContainerLogs', views.getContainerLogs, name='getContainerLogs'),
    url(r'^installImage', views.installImage, name='installImage'),
    url(r'^delContainer', views.delContainer, name='delContainer'),
    url(r'^doContainerAction', views.doContainerAction, name='doContainerAction'),
    url(r'^getContainerStatus', views.getContainerStatus, name='getContainerStatus'),
    url(r'^exportContainer', views.exportContainer, name='exportContainer'),
    url(r'^saveContainerSettings', views.saveContainerSettings, name='saveContainerSettings'),
    url(r'^getContainerTop', views.getContainerTop, name='getContainerTop'),
    url(r'^assignContainer', views.assignContainer, name='assignContainer'),
    url(r'^searchImage', views.searchImage, name='searchImage'),
    url(r'^manageImages', views.manageImages, name='manageImages'),
    url(r'^getImageHistory', views.getImageHistory, name='getImageHistory'),
    url(r'^removeImage', views.removeImage, name='removeImage'),
    url(r'^recreateContainer', views.recreateContainer, name='recreateContainer'),
    url(r'^installDocker', views.installDocker, name='installDocker'),
    url(r'^images', views.images, name='containerImage'),
    url(r'^view/(?P<name>(.*))$', views.viewContainer, name='viewContainer'),
]