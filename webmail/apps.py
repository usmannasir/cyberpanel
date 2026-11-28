from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _scrub_stored_passwords(sender, **kwargs):
    from .mailbox_secret import scrub_stored_passwords
    scrub_stored_passwords()


class WebmailConfig(AppConfig):
    name = 'webmail'

    def ready(self):
        # Every upgrade runs "manage.py migrate"; older releases kept
        # standalone mailbox passwords in plain text in the session table.
        post_migrate.connect(_scrub_stored_passwords, sender=self,
                             dispatch_uid='webmail-scrub-stored-passwords')
