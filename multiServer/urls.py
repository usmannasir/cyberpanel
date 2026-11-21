from django.urls import path

from multiServer import views

# Each view must be wrapped by views.serves(); multiServer/test_wiring.py checks.
urlpatterns = [
    path('status', views.status, name='multiServerStatus'),
]
