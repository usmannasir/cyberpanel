from django.conf.urls import url,include
from . import views

urlpatterns = [
    url(r'^$', views.loadTuningHome, name='loadTuningHome'),
    url(r'^litespeedTuning', views.liteSpeedTuning, name='liteSpeedTuning'),
    url(r'^phpTuning', views.phpTuning, name='phpTuning'),



    url(r'^tuneLitespeed', views.tuneLitespeed, name='tuneLitespeed'),
    url(r'^tunePHP', views.tunePHP, name='tunePHP'),

]