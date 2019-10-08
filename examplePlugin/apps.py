# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig


class ExamplepluginConfig(AppConfig):
    name = 'examplePlugin'

    def ready(self):
        import signals
