from django.apps import AppConfig


class ExamplepluginConfig(AppConfig):
    name = 'examplePlugin'

    def ready(self):
        from . import signals
