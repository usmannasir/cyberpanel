from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadLoginPage, name='adminLogin'),
    path('verifyLogin', views.verifyLogin, name='verifyLogin'),
    path('logout', views.logout, name='logout'),
]
