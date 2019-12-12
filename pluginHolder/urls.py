
from django.conf.urls import url
import views

urlpatterns = [

    url(r'^installed$', views.installed, name='installed'),
]