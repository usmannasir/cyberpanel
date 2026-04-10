#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""
SSH Security Analysis — IPs that must never be blocked (firewalld drop / Banned IPs).

Stored in /usr/local/CyberCP/data/ssh_security_whitelist.json as a JSON array of objects:
  [{"ip": "203.0.113.10", "label": "Office", "updated": 1710000000}, ...]
"""
from __future__ import annotations

import ipaddress
import json
import os
import time
from typing import Any, Dict, List, Optional, Set

WHITELIST_PATH = '/usr/local/CyberCP/data/ssh_security_whitelist.json'
PUBLIC_IP_CACHE_PATH = '/usr/local/CyberCP/data/ssh_whitelist_public_ipv4.cache.json'
FIRST_ADMIN_LOGIN_FLAG_PATH = '/usr/local/CyberCP/data/ssh_whitelist_first_admin_login.recorded'
LABEL_SERVER_AUTO = 'CyberPanel server public IPv4 (auto)'
LABEL_FIRST_ADMIN_AUTO = 'First CyberPanel admin login (auto)'


class SSHSecurityWhitelistUtilities:
    """Load/save trusted IPs for SSH security analysis and firewall ban protection."""

    @staticmethod
    def _ensure_data_dir() -> None:
        d = os.path.dirname(WHITELIST_PATH)
        if d:
            try:
                os.makedirs(d, mode=0o750, exist_ok=True)
            except OSError:
                pass

    @staticmethod
    def normalize_ip(ip: str) -> str:
        raw = (ip or '').strip()
        if not raw:
            return ''
        host = raw.split('/')[0].strip()
        if '%' in host:
            host = host.split('%', 1)[0]
        if host.startswith('[') and host.endswith(']'):
            host = host[1:-1]
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            return ''

    @staticmethod
    def normalized_ip_in_whitelist(raw_ip: str, wl_set: Set[str]) -> bool:
        """True if raw IP from a log line normalizes to an address in wl_set."""
        if not raw_ip or not wl_set:
            return False
        norm = SSHSecurityWhitelistUtilities.normalize_ip(raw_ip)
        return bool(norm and norm in wl_set)

    @staticmethod
    def validate_ip(ip: str) -> Optional[str]:
        norm = SSHSecurityWhitelistUtilities.normalize_ip(ip)
        if not norm:
            return None
        try:
            obj = ipaddress.ip_address(norm)
        except ValueError:
            return None
        if (
            obj.is_private
            or obj.is_loopback
            or obj.is_link_local
            or obj.is_multicast
            or obj.is_reserved
        ):
            return None
        return norm

    @staticmethod
    def load_entries() -> List[Dict[str, Any]]:
        SSHSecurityWhitelistUtilities._ensure_data_dir()
        if not os.path.isfile(WHITELIST_PATH):
            return []
        try:
            with open(WHITELIST_PATH, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            out: List[Dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                ip = item.get('ip') or item.get('address')
                norm = SSHSecurityWhitelistUtilities.normalize_ip(str(ip) if ip else '')
                if not norm:
                    continue
                label = (item.get('label') or item.get('note') or '').strip()
                updated = item.get('updated') or item.get('modified') or 0
                try:
                    updated = int(updated)
                except (TypeError, ValueError):
                    updated = 0
                out.append({'ip': norm, 'label': label, 'updated': updated})
            return out
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def save_entries(entries: List[Dict[str, Any]]) -> bool:
        SSHSecurityWhitelistUtilities._ensure_data_dir()
        try:
            serializable = []
            for e in entries:
                serializable.append({
                    'ip': e['ip'],
                    'label': e.get('label') or '',
                    'updated': int(e.get('updated') or 0),
                })
            tmp = WHITELIST_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(serializable, f, indent=2, ensure_ascii=False)
                f.write('\n')
            os.replace(tmp, WHITELIST_PATH)
            try:
                os.chmod(WHITELIST_PATH, 0o640)
            except OSError:
                pass
            try:
                import pwd
                import grp
                uid = pwd.getpwnam('cyberpanel').pw_uid
                gid = grp.getgrnam('cyberpanel').gr_gid
                os.chown(WHITELIST_PATH, uid, gid)
            except (OSError, KeyError, ImportError):
                pass
            return True
        except OSError:
            return False

    @staticmethod
    def ip_set() -> Set[str]:
        return {e['ip'] for e in SSHSecurityWhitelistUtilities.load_entries()}

    @staticmethod
    def is_whitelisted(ip: str) -> bool:
        norm = SSHSecurityWhitelistUtilities.normalize_ip(ip)
        if not norm:
            return False
        return norm in SSHSecurityWhitelistUtilities.ip_set()

    @staticmethod
    def add_entry(ip: str, label: str = '') -> tuple:
        v = SSHSecurityWhitelistUtilities.validate_ip(ip)
        if not v:
            return False, 'Invalid or non-public IP address'
        entries = SSHSecurityWhitelistUtilities.load_entries()
        label = (label or '').strip()[:200]
        now = int(time.time())
        for e in entries:
            if e['ip'] == v:
                e['label'] = label
                e['updated'] = now
                if not SSHSecurityWhitelistUtilities.save_entries(entries):
                    return False, 'Failed to save whitelist'
                return True, v
        entries.append({'ip': v, 'label': label, 'updated': now})
        if not SSHSecurityWhitelistUtilities.save_entries(entries):
            return False, 'Failed to save whitelist'
        return True, v

    @staticmethod
    def remove_entry(ip: str) -> tuple:
        norm = SSHSecurityWhitelistUtilities.normalize_ip(ip)
        if not norm:
            return False, 'Invalid IP address'
        entries = SSHSecurityWhitelistUtilities.load_entries()
        new_list = [e for e in entries if e['ip'] != norm]
        if len(new_list) == len(entries):
            return False, 'IP not found in whitelist'
        if not SSHSecurityWhitelistUtilities.save_entries(new_list):
            return False, 'Failed to save whitelist'
        return True, norm

    @staticmethod
    def update_entry(ip: str, new_ip: Optional[str] = None, label: Optional[str] = None) -> tuple:
        """
        Update whitelist row. Returns (ok, ip_or_error_message, unchanged).
        unchanged is True when nothing differed from stored values (still success).
        """
        norm = SSHSecurityWhitelistUtilities.normalize_ip(ip)
        if not norm:
            return False, 'Invalid IP address', False
        entries = SSHSecurityWhitelistUtilities.load_entries()
        idx = next((i for i, e in enumerate(entries) if e['ip'] == norm), -1)
        if idx < 0:
            return False, 'IP not found in whitelist', False
        now = int(time.time())
        target_ip = norm
        changed = False
        current_label = str(entries[idx].get('label') or '').strip()[:200]

        if new_ip is not None and str(new_ip).strip():
            v = SSHSecurityWhitelistUtilities.validate_ip(str(new_ip).strip())
            if not v:
                return False, 'Invalid or non-public new IP address', False
            if any(e['ip'] == v for e in entries if e['ip'] != norm):
                return False, 'New IP already listed', False
            if v != norm:
                entries[idx]['ip'] = v
                target_ip = v
                changed = True

        if label is not None:
            new_l = str(label).strip()[:200]
            if new_l != current_label:
                entries[idx]['label'] = new_l
                changed = True

        if not changed:
            return True, norm, True

        entries[idx]['updated'] = now
        if not SSHSecurityWhitelistUtilities.save_entries(entries):
            return False, 'Failed to save whitelist', False
        return True, target_ip, False

    @staticmethod
    def client_ip_from_request(request: Any) -> str:
        """Best-effort client IP for whitelisting (CF header or REMOTE_ADDR)."""
        if request is None:
            return ''
        try:
            meta = getattr(request, 'META', None) or {}
            raw = meta.get('HTTP_CF_CONNECTING_IP') or meta.get('REMOTE_ADDR') or ''
            raw = str(raw).split(',')[0].strip()
            if '%' in raw:
                raw = raw.split('%')[0]
            return raw
        except Exception:
            return ''

    @staticmethod
    def upsert_whitelist_ip_if_absent(ip: str, label: str) -> bool:
        """
        Add public IP to whitelist only if not already listed (does not overwrite labels).
        """
        v = SSHSecurityWhitelistUtilities.validate_ip(ip)
        if not v:
            return False
        entries = SSHSecurityWhitelistUtilities.load_entries()
        label = (label or '').strip()[:200]
        now = int(time.time())
        for e in entries:
            if e['ip'] == v:
                return True
        entries.append({'ip': v, 'label': label, 'updated': now})
        return SSHSecurityWhitelistUtilities.save_entries(entries)

    @staticmethod
    def _fetch_ipv4_public_ip() -> str:
        import re
        import urllib.request

        urls = (
            'https://ipv4.icanhazip.com',
            'https://api.ipify.org',
            'https://checkip.amazonaws.com',
        )
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    ip = resp.read().decode('utf-8', errors='replace').strip()
                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                    return ip
            except Exception:
                continue
        return ''

    @staticmethod
    def ensure_cyberpanel_public_ip_whitelisted(max_cache_age: int = 3600) -> None:
        """
        Ensure this machine's outbound/public IPv4 is on the whitelist (SSH + ban protection).
        Uses a short-lived cache to avoid HTTP self-lookups on every request.
        """
        SSHSecurityWhitelistUtilities._ensure_data_dir()
        now = int(time.time())
        cached_ip = ''
        cache_ts = 0
        try:
            if os.path.isfile(PUBLIC_IP_CACHE_PATH):
                with open(PUBLIC_IP_CACHE_PATH, 'r', encoding='utf-8', errors='replace') as fc:
                    cj = json.load(fc)
                if isinstance(cj, dict):
                    cached_ip = str(cj.get('ip') or '').strip()
                    try:
                        cache_ts = int(cj.get('ts') or 0)
                    except (TypeError, ValueError):
                        cache_ts = 0
        except (OSError, json.JSONDecodeError):
            pass

        ip_to_try = ''
        if cached_ip and (now - cache_ts) < max_cache_age:
            ip_to_try = cached_ip
        else:
            detected = SSHSecurityWhitelistUtilities._fetch_ipv4_public_ip()
            if detected:
                ip_to_try = detected
                try:
                    tmp = PUBLIC_IP_CACHE_PATH + '.tmp'
                    with open(tmp, 'w', encoding='utf-8') as ft:
                        json.dump({'ip': detected, 'ts': now}, ft, indent=2)
                        ft.write('\n')
                    os.replace(tmp, PUBLIC_IP_CACHE_PATH)
                    try:
                        os.chmod(PUBLIC_IP_CACHE_PATH, 0o640)
                    except OSError:
                        pass
                except OSError:
                    pass
            elif cached_ip:
                ip_to_try = cached_ip

        if not ip_to_try:
            return
        SSHSecurityWhitelistUtilities.upsert_whitelist_ip_if_absent(ip_to_try, LABEL_SERVER_AUTO)

    @staticmethod
    def maybe_whitelist_first_admin_login(client_ip: str) -> None:
        """
        Once per installation: whitelist the client IP of the first successful login
        by a user with admin ACL (adminStatus == 1).
        """
        if os.path.isfile(FIRST_ADMIN_LOGIN_FLAG_PATH):
            return
        v = SSHSecurityWhitelistUtilities.validate_ip(client_ip)
        if not v:
            return
        SSHSecurityWhitelistUtilities.upsert_whitelist_ip_if_absent(v, LABEL_FIRST_ADMIN_AUTO)
        try:
            tmp = FIRST_ADMIN_LOGIN_FLAG_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as tf:
                tf.write(v + '\n')
            os.replace(tmp, FIRST_ADMIN_LOGIN_FLAG_PATH)
            try:
                os.chmod(FIRST_ADMIN_LOGIN_FLAG_PATH, 0o640)
            except OSError:
                pass
            try:
                import grp
                import pwd
                uid = pwd.getpwnam('cyberpanel').pw_uid
                gid = grp.getgrnam('cyberpanel').gr_gid
                os.chown(FIRST_ADMIN_LOGIN_FLAG_PATH, uid, gid)
            except (OSError, KeyError, ImportError):
                pass
        except OSError:
            pass

    @staticmethod
    def on_successful_panel_login(request: Any, admin: Any) -> None:
        """
        Called after a successful CyberPanel login. Safe to call on every login; errors swallowed.
        """
        try:
            SSHSecurityWhitelistUtilities.ensure_cyberpanel_public_ip_whitelisted()
        except Exception:
            pass
        try:
            acl = getattr(admin, 'acl', None)
            if acl is None:
                return
            if int(getattr(acl, 'adminStatus', 0) or 0) != 1:
                return
            ip = SSHSecurityWhitelistUtilities.client_ip_from_request(request)
            SSHSecurityWhitelistUtilities.maybe_whitelist_first_admin_login(ip)
        except Exception:
            pass
