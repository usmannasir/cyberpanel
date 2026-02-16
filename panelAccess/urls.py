# -*- coding: utf-8 -*-
from django.urls import path
from . import views

# Note: app_name removed to avoid namespace issues with dynamic plugin inclusion
# URLs are accessed directly via /plugins/panelAccess/ paths

urlpatterns = [
    path('', views.settings_page, name='panel_access_settings'),
    path('save', views.save_origins, name='panel_access_save'),
    path('domains', views.get_domains_api, name='panel_access_domains'),
]
