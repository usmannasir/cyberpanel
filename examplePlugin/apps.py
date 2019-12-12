# -*- coding: utf-8 -*-


from django.apps import AppConfig


class ExamplepluginConfig(AppConfig):
    name = 'examplePlugin'

    def ready(self):
        import signals
