# -*- coding: utf-8 -*-
from django.db import models


class PaypalPremiumPluginConfig(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('patreon', 'Patreon Subscription'),
        ('paypal', 'PayPal Payment'),
        ('both', 'Check Both (Patreon or PayPal)'),
    ]
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='both',
        help_text="Choose which payment method to use for verification."
    )
    activation_key = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Validated activation key - grants access without re-entering."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PayPal Premium Plugin Configuration"
        verbose_name_plural = "PayPal Premium Plugin Configurations"

    def __str__(self):
        return "PayPal Premium Plugin Configuration"

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
