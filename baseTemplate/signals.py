# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver
from loginSystem.models import Administrator
from .models import UserNotificationPreferences


@receiver(post_save, sender=Administrator)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create default notification preferences when a new Administrator is created"""
    if created:
        UserNotificationPreferences.objects.create(
            user=instance,
            backup_notification_dismissed=False,
            ai_scanner_notification_dismissed=False
        )


@receiver(post_save, sender=Administrator)
def save_user_notification_preferences(sender, instance, **kwargs):
    """Save notification preferences when Administrator is saved"""
    if hasattr(instance, 'notification_preferences'):
        instance.notification_preferences.save()
