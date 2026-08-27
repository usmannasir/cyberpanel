# -*- coding: utf-8 -*-
"""
Standalone Auto Ban monitor (systemd).

Must NOT run inside LSCPD/lswsgi workers: ProcessUtilities UDS calls from a
busy worker deadlock the panel (all workers INUSE, /base hangs).
"""
from __future__ import annotations

import os
import sys
import time


def _django_setup():
    root = '/usr/local/CyberCP'
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    import django
    django.setup()


def run_autoban_cycle():
    """One scan/ban pass. Returns number of ban attempts."""
    from django.utils import timezone
    from datetime import timedelta
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
    from autoBanSecurityAlerts.models import AutoBanConfig, WhitelistedIP, AutoBanLog
    from autoBanSecurityAlerts.views import (
        ensure_machine_ip_whitelisted,
        get_security_alerts,
        extract_ips_from_alerts,
        auto_ban_ip,
    )

    config = AutoBanConfig.get_config()
    if not config.enabled:
        return 0

    try:
        ensure_machine_ip_whitelisted()
    except Exception as e:
        logging.writeToFile('Auto Ban monitor: whitelist ensure failed: %s' % e)

    alerts = get_security_alerts()
    if not alerts:
        return 0

    alert_ips = extract_ips_from_alerts(alerts)
    whitelisted = set(WhitelistedIP.objects.values_list('ip_address', flat=True))
    recent = set(
        AutoBanLog.objects.filter(
            banned_at__gte=timezone.now() - timedelta(hours=1)
        ).values_list('ip_address', flat=True)
    )

    try:
        from firewall.models import BannedIP
        already = set(
            BannedIP.objects.filter(active=True).values_list('ip_address', flat=True)
        )
    except Exception:
        already = set()

    banned = 0
    for info in alert_ips:
        ip = info['ip']
        if ip in whitelisted or ip in recent or ip in already:
            continue
        if auto_ban_ip(ip, info['type'], 'Auto-banned: %s' % info['type']):
            banned += 1
            already.add(ip)
    return banned


def run_loop():
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
    from autoBanSecurityAlerts.models import AutoBanConfig

    logging.writeToFile('Auto Ban monitor: systemd service started')
    while True:
        try:
            config = AutoBanConfig.get_config()
            if not config.enabled:
                time.sleep(15)
                continue
            n = run_autoban_cycle()
            if n:
                logging.writeToFile('Auto Ban monitor: banned %s IP(s)' % n)
            interval = max(30, min(int(config.check_interval or 60), 3600))
            time.sleep(interval)
        except Exception as e:
            logging.writeToFile('Auto Ban monitor: loop error: %s' % e)
            time.sleep(30)


def main():
    _django_setup()
    run_loop()


if __name__ == '__main__':
    main()
