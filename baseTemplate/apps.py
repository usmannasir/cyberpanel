# -*- coding: utf-8 -*-


from django.apps import AppConfig


class BasetemplateConfig(AppConfig):
    name = 'baseTemplate'
    
    def ready(self):
        import baseTemplate.signals