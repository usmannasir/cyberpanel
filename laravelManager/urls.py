# Mindset Laravel Manager - URL Configuration
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from django.urls import path
from . import views

app_name = 'laravelManager'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Site Management
    path('create/', views.create_laravel_site, name='create'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    path('sites/<int:site_id>/settings/', views.site_settings, name='site_settings'),

    # Deployments
    path('sites/<int:site_id>/deploy/', views.deploy, name='deploy'),
    path('sites/<int:site_id>/deployments/', views.deployment_list, name='deployments'),
    path('sites/<int:site_id>/deployments/<int:deploy_id>/', views.deployment_detail, name='deployment_detail'),
    path('sites/<int:site_id>/rollback/', views.rollback, name='rollback'),

    # Artisan
    path('sites/<int:site_id>/artisan/', views.artisan, name='artisan'),
    path('sites/<int:site_id>/artisan/run/', views.run_artisan, name='run_artisan'),
    path('sites/<int:site_id>/tinker/', views.tinker, name='tinker'),

    # Queue Workers / Horizon
    path('sites/<int:site_id>/workers/', views.workers, name='workers'),
    path('sites/<int:site_id>/workers/create/', views.create_worker, name='create_worker'),
    path('sites/<int:site_id>/workers/<int:worker_id>/', views.worker_detail, name='worker_detail'),
    path('sites/<int:site_id>/horizon/', views.horizon, name='horizon'),

    # Scheduler
    path('sites/<int:site_id>/scheduler/', views.scheduler, name='scheduler'),

    # Environment
    path('sites/<int:site_id>/env/', views.env_editor, name='env_editor'),
    path('sites/<int:site_id>/env/update/', views.update_env, name='update_env'),

    # Logs
    path('sites/<int:site_id>/logs/', views.logs, name='logs'),
    path('sites/<int:site_id>/logs/download/', views.download_logs, name='download_logs'),

    # API Endpoints (AJAX)
    path('api/sites/<int:site_id>/status/', views.api_site_status, name='api_site_status'),
    path('api/sites/<int:site_id>/metrics/', views.api_site_metrics, name='api_site_metrics'),

    # Webhooks
    path('webhook/<str:token>/', views.webhook_deploy, name='webhook'),
]
