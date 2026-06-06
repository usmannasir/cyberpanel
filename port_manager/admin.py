from django.contrib import admin
from .models import PortManagerApiKey, PortManagerAudit

admin.site.register(PortManagerApiKey)
admin.site.register(PortManagerAudit)
