from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.loadLoginPage, name='adminLogin'),
    path('verifyLogin', views.verifyLogin, name='verifyLogin'),
    path('logout', views.logout, name='logout'),
    path('webauthn/', include('loginSystem.webauthn_urls')),
]
