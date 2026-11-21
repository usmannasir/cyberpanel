"""Short-lived, per-link inventory snapshots. No database lock is held during HTTPS."""
import hashlib
from contextlib import ExitStack
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.db import transaction
from django.db.models.functions import Coalesce, Substr

from multiServer import inventory, links, models, transport

FRESH = 60
RETRY = 30
MAX_STALE = 300
FANOUT = 4
_SLOTS = threading.BoundedSemaphore(FANOUT)
OFFLINE = 'offline'
REFUSED = 'unavailable'
STORED_LIMIT = 65 + inventory.BYTE_LIMIT


def _identity(node):
    return hashlib.sha256(node.sealed.encode('ascii')).hexdigest()


def _recent(timestamp, now, seconds):
    return timestamp is not None and 0 <= now - timestamp < seconds


def _claim(link_id, now):
    with transaction.atomic():
        node = models.Node.objects.select_for_update().filter(pk=link_id, status=models.ACTIVE).first()
        if not node:
            return
        caches = models.InventoryCache.objects.filter(node=node)
        times = caches.values_list('fetched_at', 'error_at').first()
        if times and (_recent(times[0], now, FRESH) or _recent(times[1], now, RETRY)):
            return
        # A unique lease prevents an expired or paused-and-resumed request from winning a later write.
        lease = 'fetch-' + uuid.uuid4().hex
        if times is None:
            models.InventoryCache.objects.create(node=node, snapshot='', error=lease, error_at=now)
        else:
            caches.update(error=lease, error_at=now)
        return node, lease


def _fetch(node, actor):
    try:
        link = links.link_of(node)
        status, mime, body = transport.send(link, 'GET', inventory.PATH, '', '-', b'', actor, 'inventory')
        if status != 200 or mime != 'application/json':
            return REFUSED, ''
        return '', _identity(node) + '\n' + inventory.encode(inventory.decode(body)).decode('ascii')
    except transport.ConnectionFailed:
        return OFFLINE, ''
    except (links.LinkError, transport.TransportError, ValueError, RecursionError):
        return REFUSED, ''


def _finish(node, lease, result, now):
    error, snapshot = result
    with transaction.atomic():
        current = models.Node.objects.select_for_update().filter(pk=node.pk, status=models.ACTIVE).first()
        if not current or (current.sealed, current.updated_at) != (node.sealed, node.updated_at):
            return
        changes = {'error': error, 'error_at': now if error else None}
        # Only a network outage permits the previous verified snapshot to survive.
        if error != OFFLINE:
            changes.update(snapshot=snapshot, fetched_at=None if error else now)
        models.InventoryCache.objects.filter(node=current, error=lease).update(**changes)


def refresh(active, actor, now):
    due = active.exclude(inventory__fetched_at__gt=now - FRESH, inventory__fetched_at__lte=now)
    due = due.exclude(inventory__error_at__gt=now - RETRY, inventory__error_at__lte=now)
    # Ask the least recently attempted first, including nodes recovering from an outage.
    due = due.order_by(Coalesce('inventory__error_at', 'inventory__fetched_at'), 'pk')
    ids = list(due.values_list('pk', flat=True)[:FANOUT])
    with ExitStack() as slots, ThreadPoolExecutor(max_workers=FANOUT) as pool:
        pending = []
        for link_id in ids:
            if not _SLOTS.acquire(False):
                break
            slots.callback(_SLOTS.release)
            claim = _claim(link_id, now)
            if claim:
                node, lease = claim
                pending.append((node, lease, pool.submit(_fetch, node, actor)))
        for node, lease, future in pending:
            _finish(node, lease, future.result(), int(time.time()))


def sources(active):
    """Keyset batches bound the MariaDB client's result buffer, including on large fleets."""
    last = None
    while True:
        batch = active if last is None else active.filter(pk__gt=last)
        batch = list(batch.annotate(saved=Substr('inventory__snapshot', 1, STORED_LIMIT + 1)).values(
            'link_id', 'label', 'sealed', 'updated_at', 'saved', 'inventory__fetched_at', 'inventory__error'
        ).order_by('pk')[:8])
        if not batch:
            return
        for item in batch:
            node = models.Node(link_id=item['link_id'], label=item['label'], sealed=item['sealed'],
                               updated_at=item['updated_at'])
            yield node, item['saved'], item['inventory__fetched_at'], item['inventory__error']
        last = batch[-1]['link_id']


def contents(node, saved, fetched, error, now):
    pending = bool(error and error.startswith('fetch-'))
    if error not in (None, '', OFFLINE) and not pending:
        return None, 'Unavailable'
    if _recent(fetched, now, MAX_STALE) and saved and len(saved) <= STORED_LIMIT:
        try:
            identity, body = saved.split('\n', 1)
            if identity == _identity(node):
                data = inventory.decode(body.encode('ascii'))
                if not error and _recent(fetched, now, FRESH):
                    return data, 'Current'
                return data, 'Stale · node offline' if error == OFFLINE else 'Stale · refresh pending'
        except (ValueError, RecursionError):
            pass
    if error == OFFLINE:
        return None, 'Unavailable · node offline'
    if pending:
        return None, 'Refresh pending'
    return None, 'Unavailable' if saved else 'Awaiting refresh'
