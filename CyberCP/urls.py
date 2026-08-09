"""CyberCP URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
"""
import os
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.views.static import serve
from django.views.generic import RedirectView
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def serve_phpmyadmin(request, path):
    """Serve phpMyAdmin files; CSRF exempt so sign-in form POST does not get 403."""
    return serve(request, path, document_root=os.path.join(settings.PUBLIC_ROOT, 'phpmyadmin'))


_imunify_paths = []
try:
    from firewall import views as firewall_views
    if hasattr(firewall_views, 'imunifyAV'):
        _imunify_paths = [
            path('imunifyav/', firewall_views.imunifyAV, name='imunifyav_root'),
            path('ImunifyAV/', firewall_views.imunifyAV, name='imunifyav_root_legacy'),
        ]
except Exception:
    _imunify_paths = []


# STATIC_ROOT / PUBLIC_ROOT routes stay first so /static/, /snappymail/, /phpmyadmin/
# work when the panel is served by Django/lscpd (DEBUG=False).
urlpatterns = [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    re_path(r'^snappymail/?$', RedirectView.as_view(url='/snappymail/index.php', permanent=False)),
    re_path(r'^snappymail/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.PUBLIC_ROOT, 'snappymail')}),
    re_path(r'^phpmyadmin/?$', RedirectView.as_view(url='/phpmyadmin/index.php', permanent=False)),
    re_path(r'^phpmyadmin/(?P<path>.*)$', serve_phpmyadmin),
    path('base/', include('baseTemplate.urls')),
] + _imunify_paths + [
    path('', include('loginSystem.urls')),
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
    path('plugins/', include('pluginHolder.urls')),
    path('emailMarketing/', include('emailMarketing.urls')),
    path('cloudAPI/', include('cloudAPI.urls')),
    path('docker/', include('dockerManager.urls')),
    path('container/', include('containerization.urls')),
    path('CloudLinux/', include('CLManager.urls')),
    path('IncrementalBackups/', include('IncBackups.urls')),
    path('aiscanner/', include('aiScanner.urls')),
    path('webmail/', include('webmail.urls')),
    path('emailDelivery/', include('emailDelivery.urls')),
    # path('Terminal/', include('WebTerminal.urls')),
]
