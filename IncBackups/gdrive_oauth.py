"""Session-bound Google Drive setup. Credentials never travel in browser URLs."""
import base64
from functools import wraps
import hashlib
import hmac
import json
from pathlib import Path
import pwd
import re
import secrets
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_protect

SESSION_KEY = 'gdrive_oauth_v2'
TTL = 300
OPAQUE = re.compile(r'^[A-Za-z0-9_-]{43,128}$')
ACCOUNT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
CLIENT = re.compile(r'^[A-Za-z0-9_.-]+\.apps\.googleusercontent\.com$')
TOKEN = re.compile(r'^[A-Za-z0-9._~+/=-]{1,8192}$')
SCOPE = 'https://www.googleapis.com/auth/drive.file'


class AccessDenied(Exception):
    pass


def _response(response):
    response['Cache-Control'] = 'no-store'
    # no-referrer turns basic form POST Origin into null in browsers, defeating
    # normal CSRF validation. strict-origin still never discloses paths/codes.
    response['Referrer-Policy'] = 'strict-origin'
    response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _error(status=400):
    return _response(JsonResponse({'status': 0, 'error_message':
        'Google Drive setup could not be completed. Start again or contact support.'}, status=status))


def _secured(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        return _response(view(*args, **kwargs))
    return wrapped


def _base():
    if not getattr(settings, 'GDRIVE_HANDOFF_ENABLED', False):
        raise RuntimeError('Disabled')
    if getattr(settings, 'SESSION_ENGINE', '').endswith('signed_cookies'):
        raise RuntimeError('Server-side sessions required')
    base = getattr(settings, 'GDRIVE_PLATFORM_BASE_URL', 'https://platform.cyberpersons.com').rstrip('/')
    url = urlsplit(base)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        raise RuntimeError('Invalid configured service')
    return base


def _data(request):
    if request.content_type == 'application/json':
        if len(request.body) > 32768:
            raise ValueError()
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    if request.content_type == 'application/x-www-form-urlencoded':
        if any(len(request.POST.getlist(key)) != 1 for key in request.POST):
            raise ValueError()
        return request.POST
    raise ValueError()


def _check_access(request, website):
    from loginSystem.models import Administrator
    from plogical.acl import ACLManager
    user_id = request.session.get('userID')
    if type(user_id) is not int:
        raise AccessDenied()
    try:
        admin = Administrator.objects.get(pk=user_id)
        acl = ACLManager.loadedACL(user_id)
        if ACLManager.currentContextPermission(acl, 'createBackup') != 1:
            raise AccessDenied()
        if ACLManager.checkOwnership(website, admin, acl) != 1:
            raise AccessDenied()
        entitlement = ACLManager.CheckForPremFeature('all')
        if type(entitlement) is not int or entitlement != 1:
            raise AccessDenied()
    except Exception:
        raise AccessDenied() from None


def _binding(session):
    if not session.session_key:
        session.save()
    return hashlib.sha256(session.session_key.encode()).hexdigest()


def _post(base, path, payload):
    headers = {}
    if path == '/gDrive/register':
        key = getattr(settings, 'GDRIVE_HANDOFF_REGISTRATION_KEY', '')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', key):
            raise ValueError()
        headers['X-GDrive-Installation-Key'] = key
    result = requests.post(base + path, json=payload, timeout=(5, 15),
                           headers=headers, allow_redirects=False)
    if result.status_code != 200:
        raise ValueError()
    data = result.json()
    if not isinstance(data, dict) or data.get('status') != 1:
        raise ValueError()
    return data


@_secured
@csrf_protect
def begin(request):
    try:
        base = _base()
    except Exception:
        return _error(503)
    if request.method != 'POST':
        return _error(405)
    try:
        if not request.is_secure():
            return _error()
        data = _data(request)
        website, account = data['Selectedwebsite'], data['accountName']
        client_id, client_secret = data['client_id'], data['client_secret']
        if (not isinstance(website, str) or len(website) > 253 or
                not isinstance(account, str) or not ACCOUNT.fullmatch(account) or
                not isinstance(client_id, str) or len(client_id) > 256 or not CLIENT.fullmatch(client_id) or
                not isinstance(client_secret, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{1,512}', client_secret)):
            return _error()
        _check_access(request, website)
        verifier = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        callback = request.build_absolute_uri('/IncrementalBackups/ConfigureV2BackupSetup')
        payload = {'callback': callback, 'state': state, 'challenge': challenge,
                   'account': account, 'domain': website,
                   'client_id': client_id, 'client_secret': client_secret}
        registered = _post(base, '/gDrive/register', payload)
        url = urlsplit(registered['authorization_url'])
        expected = urlsplit(base)
        args = parse_qs(url.query, strict_parsing=True)
        if (url.scheme != expected.scheme or url.netloc != expected.netloc or
                url.path != '/gDrive' or url.fragment or set(args) != {'handoff'} or
                len(args['handoff']) != 1 or not OPAQUE.fullmatch(args['handoff'][0])):
            return _error(502)
        pending = request.session.get(SESSION_KEY, {})
        pending = {key: value for key, value in pending.items()
                   if 0 <= time.time() - value.get('created', 0) < TTL}
        if len(pending) >= 4:
            return _error(429)
        pending[state] = {'verifier': verifier, 'created': time.time(),
                          'user_id': request.session['userID'], 'website': website,
                          'account': account, 'callback': callback,
                          'binding': _binding(request.session)}
        request.session[SESSION_KEY] = pending
        return _response(JsonResponse({'status': 1, 'authorization_url': registered['authorization_url']}))
    except AccessDenied:
        return _error(403)
    except (KeyError, TypeError, ValueError):
        return _error()
    except Exception:
        # Do not include exceptions, response bodies, or request URLs in logs/errors.
        return _error(502)


def _valid_credentials(credentials):
    from plogical.gdriveConfig import validate_credentials
    validate_credentials(credentials)
    if (credentials.get('token_uri') != 'https://oauth2.googleapis.com/token' or
            credentials.get('scopes') != [SCOPE]):
        raise ValueError()


def _install_backend(website, account, credentials):
    from websiteFunctions.models import Websites
    site = Websites.objects.get(domain=website)
    if (not re.fullmatch(r'[A-Za-z0-9_.-]{1,253}', site.domain) or
            not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', site.externalApp)):
        raise ValueError()
    owner = pwd.getpwnam(site.externalApp)
    if owner.pw_uid == 0 or owner.pw_dir != '/home/' + site.domain:
        raise ValueError()
    # No constructor-driven installer, shell interpolation, tokens in argv, or debug logging.
    helper = Path(__file__).resolve().parents[1] / 'plogical' / 'gdriveConfig.py'
    result = subprocess.run(
        ['sudo', '-n', '-u', site.externalApp, sys.executable, str(helper), '--home', '/home/' + site.domain],
        input=json.dumps({'account': account, 'credentials': credentials}).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
    )
    if result.returncode:
        raise ValueError()


@_secured
@csrf_protect
def complete(request):
    try:
        base = _base()
    except Exception:
        return _error(503)
    if request.method not in ('GET', 'POST'):
        return _error(405)
    try:
        if not request.is_secure():
            return _error()
        data = request.GET if request.method == 'GET' else _data(request)
        if request.method == 'GET' and any(len(data.getlist(key)) != 1 for key in data):
            return _error()
        if set(data) - {'state', 'code', 'csrfmiddlewaretoken'}:
            return _error()
        state, code = data['state'], data['code']
        if not OPAQUE.fullmatch(state) or not OPAQUE.fullmatch(code):
            return _error()
        pending = request.session.get(SESSION_KEY, {})
        record = pending.get(state)
        if (not record or record['user_id'] != request.session.get('userID') or
                not hmac.compare_digest(record['binding'], _binding(request.session)) or
                not 0 <= time.time() - record['created'] < TTL or
                record['callback'] != request.build_absolute_uri('/IncrementalBackups/ConfigureV2BackupSetup')):
            return _error()
        _check_access(request, record['website'])
        if request.method == 'GET':
            html = format_html(
                '<!doctype html><html><head><title>Complete Google Drive setup</title></head><body>'
                '<h1>Complete Google Drive setup</h1><p>Save account {} for website {}?</p>'
                '<form method="post" action="/IncrementalBackups/ConfigureV2BackupSetup">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<input type="hidden" name="state" value="{}">'
                '<input type="hidden" name="code" value="{}">'
                '<button type="submit">Save Google Drive destination</button></form></body></html>',
                record['account'], record['website'], get_token(request), state, code)
            return _response(HttpResponse(html))
        del pending[state]
        request.session[SESSION_KEY] = pending
        redeemed = _post(base, '/gDrive/redeem', {
            'code': code, 'verifier': record['verifier'],
            'callback': record['callback'], 'state': state})
        if (redeemed.get('state') != state or redeemed.get('domain') != record['website'] or
                redeemed.get('account') != record['account']):
            return _error()
        credentials = redeemed['credentials']
        _valid_credentials(credentials)
        _install_backend(record['website'], record['account'], credentials)
        return _response(HttpResponse('<!doctype html><title>Google Drive configured</title>'
                                     '<h1>Google Drive destination configured</h1>'
                                     '<p>No backup job or schedule was started.</p>'))
    except AccessDenied:
        return _error(403)
    except Exception:
        return _error()
