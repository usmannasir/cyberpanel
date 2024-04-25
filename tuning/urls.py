from django.conf.urls import url, include
from . import views

urlpatterns = [
    url(r'^$', views.loadTuningHome, name='loadTuningHome'),
    url(r'^litespeedTuning', views.liteSpeedTuning, name='liteSpeedTuning'),
    url(r'^V2/litespeedTuningV2', views.liteSpeedTuningV2, name='liteSpeedTuningV2'),
    url(r'^phpTuning', views.phpTuning, name='phpTuning'),
    url(r'^V2/phpTuningV2', views.phpTuningV2, name='phpTuningV2'),

    url(r'^tuneLitespeed', views.tuneLitespeed, name='tuneLitespeed'),
    url(r'^tunePHP', views.tunePHP, name='tunePHP'),

]
