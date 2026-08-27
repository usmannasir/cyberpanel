# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'autoBanSecurityAlerts'

urlpatterns = [
    path('', views.main_view, name='main'),
    path('settings/', views.settings_view, name='settings'),
    path('export_firewall_json/', views.export_auto_bans_firewall_json, name='export_firewall_json'),
    path('recent_bans_fragment/', views.recent_bans_fragment, name='recent_bans_fragment'),
    path('update_config/', views.update_config, name='update_config'),
    path('add_whitelist_ip/', views.add_whitelist_ip, name='add_whitelist_ip'),
    path('remove_whitelist_ip/', views.remove_whitelist_ip, name='remove_whitelist_ip'),
    path('remove_auto_ban/', views.remove_auto_ban, name='remove_auto_ban'),
    path('activate_key/', views.activate_key, name='activate_key'),
]
