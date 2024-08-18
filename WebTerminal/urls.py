from django.urls import path
from . import views

urlpatterns = [
    path('', views.terminal, name='terminal'),
    path('restart', views.restart, name='restart'),
]
