# -*- coding: utf-8 -*-
"""
Background auto-ban for SSH Security Alerts (dashboard Recent SSH Logs).

When Fail2banAutoBanConfig.enabled is True, cyberpanel-fail2ban-autoban.service
periodically bans alert IPs via fail2ban + firewall (outside LSCPD workers).
"""
from __future__ import annotations

import fcntl
import logging
import os
import threading
import time

logger = logging.getLogger('fail2ban_plugin')

_monitor_thread = None
_monitor_lock = threading.Lock()
_LOCK_PATH = '/tmp/cyberpanel-fail2ban-autoban.lock'


def _sleep_interruptible(seconds):
    end = time.time() + max(5, int(seconds))
    while time.time() < end:
        time.sleep(min(5, end - time.time()))


def _already_handled(ip, hours=2):
    """Skip IPs banned recently by this plugin or still active in jail/DB/firewall."""
    try:
        from datetime import timedelta
        from django.utils import timezone
        from .models import BannedIP, SecurityEvent
        from .utils import Fail2banManager

        since = timezone.now() - timedelta(hours=hours)
        if BannedIP.objects.filter(ip_address=ip, is_active=True).exists():
            return True
        try:
            from firewall.models import BannedIP as FirewallBannedIP
            if FirewallBannedIP.objects.filter(ip_address=ip, active=True).exists():
                return True
        except Exception:
            pass
        if SecurityEvent.objects.filter(
            ip_address=ip,
            event_type='ban',
            created_at__gte=since,
        ).exists():
            return True
        try:
            manager = Fail2banManager()
            for row in manager.get_banned_ips(include_firewall=False) or []:
                tip = row.get('ip') if isinstance(row, dict) else None
                if tip == ip:
                    return True
        except Exception:
            pass
    except Exception:
        pass
    return False


def _firewall_drop_no_reload(ip):
    """
    Add a permanent firewalld drop rule without reloading.
    Returns: 'added' | 'exists' | 'error'
    """
    try:
        from plogical.processUtilities import ProcessUtilities
        check = ProcessUtilities.outputExecutioner('firewall-cmd --list-rich-rules')
        if isinstance(check, tuple):
            check = check[1] if len(check) > 1 else check[0]
        if ip in str(check or ''):
            return 'exists'
        rule = (
            'firewall-cmd --permanent --zone=public '
            '--add-rich-rule=\'rule family="ipv4" source address="%s" drop\''
            % ip
        )
        if ProcessUtilities.executioner(rule) == 1:
            return 'added'
        return 'error'
    except Exception:
        return 'error'


def _firewall_reload():
    try:
        from plogical.processUtilities import ProcessUtilities
        # Soft timeout wrapper: reload can be slow with many rich rules.
        return ProcessUtilities.executioner('timeout 45 firewall-cmd --reload') == 1
    except Exception:
        return False


def _whitelist_set():
    out = set()
    try:
        from .models import Fail2banSettings
        for row in Fail2banSettings.objects.all()[:20]:
            for part in (row.whitelist_ips or '').replace(',', '\n').splitlines():
                ip = part.strip()
                if ip:
                    out.add(ip)
    except Exception:
        pass
    try:
        from .utils import Fail2banManager
        for row in Fail2banManager().get_merged_whitelist():
            ip = (row.get('ip') if isinstance(row, dict) else row) or ''
            ip = str(ip).strip()
            if ip:
                out.add(ip)
    except Exception:
        pass
    try:
        from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
        out |= SSHSecurityWhitelistUtilities.ip_set()
    except Exception:
        pass
    return out


def run_autoban_once(force=False):
    """Scan alerts and ban new IPs. Returns number banned."""
    from django.utils import timezone
    from .models import Fail2banAutoBanConfig, SecurityEvent
    from .ssh_alerts import analyze_ssh_security_alerts, extract_alert_ips
    from .utils import Fail2banManager

    config = Fail2banAutoBanConfig.get_config()
    if not force and not config.enabled:
        return 0

    alerts = analyze_ssh_security_alerts()
    ips = extract_alert_ips(alerts)
    whitelist = _whitelist_set()
    manager = Fail2banManager()
    jail = (config.jail or 'sshd').strip() or 'sshd'
    banned = 0
    errors = []
    need_fw_reload = False

    # Cache fail2ban banned set once per pass
    banned_now = set()
    try:
        for row in manager.get_banned_ips(include_firewall=False) or []:
            tip = row.get('ip') if isinstance(row, dict) else None
            if tip:
                banned_now.add(tip)
    except Exception:
        pass

    for ip in ips:
        if ip in whitelist or ip in banned_now or _already_handled(ip):
            continue
        try:
            result = manager.ban_ip(ip, jail=jail)
            fw_ok = True
            if config.permanent:
                fw_state = _firewall_drop_no_reload(ip)
                fw_ok = fw_state in ('added', 'exists')
                if fw_state == 'added':
                    need_fw_reload = True
                    try:
                        block_log = '/usr/local/CyberCP/data/blocked_ips.log'
                        from datetime import datetime
                        os.makedirs(os.path.dirname(block_log), exist_ok=True)
                        with open(block_log, 'a') as fh:
                            fh.write(
                                '%s - %s - Auto-ban: SSH security alert\n'
                                % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip)
                            )
                    except Exception:
                        pass
            ok = bool(result.get('success')) or bool(fw_ok)
            if ok:
                banned += 1
                banned_now.add(ip)
                try:
                    SecurityEvent.objects.create(
                        event_type='ban',
                        ip_address=ip,
                        jail_name=jail,
                        description='Auto-ban from SSH security alerts',
                        severity='high',
                    )
                except Exception:
                    pass
            else:
                errors.append('%s: %s' % (ip, result.get('error') or 'failed'))
        except Exception as e:
            errors.append('%s: %s' % (ip, e))

    if need_fw_reload:
        if not _firewall_reload():
            errors.append('firewall reload failed or timed out')

    config.last_run_at = timezone.now()
    config.last_banned_count = banned
    config.last_error = '; '.join(errors[:5])
    config.save(update_fields=['last_run_at', 'last_banned_count', 'last_error', 'updated_at'])
    if banned:
        logger.info('fail2ban auto-ban banned %s IP(s)', banned)
    return banned


def _monitor_loop():
    logger.info('fail2ban auto-ban monitor started')
    while True:
        try:
            from .models import Fail2banAutoBanConfig
            config = Fail2banAutoBanConfig.get_config()
            if not config.enabled:
                _sleep_interruptible(15)
                continue
            run_autoban_once()
            interval = max(30, min(int(config.check_interval or 60), 3600))
            _sleep_interruptible(interval)
        except Exception as e:
            logger.error('fail2ban auto-ban monitor error: %s', e)
            _sleep_interruptible(30)


def start_autoban_monitor():
    """Start Fail2ban Auto Ban via systemd (outside LSCPD workers)."""
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner('systemctl enable cyberpanel-fail2ban-autoban.service')
        ProcessUtilities.executioner('systemctl restart cyberpanel-fail2ban-autoban.service')
        logger.info('fail2ban auto-ban: started cyberpanel-fail2ban-autoban.service')
    except Exception as e:
        logger.error('fail2ban auto-ban: could not start systemd unit: %s', e)


def stop_autoban_monitor():
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner('systemctl stop cyberpanel-fail2ban-autoban.service')
    except Exception as e:
        logger.error('fail2ban auto-ban: could not stop systemd unit: %s', e)


def ensure_autoban_monitor_if_enabled():
    """
    Do not start in-process threads from AppConfig.ready().

    Enabling the feature from the plugin UI (or ops) starts the systemd unit.
    """
    return
