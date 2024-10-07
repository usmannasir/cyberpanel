from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.configservercsf, name='configservercsf'),
    path('iframe/', views.configservercsfiframe, name='configservercsfiframe'),
]