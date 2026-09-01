# -*- coding: utf-8 -*-
"""
PluginHolder URL configuration.
Static routes are defined first; then URLs for each installed plugin are
included dynamically so /plugins/<plugin_name>/... (e.g. settings/) works
without hardcoding plugin names in the main CyberCP urls.py.

Discovery order: /usr/local/CyberCP first (installed), then source paths
(/home/cyberpanel/plugins, /home/cyberpanel-plugins) so settings work even
when the plugin is only present in source.
"""
from django.urls import path, include
import os
import sys

# Ensure plugin roots are on sys.path first so __import__(plugin_name + '.urls') can find packages
_INSTALLED_PLUGINS_PATH = '/usr/local/CyberCP'
_PLUGIN_SOURCE_PATHS = ['/home/cyberpanel/plugins', '/home/cyberpanel-plugins']
for _p in [_INSTALLED_PLUGINS_PATH] + _PLUGIN_SOURCE_PATHS:
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from . import views

# Installed plugins live under this path (must match pluginInstaller and pluginHolder.views)
INSTALLED_PLUGINS_PATH = _INSTALLED_PLUGINS_PATH

# Source paths for plugins (same as pluginHolder.views PLUGIN_SOURCE_PATHS)
# Checked when plugin is not under INSTALLED_PLUGINS_PATH so URLs still work
PLUGIN_SOURCE_PATHS = ['/home/cyberpanel/plugins', '/home/cyberpanel-plugins']

# Plugin directory names that must not be routed here (core apps or reserved paths)
RESERVED_PLUGIN_PATHS = frozenset([
    'installed', 'help', 'api',  # pluginHolder's own path segments
    'emailMarketing', 'emailPremium', 'pluginHolder', 'loginSystem', 'baseTemplate',
    'packages', 'websiteFunctions', 'userManagment', 'dns', 'databases', 'ftp',
    'filemanager', 'mailServer', 'cloudAPI', 'containerization', 'IncBackups',
    'CLManager', 's3Backups', 'dockerManager', 'aiScanner', 'firewall', 'tuning',
    'serverStatus', 'serverLogs', 'backup', 'managePHP', 'manageSSL', 'manageServices',
    'highAvailability',
])


def _plugin_has_urls(plugin_dir):
    """Return True if plugin_dir has meta.xml and urls.py."""
    if not os.path.isdir(plugin_dir):
        return False
    return (os.path.exists(os.path.join(plugin_dir, 'meta.xml')) and
            os.path.exists(os.path.join(plugin_dir, 'urls.py')))


def _get_installed_plugin_list():
    """
    Return sorted list of (plugin_name, path_parent) to mount at /plugins/<name>/.
    path_parent is the directory that must be on sys.path to import the plugin
    (e.g. /usr/local/CyberCP or /home/cyberpanel/plugins).
    First discovers from INSTALLED_PLUGINS_PATH, then from PLUGIN_SOURCE_PATHS.
    """
    seen = set()
    result = []  # (name, path_parent)

    # 1) Installed location (canonical)
    if os.path.isdir(INSTALLED_PLUGINS_PATH):
        try:
            for name in os.listdir(INSTALLED_PLUGINS_PATH):
                if name in RESERVED_PLUGIN_PATHS or name.startswith('.'):
                    continue
                plugin_dir = os.path.join(INSTALLED_PLUGINS_PATH, name)
                if _plugin_has_urls(plugin_dir):
                    seen.add(name)
                    result.append((name, INSTALLED_PLUGINS_PATH))
        except (OSError, IOError):
            pass

    # 2) Source paths (fallback so /plugins/PluginName/settings/ works even if not in CyberCP)
    for base in PLUGIN_SOURCE_PATHS:
        if not os.path.isdir(base):
            continue
        try:
            for name in os.listdir(base):
                if name in seen or name in RESERVED_PLUGIN_PATHS or name.startswith('.'):
                    continue
                plugin_dir = os.path.join(base, name)
                if _plugin_has_urls(plugin_dir):
                    seen.add(name)
                    result.append((name, base))
        except (OSError, IOError):
            pass

    return sorted(result, key=lambda x: x[0])


urlpatterns = [
    path('installed', views.installed, name='installed'),
    path('help/', views.help_page, name='help'),
    path('api/install/<str:plugin_name>/', views.install_plugin, name='install_plugin'),
    path('api/uninstall/<str:plugin_name>/', views.uninstall_plugin, name='uninstall_plugin'),
    path(
        'api/delete-source/<str:plugin_name>/',
        views.delete_plugin_source,
        name='delete_plugin_source',
    ),
    path('api/enable/<str:plugin_name>/', views.enable_plugin, name='enable_plugin'),
    path('api/disable/<str:plugin_name>/', views.disable_plugin, name='disable_plugin'),
    path('api/store/plugins/', views.fetch_plugin_store, name='fetch_plugin_store'),
    path('api/store/install/<str:plugin_name>/', views.install_from_store, name='install_from_store'),
    path('api/store/upgrade/<str:plugin_name>/', views.upgrade_plugin, name='upgrade_plugin'),
    path('api/backups/<str:plugin_name>/', views.get_plugin_backups, name='get_plugin_backups'),
    path('api/revert/<str:plugin_name>/', views.revert_plugin, name='revert_plugin'),
    path('api/debug-plugins/', views.debug_loaded_plugins, name='debug_loaded_plugins'),
    path('api/check-subscription/<str:plugin_name>/', views.check_plugin_subscription, name='check_plugin_subscription'),
    path('api/store-activation/<str:plugin_name>/', views.store_plugin_activation_key, name='store_plugin_activation_key'),
    path('<str:plugin_name>/settings/', views.plugin_settings_proxy, name='plugin_settings_proxy'),
    path('<str:plugin_name>/help/', views.plugin_help, name='plugin_help'),
]

# Include each installed plugin's URLs *before* the catch-all so /plugins/<name>/... (other than settings/help) match
_loaded_plugins = []
_failed_plugins = {}
for _plugin_name, _path_parent in _get_installed_plugin_list():
    try:
        if _path_parent not in sys.path:
            sys.path.insert(0, _path_parent)
        __import__(_plugin_name + '.urls')
        urlpatterns.append(path(_plugin_name + '/', include(_plugin_name + '.urls')))
        _loaded_plugins.append(_plugin_name)
    except Exception as e:
        import traceback
        _failed_plugins[_plugin_name] = str(e)
        try:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as _logging
            _logging.writeToFile(
                'pluginHolder.urls: Skipping plugin "%s" (urls not loadable): %s'
                % (_plugin_name, e)
            )
            _logging.writeToFile(traceback.format_exc())
        except Exception:
            pass

urlpatterns.append(path('<str:plugin_name>/help/', views.plugin_help, name='plugin_help'))
