"""Paid Roundcube management and the only public gateway to its private FPM pool."""
import json
import re
import socket
import struct
import subprocess
import sys
from http.cookies import SimpleCookie
from pathlib import Path

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from loginSystem.views import loadLoginPage
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.roundcubeRuntime import ROOT, STATE, ENABLED, SOCKET, VERSION

MAX_REQUEST = 24 * 1024 * 1024
MAX_RESPONSE = 64 * 1024 * 1024
ENTITLEMENT_KEY = 'roundcube-entitlement-v1'
COOKIE_NAMES = frozenset(('cp_roundcube_session', 'cp_roundcube_auth'))


def entitled():
    """Fail closed; positive results expire after 60 seconds (including revocation)."""
    known = cache.get(ENTITLEMENT_KEY)
    if type(known) is bool:
        return known
    available = False
    for feature in ('all', 'roundcube'):
        try:
            value = ACLManager.CheckForPremFeature(feature)
        except Exception:
            value = 0
        if type(value) is int and value == 1:
            available = True
            break
    cache.set(ENTITLEMENT_KEY, available, 60 if available else 10)
    return available


def administrator(request):
    try:
        acl = ACLManager.loadedACL(request.session['userID'])
        return acl.get('admin') == 1
    except (KeyError, TypeError):
        return False
    except Exception:
        return False


def runtime_status():
    value = {'phase': 'not-installed', 'message': 'Roundcube has not been installed.', 'version': None}
    try:
        record = json.loads(STATE.read_text())
        value.update({key: record.get(key) for key in ('phase', 'message', 'version')})
    except (OSError, ValueError, TypeError):
        pass
    value['enabled'] = ENABLED.is_file()
    value['available_version'] = VERSION
    value['running'] = Path(SOCKET).is_socket() if value['enabled'] else False
    if value['phase'] == 'ready' and not value['running']:
        value['phase'] = 'error'
        value['message'] = 'The Roundcube runtime is not running. Enable it again or check the service journal.'
    return value


@ensure_csrf_cookie
@require_GET
def manage(request):
    if not request.session.get('userID'):
        return redirect(loadLoginPage)
    if not administrator(request):
        return HttpResponse('Server administrator access is required.', status=403)
    data = runtime_status()
    data['roundcube_entitled'] = entitled()
    return httpProc(request, 'webmail/roundcube.html', data, 'admin').render()


@require_GET
def get_status(request):
    if not administrator(request):
        return JsonResponse({'error_message': 'Server administrator access is required.'}, status=403)
    value = runtime_status()
    value['entitled'] = entitled()
    response = JsonResponse(value)
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def operate(request):
    if not administrator(request):
        return JsonResponse({'error_message': 'Server administrator access is required.'}, status=403)
    try:
        action = json.loads(request.body).get('action')
    except (ValueError, AttributeError):
        action = None
    if action not in ('install', 'enable', 'disable'):
        return JsonResponse({'error_message': 'Choose install, enable or disable.'}, status=400)
    # Removal of access must remain possible even after a subscription expires.
    if action != 'disable' and not entitled():
        return JsonResponse({'error_message': 'An active Roundcube add-on or all-features entitlement is required.'}, status=403)
    command = ['sudo', '-n', sys.executable, '/usr/local/CyberCP/plogical/roundcubeRuntime.py', action]
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        try:
            if process.wait(timeout=0.2) != 0:
                return JsonResponse({'error_message': 'Roundcube management could not start. Check the setup status and server sudo configuration.'}, status=503)
        except subprocess.TimeoutExpired:
            pass
    except OSError:
        return JsonResponse({'error_message': 'Could not start Roundcube management.'}, status=503)
    return JsonResponse({'status': 1, 'message': 'Roundcube operation started.'}, status=202)


def _record(kind, content=b''):
    return struct.pack('!BBHHBB', 1, kind, 1, len(content), 0, 0) + content


def _pairs(values):
    out = bytearray()
    for name, value in values.items():
        name, value = name.encode(), str(value).encode()
        for item in (name, value):
            length = len(item)
            out.extend(bytes([length]) if length < 128 else struct.pack('!I', length | 0x80000000))
        out.extend(name)
        out.extend(value)
    return bytes(out)


def _read(sock, size):
    result = bytearray()
    while len(result) < size:
        data = sock.recv(size - len(result))
        if not data:
            raise OSError('The Roundcube runtime closed its connection.')
        result.extend(data)
    return bytes(result)


def fastcgi(params, body):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        channel.settimeout(125)
        channel.connect(SOCKET)
        channel.sendall(_record(1, struct.pack('!HB5x', 1, 0)))
        encoded = _pairs(params)
        for start in range(0, len(encoded), 65535):
            channel.sendall(_record(4, encoded[start:start + 65535]))
        channel.sendall(_record(4))
        for start in range(0, len(body), 65535):
            channel.sendall(_record(5, body[start:start + 65535]))
        channel.sendall(_record(5))
        output = bytearray()
        total = 0
        while True:
            version, kind, rid, length, padding, _ = struct.unpack('!BBHHBB', _read(channel, 8))
            if version != 1 or rid != 1:
                raise OSError('Invalid response from the Roundcube runtime.')
            content = _read(channel, length)
            _read(channel, padding)
            total += length
            if total > MAX_RESPONSE:
                raise OSError('Roundcube response exceeds the maximum size.')
            if kind == 6:
                output.extend(content)
            elif kind == 3:
                if len(content) != 8 or content[:5] != b'\0' * 5:
                    raise OSError('The Roundcube runtime could not complete the request.')
                return bytes(output)
            # STDERR is never exposed to the browser (it may contain mail data).


def front_controller(path):
    """No filesystem path or arbitrary PHP script comes from the request."""
    if path in ('', 'index.php'):
        return 'index.php', ''
    if path.startswith('static.php/'):
        suffix = path[len('static.php'):]
        if '..' not in suffix and '\\' not in suffix and '\x00' not in suffix:
            return 'static.php', suffix
    return None, None


def cgi_response(raw):
    head, separator, body = raw.partition(b'\r\n\r\n')
    if not separator:
        head, separator, body = raw.partition(b'\n\n')
    if not separator or len(head) > 65536:
        raise OSError('Invalid response from the Roundcube runtime.')
    response = HttpResponse(body, content_type='text/html; charset=UTF-8')
    for line in head.decode('latin-1').splitlines():
        name, sep, value = line.partition(':')
        if not sep:
            raise OSError('Invalid Roundcube response header.')
        value = value.strip()
        lower = name.lower()
        if lower == 'status':
            code = int(value.split()[0])
            if not 100 <= code <= 599:
                raise OSError('Invalid Roundcube response status.')
            response.status_code = code
        elif lower == 'set-cookie':
            cookies = SimpleCookie()
            cookies.load(value)
            for cookie_name, morsel in cookies.items():
                if cookie_name not in COOKIE_NAMES:
                    continue
                # Login can delete the old auth cookie, then issue a new one
                # in this same response. SimpleCookie value assignment retains
                # old expiry attributes, which would immediately delete the new
                # credential; replace the entire morsel (last Set-Cookie wins).
                response.cookies.pop(cookie_name, None)
                response.cookies[cookie_name] = morsel.value
                cookie = response.cookies[cookie_name]
                cookie['path'] = '/roundcube/'
                cookie['secure'] = True
                cookie['httponly'] = True
                cookie['samesite'] = 'Lax'
                for attribute in ('expires', 'max-age'):
                    if morsel[attribute]:
                        cookie[attribute] = morsel[attribute]
        elif lower in ('content-type', 'content-disposition', 'location', 'last-modified',
                       'content-language', 'content-security-policy'):
            # Roundcube emits local redirects; do not forward off-site redirects.
            if lower == 'location' and (value.startswith('//') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value)):
                raise OSError('Unexpected redirect from Roundcube.')
            response[name] = value
    # Personalized mail responses must not be stored by a CDN or shared cache.
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Referrer-Policy'] = 'same-origin'
    return response


@csrf_exempt  # Roundcube validates its own session-bound request token, including AJAX.
def gateway(request, path=''):
    script, info = front_controller(path)
    if script is None:
        return HttpResponse('Not found.', status=404)
    if request.method not in ('GET', 'HEAD', 'POST'):
        return HttpResponse('Method not allowed.', status=405)
    if not request.is_secure():
        return HttpResponse('Roundcube requires an HTTPS connection.', status=400)
    if not entitled():
        return HttpResponse('Roundcube requires an active paid add-on on this server. Integrated webmail is available at /webmail/.', status=403)
    if not ENABLED.is_file():
        return HttpResponse('Roundcube is disabled. Integrated webmail is available at /webmail/.', status=503)
    try:
        if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_REQUEST:
            return HttpResponse('The upload exceeds the 24 MB limit.', status=413)
        # Read the raw stream to support attachments without Django's 2.5 MB form limit.
        body = request.read(MAX_REQUEST + 1)
        if len(body) > MAX_REQUEST:
            return HttpResponse('The upload exceeds the 24 MB limit.', status=413)
        safe_cookies = SimpleCookie()
        for name in COOKIE_NAMES:
            if name in request.COOKIES:
                safe_cookies[name] = request.COOKIES[name]
        host = request.get_host()
        params = {
            'GATEWAY_INTERFACE': 'CGI/1.1', 'SERVER_PROTOCOL': 'HTTP/1.1',
            'REQUEST_METHOD': request.method, 'SCRIPT_FILENAME': str(ROOT / 'current' / 'public_html' / script),
            'SCRIPT_NAME': '/roundcube/' + script, 'PATH_INFO': info,
            'REQUEST_URI': request.get_full_path(), 'QUERY_STRING': request.META.get('QUERY_STRING', ''),
            'DOCUMENT_ROOT': str(ROOT / 'current' / 'public_html'),
            'CONTENT_TYPE': request.META.get('CONTENT_TYPE', ''), 'CONTENT_LENGTH': str(len(body)),
            'HTTPS': 'on', 'REQUEST_SCHEME': 'https', 'HTTP_HOST': host,
            'SERVER_NAME': host.split(':')[0], 'SERVER_PORT': request.get_port(),
            'REMOTE_ADDR': request.META.get('REMOTE_ADDR', ''),
            'HTTP_COOKIE': '; '.join(item.OutputString() for item in safe_cookies.values()),
        }
        for header in ('HTTP_ACCEPT', 'HTTP_ACCEPT_LANGUAGE', 'HTTP_USER_AGENT',
                       'HTTP_X_REQUESTED_WITH', 'HTTP_X_ROUNDCUBE_REQUEST', 'HTTP_IF_MODIFIED_SINCE'):
            if header in request.META:
                params[header] = request.META[header]
        response = cgi_response(fastcgi(params, body))
        if request.method == 'HEAD':
            response.content = b''
        return response
    except (OSError, ValueError):
        return HttpResponse('Roundcube is temporarily unavailable. Please contact your server administrator.', status=502)
