from django.urls import path
from . import views, views_api

urlpatterns = [
    path('', views.dashboard, name='port_manager_dashboard'),
    path('api/keys/create', views.create_api_key, name='port_manager_key_create'),
    path('api/keys/revoke', views.revoke_api_key, name='port_manager_key_revoke'),
    path('api/v1/ports', views_api.list_ports_api, name='port_manager_api_ports'),
    path('api/v1/docker', views_api.docker_ports_api, name='port_manager_api_docker'),
    path('api/v1/firewall/open', views_api.firewall_open_api, name='port_manager_api_fw_open'),
    path('api/v1/process/stop', views_api.process_stop_api, name='port_manager_api_stop'),
    path('api/v1/audit', views_api.audit_api, name='port_manager_api_audit'),
]
