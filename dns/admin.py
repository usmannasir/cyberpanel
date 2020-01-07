# -*- coding: utf-8 -*-

from . import models
from django.contrib import admin

admin.site.register(models.Domains)
admin.site.register(models.Records)
admin.site.register(models.Supermasters)
admin.site.register(models.Domainmetadata)