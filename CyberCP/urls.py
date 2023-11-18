"""CyberCP URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
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
from django.conf.urls import url,include
from django.contrib import admin

urlpatterns = [
    url(r'^base/',include('baseTemplate.urls')),
    url(r'^', include('loginSystem.urls')),
    url(r'^packages/',include('packages.urls')),
    url(r'^websites/',include('websiteFunctions.urls')),
    url(r'^tuning/',include('tuning.urls')),
    url(r'^ftp/',include('ftp.urls')),
    url(r'^serverstatus/',include('serverStatus.urls')),
    url(r'^dns/',include('dns.urls')),
    url(r'^users/',include('userManagment.urls')),
    url(r'^dataBases/',include('databases.urls')),
    url(r'^email/',include('mailServer.urls')),
    url(r'^serverlogs/',include('serverLogs.urls')),
    url(r'^firewall/',include('firewall.urls')),
    url(r'^backup/',include('backup.urls')),
    url(r'^managephp/',include('managePHP.urls')),
    url(r'^manageSSL/',include('manageSSL.urls')),
    url(r'^api/',include('api.urls')),
    url(r'^filemanager/',include('filemanager.urls')),
    url(r'^emailPremium/',include('emailPremium.urls')),
    url(r'^manageservices/',include('manageServices.urls')),
    url(r'^plugins/',include('pluginHolder.urls')),
    url(r'^emailMarketing/', include('emailMarketing.urls')),
    url(r'^cloudAPI/', include('cloudAPI.urls')),
    url(r'^docker/', include('dockerManager.urls')),
    url(r'^container/', include('containerization.urls')),
    url(r'^CloudLinux/', include('CLManager.urls')),
    url(r'^IncrementalBackups/', include('IncBackups.urls')),
    url(r'^Terminal/', include('WebTerminal.urls')),
]
