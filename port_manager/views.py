import json
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from plogical.httpProc import httpProc
from plogical.mailUtilities import mailUtilities
from .auth import session_or_redirect, generate_api_key
from .models import PortManagerApiKey
from .utils.port_scanner import list_listeners
from .utils.docker_ports import list_docker_maps
from .utils.panel_port import get_panel_port, get_panel_base_url

def _safe_ports():
    try:
        return list_listeners()
    except Exception:
        return []

def _safe_docker(include_stopped=False):
    try:
        return list_docker_maps(include_stopped=include_stopped)
    except Exception:
        return []

@require_http_methods(['GET'])
def dashboard(request):
    uid, redir = session_or_redirect(request)
    if redir:
        return redir
    mailUtilities.checkHome()
    include_stopped = request.GET.get('stopped') == '1'
    api_keys = list(
        PortManagerApiKey.objects.filter(revoked=False).order_by('-id')[:20].values(
            'id', 'label', 'scope', 'created_at'
        )
    )
    for row in api_keys:
        if row.get('created_at'):
            row['created_at'] = row['created_at'].isoformat()
    data = {
        'ports_json': json.dumps(_safe_ports()),
        'docker_json': json.dumps(_safe_docker(include_stopped)),
        'panel_port': get_panel_port(),
        'panel_url': get_panel_base_url(request),
        'api_keys': api_keys,
        'include_stopped': include_stopped,
    }
    proc = httpProc(request, 'port_manager/dashboard.html', data, 'admin')
    return proc.render()

@require_http_methods(['POST'])
def create_api_key(request):
    uid, redir = session_or_redirect(request)
    if redir:
        return redir
    scope = request.POST.get('scope', PortManagerApiKey.SCOPE_READ)
    if scope not in (PortManagerApiKey.SCOPE_READ, PortManagerApiKey.SCOPE_MUTATE):
        scope = PortManagerApiKey.SCOPE_READ
    raw = generate_api_key(request.POST.get('label', 'default'), scope)
    return JsonResponse({
        'key': raw,
        'scope': scope,
        'message': 'Store this key now; it will not be shown again.',
    })

@require_http_methods(['POST'])
def revoke_api_key(request):
    uid, redir = session_or_redirect(request)
    if redir:
        return redir
    try:
        kid = int(request.POST.get('id', '0'))
        PortManagerApiKey.objects.filter(id=kid).update(revoked=True)
        return JsonResponse({'success': True})
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid id'}, status=400)
