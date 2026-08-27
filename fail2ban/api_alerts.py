# -*- coding: utf-8 -*-
"""SSH alert APIs for Fail2ban plugin (dashboard Security Alerts integration)."""
import json
import uuid
import logging as pylogging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import SecurityEvent
from .utils import Fail2banManager
from .ssh_alerts import analyze_ssh_security_alerts, extract_alert_ips
from .panel_auth import fail2ban_api, json_server_error

logger = pylogging.getLogger('fail2ban_plugin')


@fail2ban_api
@require_http_methods(["GET"])
def api_ssh_alerts(request):
    """List SSH security alerts (same class of signals as dashboard Recent SSH Logs)."""
    try:
        alerts = analyze_ssh_security_alerts()
        manager = Fail2banManager()
        banned = set()
        try:
            for row in manager.get_banned_ips(include_firewall=False) or []:
                ip = row.get('ip') if isinstance(row, dict) else None
                if ip:
                    banned.add(ip)
        except Exception:
            banned = set()

        for alert in alerts:
            for ip in alert.get('ips') or []:
                alert.setdefault('ban_status', {})[ip] = 'banned' if ip in banned else 'open'

        return JsonResponse({
            'success': True,
            'data': {
                'alerts': alerts,
                'ips': extract_alert_ips(alerts),
                'note': (
                    'Dashboard Security Alerts do not auto-ban via fail2ban. '
                    'Fail2ban bans after maxretry failures; use Ban All for alert IPs.'
                ),
            },
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_ban_alert_ips(request):
    """
    Ban one or many alert IPs via fail2ban + permanent firewall rule.
    Body: {"ips": ["1.2.3.4", ...], "permanent": true, "jail": "sshd"}
    If ips omitted, bans all current alert IPs.
    """
    try:
        try:
            data = json.loads(request.body.decode('utf-8') if request.body else '{}')
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

        permanent = bool(data.get('permanent', True))
        jail = (data.get('jail') or 'sshd').strip() or 'sshd'
        ips = data.get('ips')
        if not ips:
            ips = extract_alert_ips(analyze_ssh_security_alerts())
        if isinstance(ips, str):
            ips = [ips]
        if not isinstance(ips, (list, tuple)) or not ips:
            return JsonResponse({
                'success': False,
                'error': 'No IPs to ban',
            }, status=400)

        manager = Fail2banManager()
        results = []
        banned_ok = 0
        for raw in ips:
            ip = str(raw).strip()
            if not ip:
                continue
            if permanent:
                result = manager.ban_ip_permanent(
                    ip,
                    jail=jail,
                    reason='SSH security alert (fail2ban plugin)',
                )
            else:
                result = manager.ban_ip(ip, jail=jail)
            ok = bool(result.get('success'))
            if ok:
                banned_ok += 1
                try:
                    SecurityEvent.objects.create(
                        event_type='ban',
                        ip_address=ip,
                        jail_name=jail,
                        description='Alert ban: %s' % result.get('message', ip),
                        severity='high',
                    )
                except Exception:
                    pass
            else:
                error_id = str(uuid.uuid4())[:12]
                logger.error(
                    'alert ban failed error_id=%s ip=%s detail=%s',
                    error_id,
                    ip,
                    result.get('error') or result,
                )
                result = dict(result)
                result['error_id'] = error_id
            results.append({'ip': ip, 'result': result})

        return JsonResponse({
            'success': banned_ok > 0,
            'data': {
                'banned': banned_ok,
                'total': len(results),
                'results': results,
            },
            'error': None if banned_ok else 'No IPs were banned',
        }, status=200 if banned_ok else 400)
    except Exception as e:
        return json_server_error(request, e)
