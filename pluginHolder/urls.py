from django.urls import path
from . import views

urlpatterns = [
    path('installed', views.installed, name='installed'),
    path('help/', views.help_page, name='help'),
    path('api/install/<str:plugin_name>/', views.install_plugin, name='install_plugin'),
    path('api/uninstall/<str:plugin_name>/', views.uninstall_plugin, name='uninstall_plugin'),
    path('api/enable/<str:plugin_name>/', views.enable_plugin, name='enable_plugin'),
    path('api/disable/<str:plugin_name>/', views.disable_plugin, name='disable_plugin'),
    path('api/store/plugins/', views.fetch_plugin_store, name='fetch_plugin_store'),
    path('api/store/install/<str:plugin_name>/', views.install_from_store, name='install_from_store'),
    path('api/store/upgrade/<str:plugin_name>/', views.upgrade_plugin, name='upgrade_plugin'),
    path('api/backups/<str:plugin_name>/', views.get_plugin_backups, name='get_plugin_backups'),
    path('api/revert/<str:plugin_name>/', views.revert_plugin, name='revert_plugin'),
    path('<str:plugin_name>/help/', views.plugin_help, name='plugin_help'),
]
