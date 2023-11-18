
from django.conf.urls import url
from . import views

urlpatterns = [

    url(r'^installed$', views.installed, name='installed'),
]