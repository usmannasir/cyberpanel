from django.urls import path
from . import views

urlpatterns = [
    # Site list (landing page)
    path('', views.site_list, name='v2_site_list'),

    # Site-scoped pages
    path('sites/<int:site_id>/', views.site_dashboard, name='v2_site_dashboard'),
    path('sites/<int:site_id>/domains', views.site_domains, name='v2_site_domains'),
    path('sites/<int:site_id>/databases', views.site_databases, name='v2_site_databases'),
    path('sites/<int:site_id>/email', views.site_email, name='v2_site_email'),
    path('sites/<int:site_id>/ftp', views.site_ftp, name='v2_site_ftp'),
    path('sites/<int:site_id>/dns', views.site_dns, name='v2_site_dns'),
    path('sites/<int:site_id>/ssl', views.site_ssl, name='v2_site_ssl'),
    path('sites/<int:site_id>/backup', views.site_backup, name='v2_site_backup'),
    path('sites/<int:site_id>/files', views.site_files, name='v2_site_files'),
    path('sites/<int:site_id>/logs', views.site_logs, name='v2_site_logs'),
    path('sites/<int:site_id>/config', views.site_config, name='v2_site_config'),
    path('sites/<int:site_id>/apps', views.site_apps, name='v2_site_apps'),
    path('sites/<int:site_id>/security', views.site_security, name='v2_site_security'),

    # AJAX API endpoints (site-scoped)
    path('api/sites/<int:site_id>/databases', views.api_databases, name='v2_api_databases'),
    path('api/sites/<int:site_id>/email', views.api_email, name='v2_api_email'),
    path('api/sites/<int:site_id>/ftp', views.api_ftp, name='v2_api_ftp'),
    path('api/sites/<int:site_id>/dns', views.api_dns, name='v2_api_dns'),
    path('api/sites/<int:site_id>/ssl', views.api_ssl, name='v2_api_ssl'),
    path('api/sites/<int:site_id>/backup', views.api_backup, name='v2_api_backup'),
    path('api/sites/<int:site_id>/logs', views.api_logs, name='v2_api_logs'),
    path('api/sites/<int:site_id>/config', views.api_config, name='v2_api_config'),
    path('api/sites/<int:site_id>/domains', views.api_domains, name='v2_api_domains'),
    path('api/sites/<int:site_id>/security', views.api_security, name='v2_api_security'),

    # Server management (admin only)
    path('server/', views.server_management, name='v2_server'),
]
