"""Multi-Server Manager records.

The tables are created by multiServer/schema.py, never by Django, so every model
is unmanaged and names its table. A controller uses Node, InventoryCache,
Capability and Entitlement; a managed server uses Link, PairingCode, Nonce,
SsoTicket and LinkSession; both write AuditEntry.

Every time is whole Unix seconds. Every secret that is not this server's own is
kept only as a public key or a hash: a copy of the database gives nobody a
pairing code, a login ticket or a capability.
"""
from django.db import models

PENDING, ACTIVE, PAUSED, REVOKED = 'pending', 'active', 'paused', 'revoked'
REVOKING = 'revoking'
STATUSES = (PENDING, ACTIVE, PAUSED, REVOKED, REVOKING)
_STATUS_CHOICES = [(status, status) for status in STATUSES]

# The largest inventory a controller stores; the column itself ends at 16 MiB.
MAX_SNAPSHOT = 8 * 1024 * 1024


class Node(models.Model):
    """Controller: one managed server.

    Its address, both keys and its certificate pin exist only inside `sealed`,
    which is authenticated together with `link_id`, so changing a row in the
    database cannot point a link at another server. The other columns are for
    listing and are never used to reach the server.
    """
    link_id = models.CharField(max_length=32, primary_key=True)
    label = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=_STATUS_CHOICES, default=PENDING)
    sealed = models.CharField(max_length=2048)
    panel_version = models.CharField(max_length=32, default='')
    advertised = models.CharField(max_length=400, default='')
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()
    last_seen_at = models.BigIntegerField(null=True, default=None)
    last_error = models.CharField(max_length=255, default='')
    last_error_at = models.BigIntegerField(null=True, default=None)

    class Meta:
        db_table = 'ms_nodes'
        managed = False


class InventoryCache(models.Model):
    """Controller: the last inventory of a managed server that passed validation."""
    node = models.OneToOneField(Node, on_delete=models.CASCADE, primary_key=True, db_column='link_id',
                                related_name='inventory')
    snapshot = models.TextField()
    fetched_at = models.BigIntegerField(null=True, default=None)
    error = models.CharField(max_length=255, default='')
    error_at = models.BigIntegerField(null=True, default=None)

    class Meta:
        db_table = 'ms_inventory_cache'
        managed = False


class Capability(models.Model):
    """Controller: lets one administrator's framed view reach one managed server.

    The capability travels in a URL, so only its SHA-256 is stored, next to the
    hash of the panel session it dies with.
    """
    token_hash = models.CharField(max_length=64, primary_key=True)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, db_column='link_id', related_name='capabilities')
    admin_id = models.IntegerField()
    session_hash = models.CharField(max_length=64)
    created_at = models.BigIntegerField()
    expires_at = models.BigIntegerField()

    class Meta:
        db_table = 'ms_caps'
        managed = False


class Entitlement(models.Model):
    """Controller: the platform's last licence answer (a single row, id 1)."""
    id = models.SmallIntegerField(primary_key=True)
    server_ip = models.CharField(max_length=45)
    granted = models.BooleanField(default=False)
    answered_at = models.BigIntegerField(default=0)
    checked_at = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'ms_entitlement'
        managed = False


class Link(models.Model):
    """Managed server: one controller that may manage this server.

    `controller_key` is the controller's public key; nothing here can sign.
    `pairing_key` names the pairing code the link was made from and is unique,
    so one code can never produce two links. A link counts only while
    `generation` equals the counter in the root-owned key directory, which is
    raised on every revocation: restoring an old database revives nothing.
    `last_request_at` is the newest signed time accepted, so a clock set back
    does not reopen the window for an old request. `failures` counts the wrong
    numbers typed while the link waited for approval.
    """
    link_id = models.CharField(max_length=32, primary_key=True)
    controller_key = models.CharField(max_length=64)
    pairing_key = models.CharField(max_length=64, unique=True)
    allowed_ips = models.CharField(max_length=1024)
    admin_id = models.IntegerField()
    status = models.CharField(max_length=16, choices=_STATUS_CHOICES, default=PENDING)
    generation = models.BigIntegerField()
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()
    activated_at = models.BigIntegerField(null=True, default=None)
    expires_at = models.BigIntegerField()
    last_request_at = models.BigIntegerField(default=0)
    failures = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'ms_links'
        managed = False


class PairingCode(models.Model):
    """Managed server: an open pairing code, known here only by its public key."""
    public_key = models.CharField(max_length=64, primary_key=True)
    controller_ip = models.CharField(max_length=45)
    admin_id = models.IntegerField()
    created_at = models.BigIntegerField()
    expires_at = models.BigIntegerField()
    failures = models.SmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)

    class Meta:
        db_table = 'ms_pairing_codes'
        managed = False


class Nonce(models.Model):
    """Managed server: a nonce already accepted on a link; the pair is unique."""
    id = models.BigAutoField(primary_key=True)
    link = models.ForeignKey(Link, on_delete=models.CASCADE, db_column='link_id', related_name='nonces')
    nonce = models.CharField(max_length=32)
    seen_at = models.BigIntegerField()

    class Meta:
        db_table = 'ms_nonces'
        managed = False
        unique_together = (('link', 'nonce'),)


class SsoTicket(models.Model):
    """Managed server: a one-click login ticket, by SHA-256."""
    ticket_hash = models.CharField(max_length=64, primary_key=True)
    link = models.ForeignKey(Link, on_delete=models.CASCADE, db_column='link_id', related_name='tickets')
    admin_id = models.IntegerField()
    actor = models.CharField(max_length=50)
    landing = models.CharField(max_length=255)
    created_at = models.BigIntegerField()
    expires_at = models.BigIntegerField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'ms_sso_tickets'
        managed = False


class LinkSession(models.Model):
    """Managed server: a panel session that was opened through a link."""
    session_key = models.CharField(max_length=40, primary_key=True)
    link = models.ForeignKey(Link, on_delete=models.CASCADE, db_column='link_id', related_name='sessions')
    created_at = models.BigIntegerField()

    class Meta:
        db_table = 'ms_sessions'
        managed = False


class AuditEntry(models.Model):
    """Both: one audited event. Written only by multiServer/audit.py."""
    id = models.BigAutoField(primary_key=True)
    at = models.BigIntegerField()
    event = models.CharField(max_length=32)
    outcome = models.CharField(max_length=8)
    reason = models.CharField(max_length=32, default='')
    link_id = models.CharField(max_length=32, default='')
    actor = models.CharField(max_length=50, default='')
    source_ip = models.CharField(max_length=45, default='')
    method = models.CharField(max_length=8, default='')
    path = models.CharField(max_length=255, default='')
    status = models.SmallIntegerField(null=True, default=None)
    size = models.BigIntegerField(null=True, default=None)
    dropped = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'ms_audit'
        managed = False
