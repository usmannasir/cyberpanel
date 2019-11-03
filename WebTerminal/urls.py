from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.terminal, name='terminal'),
    url(r'^restart$', views.restart, name='restart'),
]