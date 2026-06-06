import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .auth import api_auth
from .utils.port_scanner import list_listeners
from .utils.docker_ports import list_docker_maps
from .utils.firewall_bridge import open_port
from .utils.process_control import stop_process
from .utils.validation import parse_port, parse_proto, is_protected_port
from .utils.audit_log import log_action
from .models import PortManagerAudit

def _json(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})

@require_http_methods(['GET'])
def list_ports_api(request):
    key, err = api_auth(request, need_mutate=False)
    if err:
        return err
    search = request.GET.get('search', '')
    bind = request.GET.get('bind', '')
    rows = list_listeners(search)
    if bind:
        rows = [r for r in rows if r.get('bind_type') == bind]
    return _json({'ports': rows})

@require_http_methods(['GET'])
def docker_ports_api(request):
    key, err = api_auth(request, need_mutate=False)
    if err:
        return err
    return _json({'docker': list_docker_maps()})

@require_http_methods(['POST'])
def firewall_open_api(request):
    key, err = api_auth(request, need_mutate=True)
    if err:
        return err
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return _json({'error': 'invalid json'}, 400)
    if not body.get('confirm'):
        return _json({'error': 'confirm required'}, 400)
    port = parse_port(body.get('port'))
    proto = parse_proto(body.get('proto'))
    if port is None or not proto:
        return _json({'error': 'invalid port or proto'}, 400)
    ok, msg = open_port(proto, port)
    log_action('api:' + key.label, 'firewall_open', f'{proto}/{port} {msg}', ok)
    return _json({'success': ok, 'message': msg}, 200 if ok else 400)

@require_http_methods(['POST'])
def process_stop_api(request):
    key, err = api_auth(request, need_mutate=True)
    if err:
        return err
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return _json({'error': 'invalid json'}, 400)
    if not body.get('confirm'):
        return _json({'error': 'confirm required'}, 400)
    pid = body.get('pid')
    port = body.get('port')
    proto = parse_proto(body.get('proto', 'tcp'))
    if port is not None and is_protected_port(parse_port(port)):
        log_action('api:' + key.label, 'process_stop', f'denied protected port {port}', False)
        return _json({'error': 'protected port'}, 403)
    ok, msg = stop_process(pid, port=parse_port(port) if port is not None else None, proto=proto)
    log_action('api:' + key.label, 'process_stop', f'pid={pid} {msg}', ok)
    return _json({'success': ok, 'message': msg}, 200 if ok else 400)

@require_http_methods(['GET'])
def audit_api(request):
    key, err = api_auth(request, need_mutate=False)
    if err:
        return err
    rows = list(PortManagerAudit.objects.order_by('-id')[:100].values(
        'actor', 'action', 'detail', 'success', 'created_at'))
    return _json({'audit': rows})
