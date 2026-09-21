from django.urls import re_path
from .roundcube import gateway

urlpatterns = [re_path(r'^(?P<path>.*)$', gateway, name='roundcubeGateway')]
