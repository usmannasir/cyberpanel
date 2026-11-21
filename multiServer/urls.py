from django.urls import path

from multiServer import views

# Each view must be wrapped by views.serves(), except the role page; multiServer/test_wiring.py checks.
urlpatterns = [
    path('login/select', views.select_server, name='msSelect'),
    path('login/arrive', views.arrive, name='msArrive'),
    path('login/return', views.returned, name='msReturn'),
    path('login/finish', views.finish, name='msFinish'),
    path('login/redeem', views.redeem, name='msRedeem'),
    path('nodes', views.nodes_page, name='multiServerNodes'),
    path('nodes/control', views.node_control, name='multiServerNodeControl'),
    path('nodes/add', views.node_add, name='multiServerNodeAdd'),
    path('controllers', views.controllers_page, name='multiServerControllers'),
    path('controllers/control', views.controller_control, name='multiServerControllerControl'),
    path('role', views.role_page, name='multiServerRole'),
    path('inventory/<slug:category>', views.inventory_page, name='multiServerInventory'),
    path('status', views.status, name='multiServerStatus'),
]
