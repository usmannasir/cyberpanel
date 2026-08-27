from django.contrib import admin
from .models import Fail2banSettings, SecurityEvent, BannedIP

@admin.register(Fail2banSettings)
class Fail2banSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'auto_ban_threshold', 'ban_duration', 'updated_at']
    list_filter = ['email_notifications', 'created_at']
    search_fields = ['user__username', 'user__email']

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'ip_address', 'jail_name', 'severity', 'created_at']
    list_filter = ['event_type', 'severity', 'created_at']
    search_fields = ['ip_address', 'jail_name', 'description']
    readonly_fields = ['created_at']

@admin.register(BannedIP)
class BannedIPAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'jail_name', 'banned_at', 'expires_at', 'is_active']
    list_filter = ['jail_name', 'is_active', 'banned_at']
    search_fields = ['ip_address', 'jail_name']
    readonly_fields = ['banned_at']
