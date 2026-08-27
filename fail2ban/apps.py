from django.apps import AppConfig


class Fail2banPluginConfig(AppConfig):
    name = 'fail2ban'
    verbose_name = 'Fail2ban Security Manager'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
        # Auto-ban runs as cyberpanel-fail2ban-autoban.service (not in LSCPD).
