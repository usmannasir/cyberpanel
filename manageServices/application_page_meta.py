# -*- coding: utf-8 -*-
"""Server-side metadata for Manage Applications page (version lists in HTML)."""
import json
import threading
import time

from .application_detection import detect_app_state, managed_apps_os_support
from .application_versions import get_available_versions, version_compare

_APP_IMAGES = {
    'Elasticsearch': '/static/manageServices/images/elastic-search.png',
    'Redis': '/static/manageServices/images/redis.png',
    'RabbitMQ': '/static/manageServices/images/rabbitmq-logo.svg',
}

_PAGE_META_TTL_SECONDS = 20
_PAGE_META_CACHE = {}
_PAGE_META_LOCK = threading.Lock()


def _page_meta_cache_get(cache_key):
    now = time.time()
    with _PAGE_META_LOCK:
        item = _PAGE_META_CACHE.get(cache_key)
        if not item:
            return None
        ts, payload = item
        if now - ts > _PAGE_META_TTL_SECONDS:
            try:
                del _PAGE_META_CACHE[cache_key]
            except Exception:
                pass
            return None
        services, meta_json = payload
        return list(services), str(meta_json)


def _page_meta_cache_put(cache_key, services, meta_json):
    with _PAGE_META_LOCK:
        # Keep cache tiny (we only have a handful of key combos).
        if len(_PAGE_META_CACHE) > 12:
            _PAGE_META_CACHE.clear()
        _PAGE_META_CACHE[cache_key] = (
            time.time(),
            (list(services), str(meta_json)),
        )


def build_manage_applications_page_data(es_major='8', rabbitmq_stream='3'):
    """
    Build `services` for card HTML and a JSON-serializable bootstrap matching
    /manageservices/applicationMeta shape (default ES major 8, RMQ stream 3).
    """
    services = []
    bootstrap_apps = []
    support = managed_apps_os_support()
    major = str(es_major).strip() if str(es_major).strip() in ('7', '8', '9') else '8'
    rmq = str(rabbitmq_stream).strip() if str(rabbitmq_stream).strip() in ('3', '4') else '3'
    cache_key = 'major:{0}|rmq:{1}|support:{2}'.format(
        major, rmq, 1 if support.get('supported') else 0
    )

    cached = _page_meta_cache_get(cache_key)
    if cached is not None:
        return cached

    for app_name in ('Elasticsearch', 'Redis', 'RabbitMQ'):
        state = detect_app_state(app_name)
        services.append({
            'image': _APP_IMAGES[app_name],
            'name': app_name,
            'installed': 'Installed' if state['installed'] else 'Not-Installed',
            'installedVersion': state.get('installedVersion', ''),
        })

        versions = []
        latest_branch = ''
        latest_global = ''
        if support['supported']:
            try:
                versions = get_available_versions(app_name, major, rmq)
            except BaseException:
                versions = []
            if versions:
                latest_branch = versions[0]
                latest_global = latest_branch

        installed_version = state['installedVersion']
        if installed_version and installed_version not in versions:
            versions = [installed_version] + versions

        ref_latest = latest_global or latest_branch
        update_available = bool(
            state['installed']
            and installed_version
            and ref_latest
            and version_compare(installed_version, ref_latest) < 0
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
        })

    bootstrap = {'status': 1, 'apps': bootstrap_apps}
    meta_json = json.dumps(bootstrap, ensure_ascii=False)
    _page_meta_cache_put(cache_key, services, meta_json)
    return services, meta_json


def get_application_meta_response_dict(es_major='8', rabbitmq_stream='3'):
    """
    JSON payload for POST /manageservices/applicationMeta.
    Reuses the same TTL cache as the Manage Applications HTML bootstrap so
    modal refresh hits warm cache after a page load (or prior request).
    """
    support = managed_apps_os_support()
    major = str(es_major).strip() if str(es_major).strip() in ('7', '8', '9') else '8'
    rmq = str(rabbitmq_stream).strip() if str(rabbitmq_stream).strip() in ('3', '4') else '3'
    cache_key = 'major:{0}|rmq:{1}|support:{2}'.format(
        major, rmq, 1 if support.get('supported') else 0
    )

    cached = _page_meta_cache_get(cache_key)
    if cached is not None:
        _services, meta_json = cached
    else:
        _services, meta_json = build_manage_applications_page_data(major, rmq)

    payload = json.loads(meta_json)
    return {
        'status': 1,
        'osSupportedForManagedApps': support['supported'],
        'unsupportedReason': support['reason'],
        'apps': payload.get('apps') or [],
    }
