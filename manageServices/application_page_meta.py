# -*- coding: utf-8 -*-
"""Server-side metadata for Manage Applications page (version lists in HTML)."""
import json
import os
import threading
import time

from django.utils.translation import gettext as _

from .application_detection import detect_app_state, managed_apps_os_support
from .application_versions import get_available_versions, version_compare

_APP_IMAGES = {
    'Elasticsearch': '/static/manageServices/images/elastic-search.png',
    'Redis': '/static/manageServices/images/redis.png',
    'RabbitMQ': '/static/manageServices/images/rabbitmq-logo.svg',
}

# Cache only repoquery/dnf-backed version lists (slow). Install state is always refreshed.
# Override with CYBERCP_MANAGED_APPS_VERSIONS_INVENTORY_TTL (seconds), default 3600 (1 hour).
_VERSIONS_INVENTORY_TTL_SECONDS = int(
    os.environ.get('CYBERCP_MANAGED_APPS_VERSIONS_INVENTORY_TTL', '3600')
)
_VERSIONS_INVENTORY_CACHE = {}
_VERSIONS_INVENTORY_LOCK = threading.Lock()


def _versions_inventory_cache_get(cache_key):
    now = time.time()
    with _VERSIONS_INVENTORY_LOCK:
        item = _VERSIONS_INVENTORY_CACHE.get(cache_key)
        if not item:
            return None
        ts, inventory = item
        if now - ts > _VERSIONS_INVENTORY_TTL_SECONDS:
            try:
                del _VERSIONS_INVENTORY_CACHE[cache_key]
            except Exception:
                pass
            return None
        return {k: list(v) for k, v in inventory.items()}


def _versions_inventory_cache_put(cache_key, inventory):
    with _VERSIONS_INVENTORY_LOCK:
        if len(_VERSIONS_INVENTORY_CACHE) > 16:
            _VERSIONS_INVENTORY_CACHE.clear()
        snap = {k: list(v) for k, v in (inventory or {}).items()}
        _VERSIONS_INVENTORY_CACHE[cache_key] = (time.time(), snap)


def _cold_fetch_version_inventory(major, rmq, support):
    """Populate version lists from package managers (DNF/apt); can take many seconds."""
    inv = {}
    if not support.get('supported'):
        for app_name in ('Elasticsearch', 'Redis', 'RabbitMQ'):
            inv[app_name] = []
        return inv
    for app_name in ('Elasticsearch', 'Redis', 'RabbitMQ'):
        try:
            inv[app_name] = get_available_versions(app_name, major, rmq)
        except BaseException:
            inv[app_name] = []
    return inv


def _resolve_version_inventory(cache_key, major, rmq, support):
    cached = _versions_inventory_cache_get(cache_key)
    if cached is not None:
        return cached
    inv = _cold_fetch_version_inventory(major, rmq, support)
    _versions_inventory_cache_put(cache_key, inv)
    return inv


def _assemble_manage_applications_payload(major, rmq, support, version_inv):
    """Build services + bootstrap JSON from fresh install state and cached (or new) version lists."""
    services = []
    bootstrap_apps = []

    for app_name in ('Elasticsearch', 'Redis', 'RabbitMQ'):
        state = detect_app_state(app_name)
        services.append({
            'image': _APP_IMAGES[app_name],
            'name': app_name,
            'installed': 'Installed' if state['installed'] else 'Not-Installed',
            'installedVersion': state.get('installedVersion', ''),
        })

        versions = list(version_inv.get(app_name) or [])
        latest_branch = ''
        latest_global = ''
        if versions:
            latest_branch = versions[0]
            latest_global = latest_branch

        installed_version = state['installedVersion']
        if installed_version and installed_version not in versions:
            prepend_installed = True
            if app_name == 'RabbitMQ':
                from manageServices.application_rabbitmq_repo import (
                    filter_versions_for_stream,
                )
                prepend_installed = bool(
                    filter_versions_for_stream([installed_version], rmq)
                )
            if prepend_installed:
                versions = [installed_version] + versions

        ref_latest = latest_global or latest_branch
        update_available = bool(
            state['installed']
            and installed_version
            and ref_latest
            and version_compare(installed_version, ref_latest) < 0
        )

        rabbitmq_versions_hint = ''
        if app_name == 'RabbitMQ' and not versions:
            if rmq == '4':
                rabbitmq_versions_hint = _(
                    'Your OS is not unsupported: upstream RabbitMQ publishes 4.x RPMs suitable for '
                    'RHEL/Alma/Rocky 8 and 9 (RPM filenames may still contain el8; that is normal). '
                    'If this list stays empty, repository metadata may not expose 4.x to dnf yet—'
                    'refresh metadata (dnf makecache -y) or install the official .rpm from rabbitmq.com. '
                    'Check with: dnf repoquery rabbitmq-server --available --show-duplicates '
                    '(4.x lines look like rabbitmq-server-0:4.x.y-1.el8.noarch — search for :4., not a space after the colon).'
                )
            else:
                rabbitmq_versions_hint = _(
                    'No 3.x builds were returned for this stream after refreshing Team RabbitMQ repos. '
                    'This is usually metadata or repo state—not OS support. Try: dnf makecache -y, '
                    'then dnf repoquery rabbitmq-server --available --show-duplicates.'
                )

        bootstrap_apps.append({
            'name': app_name,
            'installed': state['installed'],
            'installedVersion': installed_version,
            'latestAvailable': latest_branch,
            'latestOverall': latest_global,
            'updateAvailable': update_available,
            'crossBranchUpdateSuggested': False,
            'versions': versions,
            'packageName': state['packageName'],
            'adopted': bool(state['installed'] and not state['markerExists']),
            'major': major if app_name == 'Elasticsearch' else '',
            'rabbitmqStream': rmq if app_name == 'RabbitMQ' else '',
            'rabbitmqVersionsHint': rabbitmq_versions_hint,
        })

    bootstrap = {'status': 1, 'apps': bootstrap_apps}
    meta_json = json.dumps(bootstrap, ensure_ascii=False)
    return services, meta_json


def build_manage_applications_page_data(es_major='8', rabbitmq_stream='4'):
    """
    Build `services` for card HTML and a JSON-serializable bootstrap matching
    /manageservices/applicationMeta shape (default ES major 8, RMQ stream 4).

    Version lists are cached for _VERSIONS_INVENTORY_TTL_SECONDS to avoid repeated
    DNF/repoquery on every page view; install status is always detected live.
    """
    support = managed_apps_os_support()
    major = str(es_major).strip() if str(es_major).strip() in ('7', '8', '9') else '8'
    rmq = str(rabbitmq_stream).strip() if str(rabbitmq_stream).strip() in ('3', '4') else '4'
    cache_key = 'major:{0}|rmq:{1}|support:{2}'.format(
        major, rmq, 1 if support.get('supported') else 0
    )

    version_inv = _resolve_version_inventory(cache_key, major, rmq, support)
    return _assemble_manage_applications_payload(major, rmq, support, version_inv)


def get_application_meta_response_dict(es_major='8', rabbitmq_stream='4'):
    """
    JSON payload for POST /manageservices/applicationMeta.
    Shares the same version-list inventory cache as the Manage Applications HTML bootstrap.
    """
    support = managed_apps_os_support()
    major = str(es_major).strip() if str(es_major).strip() in ('7', '8', '9') else '8'
    rmq = str(rabbitmq_stream).strip() if str(rabbitmq_stream).strip() in ('3', '4') else '4'

    _, meta_json = build_manage_applications_page_data(major, rmq)
    payload = json.loads(meta_json)
    return {
        'status': 1,
        'osSupportedForManagedApps': support['supported'],
        'unsupportedReason': support['reason'],
        'apps': payload.get('apps') or [],
    }
