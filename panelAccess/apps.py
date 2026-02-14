# -*- coding: utf-8 -*-
"""
Panel Access app: merges admin-configured custom panel domains into
CSRF_TRUSTED_ORIGINS so POSTs work when the panel is behind a reverse proxy.
"""
import os
from django.apps import AppConfig


def get_panel_csrf_origins_file():
    """Path to the file where custom panel origins are stored (one per line)."""
    return os.environ.get(
        'PANEL_CSRF_ORIGINS_FILE',
        '/home/cyberpanel/panel_csrf_origins.conf'
    )


def read_panel_csrf_origins():
    """Read trusted origins from the config file. Returns list of strings."""
    path = get_panel_csrf_origins_file()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
    except (OSError, IOError):
        return []
    origins = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        origins.append(line)
    return origins


class PanelaccessConfig(AppConfig):
    name = 'panelAccess'
    verbose_name = 'Panel Access (Custom Domain / CSRF)'

    def ready(self):
        """Merge admin-configured origins into CSRF_TRUSTED_ORIGINS at startup."""
        try:
            from django.conf import settings
            custom = read_panel_csrf_origins()
            if not custom:
                return
            base = list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []))
            for origin in custom:
                if origin and origin not in base:
                    base.append(origin)
            settings.CSRF_TRUSTED_ORIGINS = base
        except Exception:
            pass
