"""CyberCP URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import path, include
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from firewall import views as firewall_views

urlpatterns = [
    # Serve static files first (before catch-all routes)
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    path('base/', include('baseTemplate.urls')),
    path('imunifyav/', firewall_views.imunifyAV, name='imunifyav_root'),
    path('ImunifyAV/', firewall_views.imunifyAV, name='imunifyav_root_legacy'),
    path('packages/', include('packages.urls')),
    path('websites/', include('websiteFunctions.urls')),
    path('tuning/', include('tuning.urls')),
    path('ftp/', include('ftp.urls')),
    path('serverstatus/', include('serverStatus.urls')),
    path('dns/', include('dns.urls')),
    path('users/', include('userManagment.urls')),
    path('dataBases/', include('databases.urls')),
    path('email/', include('mailServer.urls')),
    path('serverlogs/', include('serverLogs.urls')),
    path('firewall/', include('firewall.urls')),
    path('backup/', include('backup.urls')),
    path('managephp/', include('managePHP.urls')),
    path('manageSSL/', include('manageSSL.urls')),
    path('api/', include('api.urls')),
    path('filemanager/', include('filemanager.urls')),
    path('emailPremium/', include('emailPremium.urls')),
    path('manageservices/', include('manageServices.urls')),
    path('plugins/pm2Manager/',include('pm2Manager.urls')),
    path('plugins/paypalPremiumPlugin/', include('paypalPremiumPlugin.urls')),
    path('plugins/examplePlugin/', include('examplePlugin.urls')),
    path('plugins/premiumPlugin/',include('premiumPlugin.urls')),
    path('plugins/testPlugin/',include('testPlugin.urls')),
    path('plugins/', include('pluginHolder.urls')),
    path('emailMarketing/', include('emailMarketing.urls')),
    path('cloudAPI/', include('cloudAPI.urls')),
    path('docker/', include('dockerManager.urls')),
    path('container/', include('containerization.urls')),
    path('CloudLinux/', include('CLManager.urls')),
    path('IncrementalBackups/', include('IncBackups.urls')),
    path('aiscanner/', include('aiScanner.urls')),
    # path('Terminal/', include('WebTerminal.urls')),
    path('', include('loginSystem.urls')),
]
