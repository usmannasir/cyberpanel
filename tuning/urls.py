from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadTuningHome, name='loadTuningHome'),
    path('litespeedTuning', views.liteSpeedTuning, name='liteSpeedTuning'),
    path('phpTuning', views.phpTuning, name='phpTuning'),
    path('tuneLitespeed', views.tuneLitespeed, name='tuneLitespeed'),
    path('tunePHP', views.tunePHP, name='tunePHP'),
]
