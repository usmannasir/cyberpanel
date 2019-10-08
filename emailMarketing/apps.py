# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig


class EmailmarketingConfig(AppConfig):
    name = 'emailMarketing'
    def ready(self):
        import signals
