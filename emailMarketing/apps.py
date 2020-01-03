# -*- coding: utf-8 -*-


from django.apps import AppConfig


class EmailmarketingConfig(AppConfig):
    name = 'emailMarketing'
    def ready(self):
        from . import signals
