"""filemanager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
import views as fm

urlpatterns = [
    url(r'^$', fm.index),
    url(r'^list', fm.list_),
    url(r'^rename', fm.rename),
    url(r'^move', fm.move),
    url(r'^copy', fm.copy),
    url(r'^remove', fm.remove),
    url(r'^edit', fm.edit),
    url(r'^getContent', fm.getContent),
    url(r'^createFolder', fm.createFolder),
    url(r'^changePermissions', fm.changePermissions),
    url(r'^compress', fm.compress),
    url(r'^extract', fm.extract),
    url(r'^downloadMultiple', fm.downloadMultiple),
    url(r'^download', fm.download),
    url(r'^upload', fm.upload),
]
