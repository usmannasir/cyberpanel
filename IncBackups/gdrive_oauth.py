"""Session-bound Google Drive setup. Credentials never travel in browser URLs."""
import base64
from functools import wraps
import hashlib
import hmac
import json
import pwd
import re
import secrets
import subprocess
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
CALLBACKS = {'v2': '/IncrementalBackups/ConfigureV2BackupSetup', 'normal': '/backup/gDriveSetup'}
NORMAL_DOMAIN = 'normal-backup-account'
PUBLIC_PLATFORM = 'https://platform.cyberpersons.com'


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


def _check_access(request, website, mode='v2', status_only=False):
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
        if mode == 'v2':
            if not status_only and ACLManager.checkOwnership(website, admin, acl) != 1:
                raise AccessDenied()
            entitlement = ACLManager.CheckForPremFeature('all')
            if type(entitlement) is not int or entitlement != 1:
                raise AccessDenied()
        elif mode != 'normal':
            raise AccessDenied()
    except Exception:
        raise AccessDenied() from None


def _binding(session):
    if not session.session_key:
        session.save()
    return hashlib.sha256(session.session_key.encode()).hexdigest()


def _registration_headers(base):
    key = getattr(settings, 'GDRIVE_HANDOFF_REGISTRATION_KEY', '')
    if isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', key):
        return {'X-GDrive-Installation-Key': key}
    if (key == '' and getattr(settings, 'GDRIVE_HANDOFF_PUBLIC', False) is True
            and base == PUBLIC_PLATFORM):
        return {}
    raise ValueError('Enrollment admission is not configured')


def _post(base, path, payload):
    headers = {}
    if path == '/gDrive/register':
        headers = _registration_headers(base)
    result = requests.post(base + path, json=payload, timeout=(5, 15),
                           headers=headers, allow_redirects=False)
    if result.status_code != 200:
        raise ValueError()
    data = result.json()
    if not isinstance(data, dict) or data.get('status') != 1:
        raise ValueError()
    return data


def capability(mode='v2'):
    """Fail closed until both this installation and the platform support v2."""
    try:
        if mode not in CALLBACKS:
            raise ValueError()
        base = _base()
        public_client = not _registration_headers(base)
        response = requests.get(base + '/gDrive/capabilities', timeout=(5, 10), allow_redirects=False)
        data = response.json()
        if (response.status_code != 200 or data.get('status') != 1 or
                data.get('protocol') != 'gdrive-handoff' or data.get('version') != 2 or
                data.get('enabled') is not True or mode not in data.get('flows', []) or
                (public_client and data.get('admission') != 'public') or
                data.get('register_path') != '/gDrive/register' or
                data.get('redeem_path') != '/gDrive/redeem' or
                data.get('start_path') != '/gDrive/v2/start' or
                data.get('callback_path') != '/gDrive/v2/callback'):
            raise ValueError()
        return True, ''
    except Exception:
        return False, 'Google Drive connection setup is unavailable. Check service availability, use the latest CyberPanel update, and contact support if this persists. Existing backups are unchanged.'


def _origin_ok(request):
    # Django 3.1 does not enforce Origin. Explicitly reject null/missing origins.
    expected = urlsplit(request.build_absolute_uri('/'))
    return request.META.get('HTTP_ORIGIN') == expected.scheme + '://' + expected.netloc


@_secured
def status(request, mode='v2'):
    if request.method != 'GET':
        return _error(405)
    try:
        _check_access(request, None, mode, status_only=True)
    except AccessDenied:
        return _error(403)
    enabled, reason = capability(mode)
    return JsonResponse({'status': 1, 'enabled': enabled, 'reason': reason})


@_secured
@csrf_protect
def begin(request, mode='v2'):
    try:
        base = _base()
    except Exception:
        return _error(503)
    if request.method != 'POST':
        return _error(405)
    try:
        if not request.is_secure() or not _origin_ok(request):
            return _error()
        data = _data(request)
        website = data['Selectedwebsite'] if mode == 'v2' else NORMAL_DOMAIN
        account = data['accountName']
        client_id, client_secret = data['client_id'], data['client_secret']
        if (not isinstance(website, str) or len(website) > 253 or
                not isinstance(account, str) or not ACCOUNT.fullmatch(account) or
                (mode == 'normal' and len(account) > 50) or
                not isinstance(client_id, str) or len(client_id) > 256 or not CLIENT.fullmatch(client_id) or
                not isinstance(client_secret, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{1,512}', client_secret)):
            return _error()
        _check_access(request, website, mode)
        if mode not in CALLBACKS or not capability(mode)[0]:
            return _error(503)
        pending = request.session.get(SESSION_KEY, {})
        pending = {key: value for key, value in pending.items()
                   if 0 <= time.time() - value.get('created', 0) < TTL}
        if len(pending) >= 4:
            return _error(429)
        verifier = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        callback = request.build_absolute_uri(CALLBACKS[mode])
        payload = {'callback': callback, 'state': state, 'challenge': challenge,
                   'account': account, 'domain': website, 'flow_type': mode,
                   'client_id': client_id, 'client_secret': client_secret}
        registered = _post(base, '/gDrive/register', payload)
        url = urlsplit(registered['authorization_url'])
        expected = urlsplit(base)
        args = parse_qs(url.query, strict_parsing=True)
        if (url.scheme != expected.scheme or url.netloc != expected.netloc or
                url.path != '/gDrive/v2/start' or url.fragment or set(args) != {'handoff'} or
                len(args['handoff']) != 1 or not OPAQUE.fullmatch(args['handoff'][0])):
            return _error(502)
        pending[state] = {'verifier': verifier, 'created': time.time(),
                          'user_id': request.session['userID'], 'website': website,
                          'account': account, 'callback': callback,
                          'binding': _binding(request.session), 'mode': mode}
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
    # LSWS may report lswsgi as sys.executable. Use the installed, isolated
    # interpreter and the exact no-extra-arguments sudo policy.
    helper = '/usr/local/CyberCP/plogical/gdriveConfig.py'
    result = subprocess.run(
        ['sudo', '-n', '/usr/local/CyberPanel/bin/python', '-I', '-S', helper],
        input=json.dumps({'user': site.externalApp, 'home': '/home/' + site.domain,
                          'account': account, 'credentials': credentials}).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
    )
    if result.returncode:
        raise ValueError()


def _install_normal(user_id, account, credentials):
    from django.db import transaction
    from websiteFunctions.models import GDrive
    # Global unique name + INSERT only: a collision must never update an old row.
    auth = dict(credentials, handoff_version=2)
    with transaction.atomic():
        GDrive.objects.create(owner_id=user_id, name=account,
                              auth=json.dumps(auth, sort_keys=True), runTime='NEVER')


@_secured
@csrf_protect
def complete(request, mode='v2'):
    try:
        base = _base()
        if mode not in CALLBACKS:
            return _error()
    except Exception:
        return _error(503)
    if request.method not in ('GET', 'POST'):
        return _error(405)
    try:
        if not request.is_secure() or (request.method == 'POST' and not _origin_ok(request)):
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
                record.get('mode') != mode or
                record['callback'] != request.build_absolute_uri(CALLBACKS[mode])):
            return _error()
        _check_access(request, record['website'], mode)
        if request.method == 'GET':
            html = format_html(
                '<!doctype html><html><head><title>Complete Google Drive setup</title></head><body>'
                '<h1>Complete Google Drive setup</h1><p>Save account {} for website {}?</p>'
                '<form method="post" action="{}">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<input type="hidden" name="state" value="{}">'
                '<input type="hidden" name="code" value="{}">'
                '<button type="submit">Save Google Drive destination</button></form></body></html>',
                record['account'], record['website'], CALLBACKS[mode], get_token(request), state, code)
            return _response(HttpResponse(html))
        del pending[state]
        request.session[SESSION_KEY] = pending
        redeemed = _post(base, '/gDrive/redeem', {
            'code': code, 'verifier': record['verifier'],
            'callback': record['callback'], 'state': state, 'flow_type': mode})
        if (redeemed.get('state') != state or redeemed.get('domain') != record['website'] or
                redeemed.get('account') != record['account'] or redeemed.get('flow_type') != mode):
            return _error()
        credentials = redeemed['credentials']
        _valid_credentials(credentials)
        if mode == 'normal':
            _install_normal(record['user_id'], record['account'], credentials)
        else:
            _install_backend(record['website'], record['account'], credentials)
        return _response(HttpResponse('<!doctype html><title>Google Drive configured</title>'
                                     '<h1>Google Drive destination configured</h1>'
                                     '<p>No backup job or schedule was started.</p>'))
    except AccessDenied:
        return _error(403)
    except Exception:
        return _error()
