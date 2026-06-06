import secrets
import time
from django.http import JsonResponse
from loginSystem.views import loadLoginPage
from django.shortcuts import redirect
from .models import PortManagerApiKey

_RATE = {}

def require_session(request):
    try:
        uid = request.session['userID']
        return True, str(uid)
    except KeyError:
        return False, None

def session_or_redirect(request):
    ok, uid = require_session(request)
    if not ok:
        return None, redirect(loadLoginPage)
    return uid, None

def _rate_limit(key, limit=10, window=60):
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True

def extract_api_key(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return (request.META.get('HTTP_X_PORT_MANAGER_KEY') or '').strip()

def api_auth(request, need_mutate=False):
    raw = extract_api_key(request)
    if not raw:
        return None, JsonResponse({'error': 'api key required'}, status=401)
    h = PortManagerApiKey.hash_key(raw)
    try:
        row = PortManagerApiKey.objects.get(key_hash=h, revoked=False)
    except PortManagerApiKey.DoesNotExist:
        return None, JsonResponse({'error': 'invalid api key'}, status=403)
    if need_mutate and row.scope != PortManagerApiKey.SCOPE_MUTATE:
        return None, JsonResponse({'error': 'mutate scope required'}, status=403)
    if need_mutate and not _rate_limit('mutate:' + h, 10, 60):
        return None, JsonResponse({'error': 'rate limit'}, status=429)
    return row, None

def generate_api_key(label='default', scope=PortManagerApiKey.SCOPE_READ):
    raw = secrets.token_urlsafe(32)
    PortManagerApiKey.objects.create(
        label=label[:64],
        key_hash=PortManagerApiKey.hash_key(raw),
        scope=scope,
    )
    return raw
