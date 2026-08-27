# -*- coding: utf-8 -*-
"""JSON API views for Fail2ban plugin (CyberPanel admin session required)."""
import json
import re
import subprocess
import uuid
import logging as pylogging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Fail2banSettings, SecurityEvent
from .utils import Fail2banManager
from .panel_auth import (
    fail2ban_api,
    json_server_error,
)

logger = pylogging.getLogger('fail2ban_plugin')


@fail2ban_api
@require_http_methods(["GET"])
def api_status(request):
    """Get fail2ban service status"""
    try:
        manager = Fail2banManager()
        status = manager.get_status()
        return JsonResponse({
            'success': True,
            'data': status
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET"])
def api_jails(request):
    """Get all jails information"""
    try:
        manager = Fail2banManager()
        jails = manager.get_jails()
        return JsonResponse({
            'success': True,
            'data': jails
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET"])
def api_banned_ips(request):
    """Get banned IPs (fail2ban jails + optional firewall merge) with pagination/search."""
    try:
        manager = Fail2banManager()
        include_firewall = str(request.GET.get('include_firewall', '1')).lower() in (
            '1', 'true', 'yes', 'on'
        )
        source = (request.GET.get('source') or 'all').strip().lower()
        q = (request.GET.get('q') or request.GET.get('search') or '').strip()
        try:
            limit = int(request.GET.get('limit') or 50)
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int(request.GET.get('offset') or 0)
        except (TypeError, ValueError):
            offset = 0
        limit = max(1, min(200, limit))
        offset = max(0, offset)

        if source == 'fail2ban':
            include_firewall = False
        elif source == 'firewall':
            fw_total = manager.count_firewall_bans(q=q)
            data = manager.query_firewall_banned_page(limit=limit, offset=offset, q=q)
            return JsonResponse({
                'success': True,
                'data': data,
                'meta': {
                    'total': fw_total,
                    'offset': offset,
                    'limit': limit,
                    'q': q,
                    'source': 'firewall',
                    'fail2ban_count': 0,
                    'firewall_count': fw_total,
                    'page': (offset // limit) + 1,
                    'pages': max(1, (fw_total + limit - 1) // limit),
                },
            })

        page = manager.get_banned_ips_page(
            include_firewall=include_firewall,
            limit=limit,
            offset=offset,
            q=q,
        )
        total = int(page.get('total') or 0)
        return JsonResponse({
            'success': True,
            'data': page.get('data') or [],
            'meta': {
                'total': total,
                'offset': offset,
                'limit': limit,
                'q': q,
                'source': source,
                'fail2ban_count': page.get('fail2ban_count') or 0,
                'firewall_count': page.get('firewall_count') or 0,
                'page': (offset // limit) + 1,
                'pages': max(1, (total + limit - 1) // limit) if total else 1,
            },
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_sync_firewall_bans(request):
    """Batch-import active firewall bans into a fail2ban jail."""
    try:
        manager = Fail2banManager()
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        jail = payload.get('jail') or request.POST.get('jail') or 'sshd'
        limit = payload.get('limit', request.POST.get('limit', 100))
        offset = payload.get('offset', request.POST.get('offset', 0))
        result = manager.import_firewall_bans_to_jail(jail=jail, limit=limit, offset=offset)
        return JsonResponse({'success': True, 'data': result})
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET", "POST", "DELETE"])
def api_whitelist(request):
    """Manage whitelist IPs (fail2ban ignoreip + firewall SSH trusted mirror)."""
    try:
        manager = Fail2banManager()

        if request.method == 'GET':
            sync_note = ''
            try:
                sync_result = manager.sync_firewall_whitelist_into_ignoreip(restart=False)
                added = sync_result.get('added') or []
                if added:
                    sync_note = 'Synced %d firewall trusted IP(s) into fail2ban ignoreip.' % len(added)
                elif sync_result.get('error'):
                    sync_note = 'Firewall whitelist sync issue: %s' % sync_result.get('error')
            except Exception as sync_exc:
                sync_note = 'Firewall whitelist sync issue: %s' % sync_exc
            rows = manager.get_merged_whitelist()
            return JsonResponse({
                'success': True,
                'data': rows,
                'meta': {
                    'count': len(rows),
                    'sources': ['fail2ban', 'firewall', 'plugin'],
                    'note': 'Mirrors Firewall SSH trusted IPs and fail2ban ignoreip. Up to 2000 entries supported.',
                    'firewall_synced_into_ignoreip': sync_note,
                }
            })

        data = {}
        try:
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}

        if request.method == 'POST':
            # Bulk import: {ips: [...]} or {ips_text: "a\nb"} or single {ip}
            ips = data.get('ips')
            if isinstance(ips, str):
                ips = re.split(r'[\s,;]+', ips)
            if not ips and data.get('ips_text'):
                ips = re.split(r'[\s,;]+', str(data.get('ips_text')))
            label = (data.get('label') or '').strip()
            sync_firewall = data.get('sync_firewall', True)
            if isinstance(sync_firewall, str):
                sync_firewall = sync_firewall.lower() in ('1', 'true', 'yes', 'on')

            if ips:
                cleaned = [x.strip() for x in ips if (x or '').strip()]
                if len(cleaned) > 2000:
                    return JsonResponse({
                        'success': False,
                        'error': 'Too many IPs in one request (max 2000)'
                    }, status=400)
                result = manager.add_many_to_whitelist(
                    cleaned, label=label, sync_firewall=bool(sync_firewall)
                )
                return JsonResponse({'success': bool(result.get('success')), 'data': result,
                                    'error': result.get('error')},
                                   status=200 if result.get('success') else 400)

            ip = (data.get('ip') or '').strip()
            if not ip:
                return JsonResponse({
                    'success': False,
                    'error': 'IP address is required'
                }, status=400)

            result = manager.add_to_whitelist(
                ip, label=label, sync_firewall=bool(sync_firewall)
            )
            return JsonResponse({
                'success': bool(result.get('success')),
                'data': result,
                'error': result.get('error')
            }, status=200 if result.get('success') else 400)

        elif request.method == 'DELETE':
            ip = (data.get('ip') or '').strip()
            if not ip:
                return JsonResponse({
                    'success': False,
                    'error': 'IP address is required'
                }, status=400)
            layers = (data.get('layers') or 'both').strip().lower()
            sync_firewall = data.get('sync_firewall', True)
            if isinstance(sync_firewall, str):
                sync_firewall = sync_firewall.lower() in ('1', 'true', 'yes', 'on')
            remove_fail2ban = True
            if layers in ('firewall', 'fw'):
                remove_fail2ban = False
                sync_firewall = True
            elif layers in ('fail2ban', 'f2b', 'ignoreip'):
                remove_fail2ban = True
                sync_firewall = False
            elif layers in ('both', 'all', ''):
                remove_fail2ban = True
                sync_firewall = True if data.get('sync_firewall') is None else bool(sync_firewall)
            result = manager.remove_from_whitelist(
                ip,
                sync_firewall=bool(sync_firewall),
                remove_fail2ban=bool(remove_fail2ban),
            )
            return JsonResponse({
                'success': bool(result.get('success')),
                'data': result,
                'error': result.get('error')
            }, status=200 if result.get('success') else 400)

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET", "POST", "DELETE"])
def api_blacklist(request):
    """Manage blacklist IPs"""
    try:
        manager = Fail2banManager()

        if request.method == 'GET':
            blacklist = manager.get_blacklist()
            return JsonResponse({
                'success': True,
                'data': blacklist
            })

        elif request.method == 'POST':
            data = json.loads(request.body)
            ip = data.get('ip')
            if not ip:
                return JsonResponse({
                    'success': False,
                    'error': 'IP address is required'
                }, status=400)

            result = manager.add_to_blacklist(ip)
            return JsonResponse({
                'success': True,
                'data': result
            })

        elif request.method == 'DELETE':
            data = json.loads(request.body)
            ip = data.get('ip')
            if not ip:
                return JsonResponse({
                    'success': False,
                    'error': 'IP address is required'
                }, status=400)

            result = manager.remove_from_blacklist(ip)
            return JsonResponse({
                'success': True,
                'data': result
            })

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_ban_ip(request):
    """Ban an IP address (optional permanent firewall dual-ban)."""
    try:
        data = json.loads(request.body)
        ip = data.get('ip')
        jail = data.get('jail', 'sshd')
        permanent = bool(data.get('permanent', False))

        if not ip:
            return JsonResponse({
                'success': False,
                'error': 'IP address is required'
            }, status=400)

        manager = Fail2banManager()
        if permanent:
            result = manager.ban_ip_permanent(
                ip,
                jail=jail,
                reason=data.get('reason') or 'Manual permanent ban from fail2ban plugin',
            )
        else:
            result = manager.ban_ip(ip, jail)

        if not result.get('success'):
            error_id = str(uuid.uuid4())[:12]
            logger.error(
                'ban_ip failed error_id=%s ip=%s jail=%s detail=%s',
                error_id,
                ip,
                jail,
                result.get('error', ''),
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Could not ban IP',
                    'error_id': error_id,
                },
                status=400,
            )

        SecurityEvent.objects.create(
            event_type='ban',
            ip_address=ip,
            jail_name=jail,
            description='IP %s manually banned from %s (permanent=%s)' % (ip, jail, permanent),
            severity='high'
        )

        return JsonResponse({
            'success': True,
            'data': result
        })

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_unban_ip(request):
    """Unban an IP from fail2ban and/or firewall layers."""
    try:
        data = json.loads(request.body)
        ip = (data.get('ip') or '').strip()
        jail = (data.get('jail') or 'sshd').strip() or 'sshd'
        if jail == 'firewall':
            jail = 'sshd'

        if not ip:
            return JsonResponse({
                'success': False,
                'error': 'IP address is required'
            }, status=400)

        layers = (data.get('layers') or '').strip().lower()
        also_firewall = data.get('also_firewall', data.get('unban_firewall', False))
        if isinstance(also_firewall, str):
            also_firewall = also_firewall.lower() in ('1', 'true', 'yes', 'on')

        unban_fail2ban = True
        unban_firewall = bool(also_firewall)
        if layers in ('firewall', 'fw'):
            unban_fail2ban = False
            unban_firewall = True
        elif layers in ('both', 'all'):
            unban_fail2ban = True
            unban_firewall = True
        elif layers in ('fail2ban', 'f2b', 'jail'):
            unban_fail2ban = True
            unban_firewall = False

        source = (data.get('source') or '').strip().lower()
        if source == 'firewall' and not layers:
            unban_fail2ban = False
            unban_firewall = True

        manager = Fail2banManager()
        result = manager.manage_unban(
            ip,
            jail=jail,
            unban_fail2ban=unban_fail2ban,
            unban_firewall=unban_firewall,
        )

        if not result.get('success'):
            error_id = str(uuid.uuid4())[:12]
            logger.error(
                'unban_ip failed error_id=%s ip=%s jail=%s detail=%s',
                error_id,
                ip,
                jail,
                result.get('error', ''),
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': result.get('error') or 'Could not unban IP',
                    'error_id': error_id,
                    'data': result,
                },
                status=400,
            )

        SecurityEvent.objects.create(
            event_type='unban',
            ip_address=ip,
            jail_name=jail,
            description='IP %s manually unbanned (fail2ban=%s, firewall=%s)' % (
                ip, unban_fail2ban, unban_firewall
            ),
            severity='medium'
        )

        return JsonResponse({
            'success': True,
            'data': result
        })

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_restart(request):
    """Restart fail2ban service"""
    try:
        manager = Fail2banManager()
        result = manager.restart_service()

        if not result.get('success'):
            error_id = str(uuid.uuid4())[:12]
            logger.error(
                'api_restart failed error_id=%s detail=%s',
                error_id,
                result.get('error', ''),
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Internal server error',
                    'error_id': error_id,
                },
                status=500,
            )

        SecurityEvent.objects.create(
            event_type='restart',
            ip_address='0.0.0.0',
            jail_name='system',
            description='Fail2ban service restarted',
            severity='medium'
        )

        return JsonResponse({
            'success': True,
            'data': result
        })

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET"])
def api_logs(request):
    """Get fail2ban logs (newest among last N file lines). Optional ?lines= (1..5000, default 500)."""
    try:
        try:
            n = int(request.GET.get('lines', 500))
        except (TypeError, ValueError):
            n = 500
        n = max(1, min(n, 5000))
        manager = Fail2banManager()
        logs = manager.get_logs(lines=n)
        return JsonResponse({
            'success': True,
            'data': logs,
            'meta': {'fetched': len(logs) if isinstance(logs, list) else 0, 'lines': n},
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_logs_clear(request):
    """Truncate /var/log/fail2ban.log after admin confirmation in the UI."""
    try:
        manager = Fail2banManager()
        result = manager.clear_logs()
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error') or 'Could not clear fail2ban.log',
            }, status=400)
        return JsonResponse({
            'success': True,
            'message': result.get('message') or 'Log cleared',
        })
    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["GET", "POST"])
def api_settings(request):
    """Get or update fail2ban settings (singleton). Whitelist mirrors firewall + ignoreip."""
    try:
        settings = Fail2banSettings.get_config()
        manager = Fail2banManager()

        if request.method == 'GET':
            merged = manager.get_merged_whitelist()
            # Prefer live mirrored list for the Settings textarea
            whitelist_text = '\n'.join(
                (row.get('ip') if isinstance(row, dict) else str(row))
                for row in merged
                if (row.get('ip') if isinstance(row, dict) else row)
            )
            if not whitelist_text:
                whitelist_text = settings.whitelist_ips or ''
            return JsonResponse({
                'success': True,
                'data': {
                    'email_notifications': settings.email_notifications,
                    'auto_ban_threshold': settings.auto_ban_threshold,
                    'ban_duration': settings.ban_duration,
                    'whitelist_ips': whitelist_text,
                    'whitelist_entries': merged,
                    'blacklist_ips': settings.blacklist_ips,
                    'enabled_jails': settings.enabled_jails,
                }
            })

        data = json.loads(request.body.decode('utf-8') if request.body else '{}')
        settings.email_notifications = data.get('email_notifications', settings.email_notifications)
        settings.auto_ban_threshold = data.get('auto_ban_threshold', settings.auto_ban_threshold)
        settings.ban_duration = data.get('ban_duration', settings.ban_duration)
        settings.whitelist_ips = data.get('whitelist_ips', settings.whitelist_ips)
        settings.blacklist_ips = data.get('blacklist_ips', settings.blacklist_ips)
        settings.enabled_jails = data.get('enabled_jails', settings.enabled_jails)
        settings.save()

        # Sync settings textarea into fail2ban ignoreip + firewall trusted IPs
        try:
            raw = (settings.whitelist_ips or '').replace(',', '\n')
            tokens = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if tokens:
                manager.add_many_to_whitelist(
                    tokens, label='From Fail2ban settings', sync_firewall=True
                )
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'data': 'Settings updated successfully'
        })

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_toggle_plugin(request):
    """Toggle plugin on/off"""
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', True)

        manager = Fail2banManager()

        if enabled:
            result = manager.start_service()
            action = 'enabled'
        else:
            result = manager.stop_service()
            action = 'disabled'

        if result.get('success', False):
            SecurityEvent.objects.create(
                event_type='plugin_toggle',
                ip_address='0.0.0.0',
                jail_name='system',
                description='Plugin %s by user' % action,
                severity='medium'
            )

            return JsonResponse({
                'success': True,
                'data': {
                    'enabled': enabled,
                    'message': 'Plugin %s successfully' % action
                }
            })
        else:
            error_id = str(uuid.uuid4())[:12]
            logger.error(
                'toggle_plugin failed error_id=%s action=%s detail=%s',
                error_id,
                action,
                result.get('error', ''),
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Internal server error',
                    'error_id': error_id,
                },
                status=500,
            )

    except Exception as e:
        return json_server_error(request, e)


@fail2ban_api
@require_http_methods(["POST"])
def api_restart_litespeed(request):
    """Restart LiteSpeed service"""
    try:
        result = subprocess.run(
            ['systemctl', 'restart', 'lshttpd'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            SecurityEvent.objects.create(
                event_type='service_restart',
                ip_address='0.0.0.0',
                jail_name='system',
                description='LiteSpeed service restarted by user',
                severity='medium'
            )

            return JsonResponse({
                'success': True,
                'data': {
                    'message': 'LiteSpeed service restarted successfully',
                }
            })
        else:
            error_id = str(uuid.uuid4())[:12]
            logger.error(
                'litespeed restart failed error_id=%s stderr=%s',
                error_id,
                (result.stderr or '')[:2000],
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Could not restart LiteSpeed',
                    'error_id': error_id,
                },
                status=500,
            )

    except subprocess.TimeoutExpired as e:
        return json_server_error(request, e)
    except Exception as e:
        return json_server_error(request, e)
