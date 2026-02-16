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
import os
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic import RedirectView
from firewall import views as firewall_views

# Plugin routes are no longer hardcoded here; pluginHolder.urls dynamically
# includes each installed plugin (under /plugins/<name>/) so settings and
# other plugin pages work for any installed plugin.

# Optional app: may be missing after clean clone or git clean -fd (not in all repo trees).
# When missing or broken, register a placeholder so {% url 'emailMarketing' %} in templates never raises Reverse not found.
_optional_email_marketing = []
try:
    _optional_email_marketing.append(path('emailMarketing/', include('emailMarketing.urls')))
except (ModuleNotFoundError, ImportError, AttributeError):
    _optional_email_marketing.append(
        path('emailMarketing/', RedirectView.as_view(url='/base/', permanent=False), name='emailMarketing')
    )

urlpatterns = [
    # Serve static files first (before catch-all routes)
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    # Serve SnappyMail and phpMyAdmin from public directory (fixes 404 when panel is served by Django/lscpd on :2087/:8090)
    re_path(r'^snappymail/?$', RedirectView.as_view(url='/snappymail/index.php', permanent=False)),
    re_path(r'^snappymail/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.PUBLIC_ROOT, 'snappymail')}),
    re_path(r'^phpmyadmin/?$', RedirectView.as_view(url='/phpmyadmin/index.php', permanent=False)),
    re_path(r'^phpmyadmin/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.PUBLIC_ROOT, 'phpmyadmin')}),
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
    *_optional_email_marketing,
    path('manageservices/', include('manageServices.urls')),
    path('plugins/', include('pluginHolder.urls')),
    path('cloudAPI/', include('cloudAPI.urls')),
    path('docker/', include('dockerManager.urls')),
    path('container/', include('containerization.urls')),
    path('CloudLinux/', include('CLManager.urls')),
    path('IncrementalBackups/', include('IncBackups.urls')),
    path('aiscanner/', include('aiScanner.urls')),
    # path('Terminal/', include('WebTerminal.urls')),
    path('', include('loginSystem.urls')),
]
