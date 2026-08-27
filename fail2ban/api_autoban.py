# -*- coding: utf-8 -*-
"""Auto-ban API endpoints for Fail2ban plugin."""
import json
import logging as pylogging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Fail2banAutoBanConfig
from .panel_auth import fail2ban_api, json_server_error
from . import auto_ban

logger = pylogging.getLogger('fail2ban_plugin')


def _serialize_config(config):
    return {
        'enabled': bool(config.enabled),
        'permanent': bool(config.permanent),
        'check_interval': int(config.check_interval or 60),
        'jail': config.jail or 'sshd',
        'last_run_at': config.last_run_at.isoformat() if config.last_run_at else None,
        'last_banned_count': int(config.last_banned_count or 0),
        'last_error': config.last_error or '',
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
    }


@fail2ban_api
@require_http_methods(["GET", "POST"])
def api_autoban_config(request):
    """Get or update SSH-alert auto-ban configuration."""
    try:
        config = Fail2banAutoBanConfig.get_config()
        if request.method == 'GET':
            return JsonResponse({'success': True, 'data': _serialize_config(config)})

        try:
            data = json.loads(request.body.decode('utf-8') if request.body else '{}')
        except (TypeError, ValueError, UnicodeDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

        if 'enabled' in data:
            config.enabled = bool(data.get('enabled'))
        if 'permanent' in data:
            config.permanent = bool(data.get('permanent'))
        if 'check_interval' in data:
            try:
                interval = int(data.get('check_interval'))
            except (TypeError, ValueError):
                interval = config.check_interval
            config.check_interval = max(30, min(interval, 3600))
        if 'jail' in data:
            jail = str(data.get('jail') or 'sshd').strip()
            if jail:
                config.jail = jail[:64]
        config.save()

        if config.enabled:
            auto_ban.start_autoban_monitor()
        else:
            auto_ban.stop_autoban_monitor()

        return JsonResponse({
            'success': True,
            'data': _serialize_config(Fail2banAutoBanConfig.get_config()),
            'message': 'Auto-ban settings saved',
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_autoban_run_now(request):
    """Run one auto-ban pass immediately (even if disabled, for manual refresh)."""
    try:
        banned = auto_ban.run_autoban_once(force=True)
        config = Fail2banAutoBanConfig.get_config()
        return JsonResponse({
            'success': True,
            'data': {
                'banned': banned,
                'config': _serialize_config(config),
                'ran_at': timezone.now().isoformat(),
            },
        })
    except Exception as e:
        return json_server_error(request, e)
