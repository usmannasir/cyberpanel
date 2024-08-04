from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.router, name='router'),
    re_path(r'^access$', views.access, name='access'),
]
