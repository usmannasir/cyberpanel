# -*- coding: utf-8 -*-


from django.db import models


class PluginActivationKey(models.Model):
    """
    Optional ORM mirror for activation keys persisted in MariaDB.
    Runtime code uses raw SQL CREATE TABLE IF NOT EXISTS for migration safety.
    """
    plugin_name = models.CharField(max_length=191)
    user_identity = models.CharField(max_length=191)
    activation_key_hash = models.CharField(max_length=64)
    key_last4 = models.CharField(max_length=4, blank=True, default='')
    source = models.CharField(max_length=50, blank=True, default='manual')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'plugin_activation_keys'
        unique_together = (('plugin_name', 'user_identity'),)
