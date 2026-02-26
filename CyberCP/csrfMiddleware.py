# -*- coding: utf-8 -*-
"""
Custom CSRF middleware that exempts /phpmyadmin/ and /snappymail/ so their
PHP sign-in forms (POST) do not get 403 CSRF verification failed.
"""
from django.middleware.csrf import CsrfViewMiddleware


class CsrfExemptPhpMyAdminMiddleware(CsrfViewMiddleware):
    """CSRF middleware that skips verification for phpMyAdmin and SnappyMail paths."""

    EXEMPT_PREFIXES = ('/phpmyadmin/', '/snappymail/')

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith(self.EXEMPT_PREFIXES):
            return None  # Skip CSRF check
        return super().process_view(request, callback, callback_args, callback_kwargs)
