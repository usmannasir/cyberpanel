from django.urls import path
from . import views

urlpatterns = [
    path('', views.test_plugin_view, name='testPlugin'),
    path('info/', views.plugin_info_view, name='testPluginInfo'),
    path('settings/', views.settings_view, name='testPluginSettings'),
]
