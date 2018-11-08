from django.conf.urls import url
import views

urlpatterns = [
    url(r'^$', views.router, name='router'),
]