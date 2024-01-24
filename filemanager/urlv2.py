from django.conf.urls import url
from . import views

urlpatterns = [

    url(r'^(?P<domain>(.*))$', views.loadFileManagerHomeV2, name='loadFileManagerHomeV2'),

]

