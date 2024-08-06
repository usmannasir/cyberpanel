from django.urls import path
from . import views

urlpatterns = [
    path('installed', views.installed, name='installed'),
]
