from django.urls import path, re_path
from . import views

app_name = 'premiumPlugin'

urlpatterns = [
    path('', views.main_view, name='main'),
    path('settings/', views.settings_view, name='settings'),
    re_path(r'^activate-key/$', views.activate_key, name='activate_key'),
    path('save-payment-method/', views.save_payment_method, name='save_payment_method'),
    path('api/status/', views.api_status_view, name='api_status'),
]
