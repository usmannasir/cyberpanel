# -*- coding: utf-8 -*-
"""
Standalone Fail2ban Auto Ban monitor (systemd).

Kept outside LSCPD workers to avoid UDS deadlocks with ProcessUtilities.
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


def run_loop():
    # Absolute imports: this file is executed as a script by systemd.
    from fail2ban.auto_ban import run_autoban_once, _sleep_interruptible
    from fail2ban.models import Fail2banAutoBanConfig
    import logging

    logger = logging.getLogger('fail2ban_plugin')
    logger.info('fail2ban auto-ban systemd monitor started')
    while True:
        try:
            config = Fail2banAutoBanConfig.get_config()
            if not config.enabled:
                _sleep_interruptible(15)
                continue
            run_autoban_once()
            interval = max(30, min(int(config.check_interval or 60), 3600))
            _sleep_interruptible(interval)
        except Exception as e:
            logger.error('fail2ban auto-ban systemd monitor error: %s', e)
            _sleep_interruptible(30)


def main():
    _django_setup()
    run_loop()


if __name__ == '__main__':
    main()
