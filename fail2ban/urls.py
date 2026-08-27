from django.urls import re_path
from . import views
from . import api_views
from . import api_statistics
from . import api_alerts
from . import api_autoban

urlpatterns = [
    re_path(r'^$', views.fail2ban_plugin, name='fail2ban_plugin'),
    re_path(r'^dashboard/$', views.dashboard, name='dashboard_alt'),
    re_path(r'^jails/$', views.jails_standalone, name='jails_standalone'),
    re_path(r'^banned-ips/$', views.banned_ips_standalone, name='banned_ips_standalone'),
    re_path(r'^whitelist/$', views.whitelist_standalone, name='whitelist_standalone'),
    re_path(r'^blacklist/$', views.blacklist_standalone, name='blacklist_standalone'),
    re_path(r'^logs/$', views.logs_standalone, name='logs_standalone'),
    re_path(r'^statistics/$', views.statistics_standalone, name='statistics_standalone'),
    re_path(r'^settings/$', views.settings_standalone, name='settings_standalone'),
    re_path(r'^card/$', views.plugin_card, name='plugin_card'),
    re_path(r'^api/status/$', api_views.api_status, name='api_status'),
    re_path(r'^api/jails/$', api_views.api_jails, name='api_jails'),
    re_path(r'^api/banned-ips/$', api_views.api_banned_ips, name='api_banned_ips'),
    re_path(r'^api/sync-firewall-bans/$', api_views.api_sync_firewall_bans, name='api_sync_firewall_bans'),
    re_path(r'^api/whitelist/$', api_views.api_whitelist, name='api_whitelist'),
    re_path(r'^api/blacklist/$', api_views.api_blacklist, name='api_blacklist'),
    re_path(r'^api/ban-ip/$', api_views.api_ban_ip, name='api_ban_ip'),
    re_path(r'^api/unban-ip/$', api_views.api_unban_ip, name='api_unban_ip'),
    re_path(r'^api/restart/$', api_views.api_restart, name='api_restart'),
    re_path(r'^api/restart-litespeed/$', api_views.api_restart_litespeed, name='api_restart_litespeed'),
    re_path(r'^api/logs/$', api_views.api_logs, name='api_logs'),
    re_path(r'^api/logs/clear/$', api_views.api_logs_clear, name='api_logs_clear'),
    re_path(r'^api/settings/$', api_views.api_settings, name='api_settings'),
    re_path(r'^api/statistics/$', api_statistics.api_statistics, name='api_statistics'),
    re_path(r'^api/toggle-plugin/$', api_views.api_toggle_plugin, name='api_toggle_plugin'),
    re_path(r'^api/ssh-alerts/$', api_alerts.api_ssh_alerts, name='api_ssh_alerts'),
    re_path(r'^api/ban-alert-ips/$', api_alerts.api_ban_alert_ips, name='api_ban_alert_ips'),
    re_path(r'^api/autoban/$', api_autoban.api_autoban_config, name='api_autoban_config'),
    re_path(r'^api/autoban/run-now/$', api_autoban.api_autoban_run_now, name='api_autoban_run_now'),
    re_path(r'^unified/$', views.unified_settings, name='unified_settings'),
]
