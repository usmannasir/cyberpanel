from django.urls import path
from . import views

urlpatterns = [
    path('installed', views.installed, name='installed'),
    path('api/install/<str:plugin_name>/', views.install_plugin, name='install_plugin'),
    path('api/uninstall/<str:plugin_name>/', views.uninstall_plugin, name='uninstall_plugin'),
    path('api/enable/<str:plugin_name>/', views.enable_plugin, name='enable_plugin'),
    path('api/disable/<str:plugin_name>/', views.disable_plugin, name='disable_plugin'),
]
