from django.urls import path

from multiServer import views

# Each view must be wrapped by views.serves(); multiServer/test_wiring.py checks.
urlpatterns = [
    path('nodes', views.nodes_page, name='multiServerNodes'),
    path('nodes/control', views.node_control, name='multiServerNodeControl'),
    path('status', views.status, name='multiServerStatus'),
]
