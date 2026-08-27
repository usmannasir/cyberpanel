# -*- coding: utf-8 -*-
"""
SSH security alert analysis for Fail2ban plugin.

Mirrors CyberPanel dashboard Recent SSH Logs alerts, but returns every
attacker IP (not only Top IP) so Ban All can cover root login attempts.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict


def _log_path():
    try:
        from plogical.processUtilities import ProcessUtilities
        distro = ProcessUtilities.decideDistro()
        if distro in (ProcessUtilities.ubuntu, ProcessUtilities.ubuntu20):
            return '/var/log/auth.log'
    except Exception:
        pass
    return '/var/log/secure'


def _read_log_lines(max_lines=500):
    path = _log_path()
    try:
        from plogical.processUtilities import ProcessUtilities
        n = max(50, min(int(max_lines), 2000))
        output = ProcessUtilities.outputExecutioner('tail -n %s %s' % (n, path))
        if isinstance(output, tuple):
            output = output[1] if len(output) > 1 else output[0]
        return [ln for ln in str(output or '').split('\n') if ln.strip()]
    except Exception:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
            return [ln.rstrip('\n') for ln in lines[-max_lines:] if ln.strip()]
        except Exception:
            return []


def analyze_ssh_security_alerts(max_lines=500):
    """
    Return alert dicts compatible with dashboard Security Alerts UI, plus `ips`.
    """
    lines = _read_log_lines(max_lines=max_lines)
    failed_passwords = defaultdict(int)
    invalid_users = defaultdict(int)
    root_login_attempts = []

    for line in lines:
        if 'Failed password' in line:
            match = re.search(
                r'Failed password for (?:invalid user )?(\S+) from (\S+)',
                line,
            )
            if match:
                user, ip = match.groups()
                failed_passwords[ip] += 1
                if user == 'root':
                    root_login_attempts.append({'ip': ip, 'line': line})
        elif 'Invalid user' in line or 'invalid user' in line:
            match = re.search(r'[Ii]nvalid user (\S+) from (\S+)', line)
            if match:
                _user, ip = match.groups()
                invalid_users[ip] += 1

    alerts = []

    for ip, count in failed_passwords.items():
        if count >= 10:
            alerts.append({
                'title': 'Brute Force Attack Detected',
                'description': (
                    'IP address %s has made %s failed password attempts. '
                    'This indicates a potential brute force attack.'
                ) % (ip, count),
                'severity': 'high',
                'details': {
                    'IP Address': ip,
                    'Failed Attempts': count,
                    'Attack Type': 'Brute Force',
                },
                'ips': [ip],
                'recommendation': 'Ban this IP in fail2ban (sshd) and permanently in the firewall.',
            })

    if root_login_attempts:
        counts = Counter(r['ip'] for r in root_login_attempts)
        unique_ips = [ip for ip, _c in counts.most_common()]
        top_ip = unique_ips[0]
        alerts.append({
            'title': 'Root Login Attempts Detected',
            'description': (
                'Direct root login attempts detected from %s IP addresses. '
                'Root SSH access should be disabled.'
            ) % len(unique_ips),
            'severity': 'high',
            'details': {
                'Unique IPs': len(unique_ips),
                'Total Attempts': len(root_login_attempts),
                'Top IP': top_ip,
                'IP Address': top_ip,
                'All IPs': ', '.join(unique_ips[:30]),
            },
            'ips': unique_ips,
            'recommendation': (
                'Disable root SSH login (PermitRootLogin no). '
                'Ban all listed IPs via fail2ban + firewall.'
            ),
        })

    for ip, count in invalid_users.items():
        if count >= 5:
            alerts.append({
                'title': 'Dictionary Attack Detected',
                'description': (
                    'IP address %s attempted to login with %s non-existent usernames.'
                ) % (ip, count),
                'severity': 'medium',
                'details': {
                    'IP Address': ip,
                    'Invalid User Attempts': count,
                    'Attack Type': 'Dictionary Attack',
                },
                'ips': [ip],
                'recommendation': 'Ban this IP and consider tightening SSH (keys only, non-standard port).',
            })

    return alerts


def extract_alert_ips(alerts):
    """Unique IPs from alert list (preserves first-seen order)."""
    seen = set()
    ordered = []
    for alert in alerts or []:
        for ip in alert.get('ips') or []:
            if ip and ip not in seen:
                seen.add(ip)
                ordered.append(ip)
        details = alert.get('details') or {}
        for key in ('IP Address', 'Top IP'):
            ip = details.get(key)
            if ip and ip not in seen and re.match(r'^[0-9a-fA-F:.]+$', str(ip)):
                seen.add(ip)
                ordered.append(ip)
    return ordered
