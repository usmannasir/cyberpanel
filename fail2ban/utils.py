import subprocess
import json
import re
import os
from datetime import datetime, timedelta
from .models import SecurityEvent, BannedIP

# Fail2ban jail names: alphanumeric, underscore, hyphen, dot (no shell metacharacters)
JAIL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')
JAIL_NAME_MAX_LEN = 128
SAFE_FAIL2BAN_CLIENT = '/usr/local/bin/cyberpanel-safe-fail2ban-client'
SAFE_FAIL2BAN_LOGS = '/usr/local/bin/cyberpanel-safe-fail2ban-logs'
SAFE_FAIL2BAN_LOGS_CLEAR = '/usr/local/bin/cyberpanel-safe-fail2ban-logs-clear'
FAIL2BAN_LOG_FILE = '/var/log/fail2ban.log'

# Short-lived cache so Banned IPs pagination does not re-query fail2ban every page.
_F2B_BANNED_CACHE = {'at': 0.0, 'rows': None}
_F2B_BANNED_CACHE_TTL = 20.0


class Fail2banManager:
    """Main class for managing fail2ban operations"""
    
    def __init__(self):
        self.fail2ban_cmd = 'fail2ban-client'
        self.firewall_cmd = 'firewall-cmd'
        self.config_file = '/etc/fail2ban/jail.local'
    
    def _privileged_fail2ban_argv(self, argv):
        """
        LSCPD workers run as cyberpanel (not root). Prefer the allowlisted
        sudo wrapper; fall back to sudo fail2ban-client when needed.
        """
        argv = list(argv)
        if not argv:
            return argv
        cmd0 = os.path.basename(str(argv[0]))
        if cmd0 not in ('fail2ban-client', os.path.basename(SAFE_FAIL2BAN_CLIENT)):
            return argv
        rest = argv[1:]
        if os.path.isfile(SAFE_FAIL2BAN_CLIENT):
            return ['sudo', '-n', SAFE_FAIL2BAN_CLIENT] + rest
        return ['sudo', '-n', '/usr/bin/fail2ban-client'] + rest

    def run_command(self, argv, timeout=30):
        """
        Run a subprocess with shell=False. argv must be a non-empty list of strings.
        """
        if not isinstance(argv, (list, tuple)) or not argv:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Invalid command',
                'returncode': -1
            }
        try:
            argv = self._privileged_fail2ban_argv(argv)
            result = subprocess.run(
                list(argv),
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'success': result.returncode == 0,
                'stdout': (result.stdout or '').strip(),
                'stderr': (result.stderr or '').strip(),
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }

    def is_safe_jail_name(self, jail):
        """Reject jail names that could confuse fail2ban-client or contain unsafe characters."""
        if not jail or not isinstance(jail, str):
            return False
        jail = jail.strip()
        if len(jail) > JAIL_NAME_MAX_LEN or len(jail) < 1:
            return False
        if not JAIL_NAME_PATTERN.match(jail):
            return False
        status = self.get_status()
        if status.get('running') and status.get('jails'):
            if jail not in status['jails']:
                return False
        return True
    
    def get_status(self):
        """Get fail2ban service status"""
        # Check if fail2ban is running
        result = self.run_command(['systemctl', 'is-active', 'fail2ban'])
        
        if not result['success']:
            return {
                'running': False,
                'error': 'Fail2ban service is not running'
            }
        
        # Get fail2ban status
        result = self.run_command([self.fail2ban_cmd, 'status'])
        
        if not result['success']:
            return {
                'running': False,
                'error': 'Failed to get fail2ban status'
            }
        
        # Parse the output
        lines = result['stdout'].split('\n')
        jails = []
        
        for line in lines:
            if 'Jail list:' in line:
                jail_list = line.split('Jail list:')[1].strip()
                jails = [j.strip() for j in jail_list.split(',') if j.strip()]
                break
        
        return {
            'running': True,
            'jails': jails,
            'total_jails': len(jails)
        }
    
    def get_jails(self):
        """Get detailed information about all jails (per-jail status)."""
        try:
            overview = self.get_status()
            if not overview.get('running'):
                return []

            jails = []
            for jail_name in overview.get('jails') or []:
                result = self.run_command([self.fail2ban_cmd, 'status', jail_name])
                current_jail = {
                    'name': jail_name,
                    'enabled': True,
                    'status': 'active',
                    'failed_attempts': 0,
                    'banned_ips': 0,
                    'currently_banned': 0,
                    'banned_ip_list': [],
                }
                if not result.get('success'):
                    current_jail['status'] = 'error'
                    jails.append(current_jail)
                    continue

                for line in (result.get('stdout') or '').split('\n'):
                    line = line.strip()
                    if 'Currently failed:' in line:
                        try:
                            current_jail['failed_attempts'] = int(line.split(':', 1)[1].strip())
                        except (TypeError, ValueError):
                            pass
                    elif 'Currently banned:' in line:
                        try:
                            count = int(line.split(':', 1)[1].strip())
                            current_jail['banned_ips'] = count
                            current_jail['currently_banned'] = count
                        except (TypeError, ValueError):
                            pass
                    elif 'Banned IP list:' in line:
                        banned_ips = line.split('Banned IP list:', 1)[1].strip()
                        if banned_ips:
                            current_jail['banned_ip_list'] = [
                                ip.strip() for ip in banned_ips.split() if ip.strip()
                            ]
                jails.append(current_jail)

            return jails
        except Exception:
            return []

    def list_fail2ban_banned_rows(self, use_cache=True):
        """
        Fast list of currently banned IPs across fail2ban jails.
        Cached briefly so pagination/search does not wait on fail2ban every request.
        """
        import time
        now = time.time()
        if (
            use_cache
            and _F2B_BANNED_CACHE['rows'] is not None
            and (now - float(_F2B_BANNED_CACHE['at'] or 0)) < _F2B_BANNED_CACHE_TTL
        ):
            return [dict(r) for r in _F2B_BANNED_CACHE['rows']]

        rows = []
        seen = set()
        try:
            result = self.run_command([self.fail2ban_cmd, 'status'], timeout=15)
            if not result.get('success'):
                return []
            jail_names = []
            for line in (result.get('stdout') or '').split('\n'):
                if 'Jail list:' in line:
                    raw = line.split('Jail list:', 1)[1].strip()
                    jail_names = [j.strip() for j in raw.replace(',', ' ').split() if j.strip()]
                    break
            for jail_name in jail_names:
                if not jail_name or not JAIL_NAME_PATTERN.match(jail_name):
                    continue
                if len(jail_name) > JAIL_NAME_MAX_LEN:
                    continue
                jr = self.run_command([self.fail2ban_cmd, 'status', jail_name], timeout=15)
                if not jr.get('success'):
                    continue
                for line in (jr.get('stdout') or '').split('\n'):
                    line = line.strip()
                    if 'Banned IP list:' not in line:
                        continue
                    banned_ips = line.split('Banned IP list:', 1)[1].strip()
                    for ip in banned_ips.split():
                        ip = ip.strip()
                        if not ip or ip in seen:
                            continue
                        seen.add(ip)
                        rows.append({
                            'ip': ip,
                            'jail': jail_name,
                            'source': 'fail2ban',
                            'banned_at': datetime.now().isoformat(),
                        })
        except Exception:
            rows = []

        _F2B_BANNED_CACHE['at'] = time.time()
        _F2B_BANNED_CACHE['rows'] = [dict(r) for r in rows]
        return rows

    def count_firewall_bans(self, q=None):
        """Fast count of active CyberPanel firewall bans (optional IP search)."""
        try:
            from firewall.models import BannedIP as FirewallBannedIP
            qs = FirewallBannedIP.objects.filter(active=True)
            q = (q or '').strip()
            if q:
                qs = qs.filter(ip_address__icontains=q)
            return int(qs.count())
        except Exception:
            return 0

    def query_firewall_banned_page(self, limit=50, offset=0, q=None):
        """Paginated firewall BannedIP rows (DB only; avoids full rich-rule scan)."""
        entries = []
        try:
            from firewall.models import BannedIP as FirewallBannedIP
            limit = max(1, min(200, int(limit or 50)))
            offset = max(0, int(offset or 0))
            qs = FirewallBannedIP.objects.filter(active=True).order_by('-banned_on')
            q = (q or '').strip()
            if q:
                qs = qs.filter(ip_address__icontains=q)
            for row in qs[offset:offset + limit]:
                ip = (row.ip_address or '').strip()
                if not ip:
                    continue
                banned_at = ''
                try:
                    if row.banned_on:
                        banned_at = row.banned_on.isoformat()
                except Exception:
                    banned_at = ''
                entries.append({
                    'ip': ip,
                    'jail': 'firewall',
                    'source': 'firewall',
                    'reason': getattr(row, 'reason', '') or '',
                    'banned_at': banned_at,
                })
        except Exception:
            pass
        return entries

    def get_banned_ips_page(self, include_firewall=True, limit=50, offset=0, q=None):
        """
        Efficient merged page: fail2ban jail bans first, then firewall DB bans.
        Supports search (q) and pagination without loading all 5k+ rows.
        """
        limit = max(1, min(200, int(limit or 50)))
        offset = max(0, int(offset or 0))
        q = (q or '').strip().lower()

        f2b_rows = self.list_fail2ban_banned_rows(use_cache=True) or []
        if q:
            f2b_rows = [
                r for r in f2b_rows
                if q in str((r.get('ip') if isinstance(r, dict) else r) or '').lower()
            ]
        f2b_count = len(f2b_rows)
        fw_count = self.count_firewall_bans(q=q) if include_firewall else 0
        total = f2b_count + fw_count

        data = []
        if offset < f2b_count:
            data.extend(f2b_rows[offset:offset + limit])
            remain = limit - len(data)
            if include_firewall and remain > 0:
                data.extend(self.query_firewall_banned_page(limit=remain, offset=0, q=q))
        elif include_firewall:
            fw_offset = offset - f2b_count
            data.extend(self.query_firewall_banned_page(limit=limit, offset=fw_offset, q=q))

        return {
            'data': data,
            'total': total,
            'offset': offset,
            'limit': limit,
            'fail2ban_count': f2b_count,
            'firewall_count': fw_count,
        }

    def get_banned_ips(self, include_firewall=False, limit=None, offset=0):
        """
        Get banned IPs from fail2ban jails.

        When include_firewall=True, also merge CyberPanel firewall BannedIP /
        firewalld rich-rule drops so historical Firewall bans appear in this plugin.
        Prefer get_banned_ips_page() for large lists.
        """
        try:
            banned_ips = self.list_fail2ban_banned_rows(use_cache=True) or []
            seen = set()
            for row in banned_ips:
                ip = row.get('ip') if isinstance(row, dict) else None
                if ip:
                    seen.add(ip)

            offset = max(0, int(offset or 0))
            limit_n = None
            if limit is not None:
                try:
                    limit_n = max(1, int(limit))
                except (TypeError, ValueError):
                    limit_n = 500

            if include_firewall:
                need_through = None
                if limit_n is not None:
                    need_through = offset + limit_n
                # Prefer DB pagination for large sets
                for row in self.query_firewall_banned_page(
                    limit=need_through or 500,
                    offset=0,
                    q=None,
                ):
                    ip = row.get('ip')
                    if not ip or ip in seen:
                        continue
                    seen.add(ip)
                    banned_ips.append(row)
                    if need_through is not None and len(banned_ips) >= need_through:
                        break

            if limit_n is not None:
                return banned_ips[offset:offset + limit_n]
            if offset:
                return banned_ips[offset:]
            return banned_ips
        except Exception:
            return []

    def get_firewall_banned_entries(self, max_count=None):
        """Active Firewall plugin bans + firewalld rich-rule drops."""
        entries = []
        seen = set()
        try:
            max_n = int(max_count) if max_count is not None else None
        except (TypeError, ValueError):
            max_n = None

        try:
            from firewall.models import BannedIP as FirewallBannedIP

            qs = FirewallBannedIP.objects.filter(active=True).order_by('-banned_on')
            if max_n is not None:
                qs = qs[:max_n]
            for row in qs.iterator(chunk_size=500):
                ip = (row.ip_address or '').strip()
                if not ip or ip in seen:
                    continue
                seen.add(ip)
                banned_at = ''
                try:
                    if row.banned_on:
                        banned_at = row.banned_on.isoformat()
                except Exception:
                    banned_at = ''
                entries.append({
                    'ip': ip,
                    'jail': 'firewall',
                    'source': 'firewall',
                    'reason': getattr(row, 'reason', '') or '',
                    'banned_at': banned_at,
                })
                if max_n is not None and len(entries) >= max_n:
                    return entries
        except Exception:
            pass

        try:
            for ip in self.get_blacklist() or []:
                if not ip or ip in seen:
                    continue
                seen.add(ip)
                entries.append({
                    'ip': ip,
                    'jail': 'firewalld',
                    'source': 'firewall',
                    'reason': 'firewalld rich rule',
                    'banned_at': '',
                })
                if max_n is not None and len(entries) >= max_n:
                    break
        except Exception:
            pass

        return entries

    def import_firewall_bans_to_jail(self, jail='sshd', limit=100, offset=0):
        """
        Import active firewall bans into a fail2ban jail (batched).

        Uses DB pagination so we never load all 5k+ candidates into memory.
        """
        jail = (jail or 'sshd').strip() or 'sshd'
        try:
            limit = max(1, min(200, int(limit)))
        except (TypeError, ValueError):
            limit = 100
        try:
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            offset = 0

        already = set()
        for row in self.list_fail2ban_banned_rows(use_cache=True) or []:
            ip = row.get('ip') if isinstance(row, dict) else None
            if ip:
                already.add(ip)

        fw_total = self.count_firewall_bans()
        # Walk firewall rows, skipping ones already in fail2ban, until we fill a batch
        # starting at logical candidate offset.
        batch = []
        skipped_candidates = 0
        scan_offset = 0
        scan_chunk = max(limit * 5, 200)
        guard = 0
        while len(batch) < limit and guard < 50:
            guard += 1
            page = self.query_firewall_banned_page(limit=scan_chunk, offset=scan_offset, q=None)
            if not page:
                break
            scan_offset += len(page)
            for row in page:
                ip = row.get('ip')
                if not ip or ip in already:
                    continue
                if skipped_candidates < offset:
                    skipped_candidates += 1
                    continue
                batch.append(ip)
                if len(batch) >= limit:
                    break
            if len(page) < scan_chunk:
                break

        banned = 0
        errors = []
        for ip in batch:
            result = self.ban_ip(ip, jail)
            ok = False
            if isinstance(result, dict):
                ok = bool(result.get('success'))
                if not ok:
                    errors.append('%s: %s' % (ip, result.get('error') or result.get('message') or 'failed'))
            else:
                ok = bool(result)
            if ok:
                banned += 1
                already.add(ip)

        # Approximate remaining candidates
        candidate_total = max(0, fw_total - len(already) + banned)
        next_offset = offset + len(batch)
        done = (len(batch) == 0) or (next_offset >= candidate_total) or (len(batch) < limit)

        return {
            'success': True,
            'jail': jail,
            'candidate_total': candidate_total,
            'batch_size': len(batch),
            'banned': banned,
            'offset': offset,
            'next_offset': next_offset,
            'done': done,
            'errors': errors[:20],
        }
    def get_whitelist(self):
        """Get whitelisted IPs from fail2ban jail.local ignoreip."""
        return self.get_ignoreip_list()

    def get_ignoreip_list(self):
        """Parse ignoreip from jail.local (supports many IPs / CIDR)."""
        try:
            if not os.path.exists(self.config_file):
                return []
            with open(self.config_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            match = re.search(r'(?m)^\s*ignoreip\s*=\s*(.+)$', content)
            if not match:
                return []
            raw = match.group(1).strip()
            parts = re.split(r'[\s,]+', raw)
            out = []
            seen = set()
            for part in parts:
                token = (part or '').strip()
                if not token or token in seen:
                    continue
                if self.is_valid_ip_or_cidr(token):
                    seen.add(token)
                    out.append(token)
            return out
        except Exception:
            return []

    def get_merged_whitelist(self):
        """
        Mirror Firewall SSH trusted IPs + fail2ban ignoreip + plugin settings.
        Returns list of {ip, label, sources: [...]}.
        """
        by_ip = {}

        def _add(ip, label='', source=''):
            token = (ip or '').strip()
            if not token:
                return
            row = by_ip.setdefault(token, {'ip': token, 'label': '', 'sources': []})
            if label and not row['label']:
                row['label'] = label
            if source and source not in row['sources']:
                row['sources'].append(source)

        for ip in self.get_ignoreip_list():
            _add(ip, source='fail2ban')

        try:
            from .models import Fail2banSettings
            for settings in Fail2banSettings.objects.all()[:20]:
                text = (settings.whitelist_ips or '').replace(',', '\n')
                for line in text.splitlines():
                    token = line.strip()
                    if token:
                        _add(token, source='plugin')
        except Exception:
            pass

        try:
            from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
            for entry in SSHSecurityWhitelistUtilities.load_entries():
                _add(entry.get('ip'), label=entry.get('label') or '', source='firewall')
        except Exception:
            pass

        rows = list(by_ip.values())
        rows.sort(key=lambda r: r['ip'])
        return rows

    def sync_firewall_whitelist_into_ignoreip(self, restart=False):
        """
        Ensure Firewall SSH trusted IPs are also present in fail2ban ignoreip.
        Display merge alone is not enough for fail2ban to honour them.
        """
        current = list(self.get_ignoreip_list() or [])
        seen = set(current)
        added = []
        try:
            from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
            for entry in SSHSecurityWhitelistUtilities.load_entries():
                token = (entry.get('ip') or '').strip()
                if not token or token in seen:
                    continue
                if not self.is_valid_ip_or_cidr(token):
                    continue
                current.append(token)
                seen.add(token)
                added.append(token)
        except Exception:
            pass
        if added:
            result = self.write_ignoreip_list(current, restart=restart)
            if not result.get('success'):
                return {
                    'success': False,
                    'added': [],
                    'error': result.get('error') or 'Failed to update ignoreip',
                }
        return {'success': True, 'added': added, 'total': len(current)}

    def write_ignoreip_list(self, ips, restart=True):
        """Replace ignoreip= line with the given list (preserves 127.0.0.1 / ::1)."""
        try:
            cleaned = []
            seen = set()
            for token in list(ips or []) + ['127.0.0.1', '::1']:
                token = (token or '').strip()
                if not token or token in seen:
                    continue
                if not self.is_valid_ip_or_cidr(token):
                    continue
                seen.add(token)
                cleaned.append(token)
            if not cleaned:
                cleaned = ['127.0.0.1', '::1']

            helper = '/usr/local/bin/cyberpanel-safe-fail2ban-ignoreip'
            payload = ' '.join(cleaned)
            wrote = False
            if os.path.isfile(helper):
                try:
                    result = subprocess.run(
                        ['sudo', '-n', helper],
                        input=payload,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        wrote = True
                    else:
                        err = (result.stderr or result.stdout or 'ignoreip helper failed').strip()
                        # Fall through to direct write (root/CLI)
                        if os.access(self.config_file, os.W_OK) or not os.path.exists(self.config_file):
                            pass
                        else:
                            return {'success': False, 'error': err}
                except Exception as helper_exc:
                    if not (os.access(self.config_file, os.W_OK) or not os.path.exists(self.config_file)):
                        return {'success': False, 'error': str(helper_exc)}

            if not wrote:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                else:
                    content = '[DEFAULT]\n'

                line = 'ignoreip = ' + ' '.join(cleaned)
                if re.search(r'(?m)^\s*ignoreip\s*=', content):
                    new_content = re.sub(r'(?m)^\s*ignoreip\s*=\s*.*$', line, content, count=1)
                else:
                    if '[DEFAULT]' in content:
                        new_content = content.replace('[DEFAULT]', '[DEFAULT]\n' + line, 1)
                    else:
                        new_content = '[DEFAULT]\n' + line + '\n' + content

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            if restart:
                self.restart_service()
            return {'success': True, 'data': cleaned, 'message': 'Whitelist updated (%d IPs)' % len(cleaned)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_to_whitelist(self, ip, label='', sync_firewall=True, restart=True):
        """Add IP/CIDR to fail2ban ignoreip and optionally firewall SSH trusted list."""
        try:
            token = (ip or '').strip()
            if not self.is_valid_ip_or_cidr(token):
                return {'success': False, 'error': 'Invalid IP address or CIDR'}

            current = self.get_ignoreip_list()
            if token not in current:
                current.append(token)
            result = self.write_ignoreip_list(current, restart=restart)
            if not result.get('success'):
                return result

            firewall_ok = None
            firewall_msg = ''
            if sync_firewall and '/' not in token:
                try:
                    from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
                    ok, msg = SSHSecurityWhitelistUtilities.add_entry(token, label=label or '')
                    firewall_ok = bool(ok)
                    firewall_msg = str(msg)
                except Exception as e:
                    firewall_ok = False
                    firewall_msg = str(e)

            try:
                self._append_plugin_whitelist_text(token)
            except Exception:
                pass

            return {
                'success': True,
                'message': 'IP %s added to whitelist' % token,
                'ip': token,
                'firewall_synced': firewall_ok,
                'firewall_detail': firewall_msg,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def remove_from_whitelist(self, ip, sync_firewall=True, restart=True, remove_fail2ban=True):
        """Remove IP/CIDR from fail2ban ignoreip and/or firewall SSH trusted list."""
        try:
            token = (ip or '').strip()
            if not token:
                return {'success': False, 'error': 'IP address is required'}

            if remove_fail2ban:
                current = [x for x in self.get_ignoreip_list() if x != token]
                result = self.write_ignoreip_list(current, restart=restart)
                if not result.get('success'):
                    return result

            if sync_firewall and '/' not in token:
                try:
                    from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
                    SSHSecurityWhitelistUtilities.remove_entry(token)
                except Exception:
                    pass

            if remove_fail2ban:
                try:
                    self._remove_plugin_whitelist_text(token)
                except Exception:
                    pass

            return {
                'success': True,
                'message': 'IP %s removed from whitelist' % token,
                'ip': token,
                'removed_fail2ban': bool(remove_fail2ban),
                'removed_firewall': bool(sync_firewall and '/' not in token),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_many_to_whitelist(self, ips, label='', sync_firewall=True):
        """Bulk-add many IPs (one restart)."""
        added = []
        skipped = []
        errors = []
        current = self.get_ignoreip_list()
        changed = False
        for raw in ips or []:
            token = (raw or '').strip()
            if not token:
                continue
            if not self.is_valid_ip_or_cidr(token):
                errors.append('%s: invalid' % token)
                continue
            if token in current:
                skipped.append(token)
                continue
            current.append(token)
            added.append(token)
            changed = True
            if sync_firewall and '/' not in token:
                try:
                    from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
                    SSHSecurityWhitelistUtilities.add_entry(token, label=label or '')
                except Exception:
                    pass
            try:
                self._append_plugin_whitelist_text(token)
            except Exception:
                pass
        if changed:
            result = self.write_ignoreip_list(current, restart=True)
            if not result.get('success'):
                return result
        return {
            'success': True,
            'added': added,
            'skipped': skipped,
            'errors': errors[:50],
            'total': len(self.get_ignoreip_list()),
        }

    def _append_plugin_whitelist_text(self, ip):
        from .models import Fail2banSettings
        for settings in Fail2banSettings.objects.all()[:20]:
            lines = [ln.strip() for ln in (settings.whitelist_ips or '').replace(',', '\n').splitlines() if ln.strip()]
            if ip not in lines:
                lines.append(ip)
                settings.whitelist_ips = '\n'.join(lines[:2000])
                settings.save(update_fields=['whitelist_ips', 'updated_at'])

    def _remove_plugin_whitelist_text(self, ip):
        from .models import Fail2banSettings
        for settings in Fail2banSettings.objects.all()[:20]:
            lines = [ln.strip() for ln in (settings.whitelist_ips or '').replace(',', '\n').splitlines() if ln.strip()]
            new_lines = [ln for ln in lines if ln != ip]
            if new_lines != lines:
                settings.whitelist_ips = '\n'.join(new_lines)
                settings.save(update_fields=['whitelist_ips', 'updated_at'])

    def get_blacklist(self):
        """Get blacklisted IPs from firewall rules"""
        try:
            result = self.run_command([self.firewall_cmd, '--list-rich-rules'])

            if not result['success']:
                return []

            blacklisted_ips = []
            for line in result['stdout'].split('\n'):
                if 'source address=' in line and 'drop' in line.lower():
                    ip_match = re.search(r'source address="([^"]+)"', line)
                    if ip_match:
                        blacklisted_ips.append(ip_match.group(1))

            return blacklisted_ips
        except Exception as e:
            return []

    def add_to_blacklist(self, ip):
        """Add IP to blacklist (permanent ban)"""
        try:
            if not self.is_valid_ip(ip):
                return {'success': False, 'error': 'Invalid IP address format'}
            
            rich_rule = 'rule family=ipv4 source address=%s drop' % ip
            result = self.run_command([
                self.firewall_cmd, '--permanent', '--add-rich-rule', rich_rule
            ])
            
            if not result['success']:
                return {'success': False, 'error': 'Failed to add firewall rule'}
            
            reload_result = self.run_command([self.firewall_cmd, '--reload'])
            
            if not reload_result['success']:
                return {'success': False, 'error': 'Failed to reload firewall'}
            
            return {'success': True, 'message': f'IP {ip} added to blacklist'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def remove_from_blacklist(self, ip):
        """Remove IP from blacklist"""
        try:
            rich_rule = 'rule family=ipv4 source address=%s drop' % ip
            result = self.run_command([
                self.firewall_cmd, '--permanent', '--remove-rich-rule', rich_rule
            ])
            
            if not result['success']:
                return {'success': False, 'error': 'Failed to remove firewall rule'}
            
            reload_result = self.run_command([self.firewall_cmd, '--reload'])
            
            if not reload_result['success']:
                return {'success': False, 'error': 'Failed to reload firewall'}
            
            return {'success': True, 'message': f'IP {ip} removed from blacklist'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def ban_ip(self, ip, jail='sshd'):
        """Ban an IP address in fail2ban (temporary per jail bantime)."""
        try:
            if not self.is_valid_ip(ip):
                return {'success': False, 'error': 'Invalid IP address format'}
            if self._is_protected_ip(ip):
                return {'success': False, 'error': 'Refusing to ban protected or private IP'}
            
            if not self.is_safe_jail_name(jail):
                return {'success': False, 'error': 'Invalid or unknown jail name'}
            
            result = self.run_command([self.fail2ban_cmd, 'set', jail, 'banip', ip])
            
            if not result['success']:
                return {'success': False, 'error': f'Failed to ban IP: {result["stderr"]}'}
            
            return {'success': True, 'message': f'IP {ip} banned from {jail}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _is_protected_ip(self, ip):
        """Block bans of private/loopback/link-local and this server's addresses."""
        import ipaddress
        try:
            obj = ipaddress.ip_address(ip)
        except ValueError:
            return True
        if obj.is_private or obj.is_loopback or obj.is_link_local or obj.is_reserved or obj.is_multicast:
            return True
        try:
            import socket
            host_ips = set()
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                host_ips.add(info[4][0])
            # Common primary IPv4 from hostname -I style
            try:
                out = subprocess.run(
                    ['hostname', '-I'], capture_output=True, text=True, timeout=5
                )
                for part in (out.stdout or '').split():
                    host_ips.add(part.strip())
            except Exception:
                pass
            if ip in host_ips:
                return True
        except Exception:
            pass
        return False

    def ban_ip_permanent(self, ip, jail='sshd', reason='Security alert'):
        """
        Ban via fail2ban (immediate jail ban) and permanently via firewalld rich rule.
        Dashboard Security Alerts use firewall alone; this also syncs fail2ban.
        """
        if not self.is_valid_ip(ip):
            return {'success': False, 'error': 'Invalid IP address format'}
        if self._is_protected_ip(ip):
            return {'success': False, 'error': 'Refusing to ban protected or private IP'}

        f2b = self.ban_ip(ip, jail=jail)
        fw_ok = False
        fw_msg = ''
        try:
            from plogical.firewallUtilities import FirewallUtilities
            fw_ok, fw_msg = FirewallUtilities.blockIP(ip, reason)
        except Exception as e:
            fw_msg = str(e)

        ok = bool(f2b.get('success')) or bool(fw_ok)
        return {
            'success': ok,
            'fail2ban': f2b,
            'firewall': {'success': bool(fw_ok), 'message': fw_msg},
            'message': (
                'IP %s banned (fail2ban=%s, firewall=%s)'
                % (ip, bool(f2b.get('success')), bool(fw_ok))
            ),
            'error': None if ok else (f2b.get('error') or fw_msg or 'Ban failed'),
        }
    
    def unban_ip(self, ip, jail='sshd'):
        """Unban an IP address from a fail2ban jail."""
        try:
            if not self.is_valid_ip(ip):
                return {'success': False, 'error': 'Invalid IP address format'}
            
            if not self.is_safe_jail_name(jail):
                return {'success': False, 'error': 'Invalid or unknown jail name'}
            
            result = self.run_command([self.fail2ban_cmd, 'set', jail, 'unbanip', ip])
            
            if not result['success']:
                return {'success': False, 'error': f'Failed to unban IP: {result["stderr"]}'}
            
            return {'success': True, 'message': f'IP {ip} unbanned from {jail}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def unban_firewall_ip(self, ip):
        """Remove a permanent CyberPanel / firewalld ban for an IP."""
        try:
            if not self.is_valid_ip(ip):
                return {'success': False, 'error': 'Invalid IP address format'}
            fw_ok = False
            fw_msg = ''
            try:
                from plogical.firewallUtilities import FirewallUtilities
                fw_ok, fw_msg = FirewallUtilities.unblockIP(ip)
            except Exception as e:
                fw_msg = str(e)
            # Also deactivate BannedIP row when present
            try:
                from firewall.models import BannedIP as FirewallBannedIP
                updated = FirewallBannedIP.objects.filter(
                    ip_address=ip, active=True
                ).update(active=False)
                if updated and not fw_ok:
                    fw_ok = True
                    fw_msg = fw_msg or ('Deactivated %d firewall ban row(s)' % updated)
            except Exception:
                pass
            # Bust short-lived banned cache
            try:
                _F2B_BANNED_CACHE['rows'] = None
                _F2B_BANNED_CACHE['at'] = 0.0
            except Exception:
                pass
            return {
                'success': bool(fw_ok),
                'message': fw_msg or ('IP %s removed from firewall bans' % ip),
                'error': None if fw_ok else (fw_msg or 'Firewall unban failed'),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def manage_unban(self, ip, jail='sshd', unban_fail2ban=True, unban_firewall=False):
        """Unban from fail2ban and/or firewall layers (used by Manage modal)."""
        out = {
            'success': False,
            'ip': ip,
            'fail2ban': None,
            'firewall': None,
        }
        if unban_fail2ban:
            j = (jail or 'sshd').strip() or 'sshd'
            if j == 'firewall':
                j = 'sshd'
            out['fail2ban'] = self.unban_ip(ip, j)
        if unban_firewall:
            out['firewall'] = self.unban_firewall_ip(ip)
        f2b_ok = (not unban_fail2ban) or bool((out['fail2ban'] or {}).get('success'))
        fw_ok = (not unban_firewall) or bool((out['firewall'] or {}).get('success'))
        # fail2ban may already be unbanned; treat "already" style errors softly when also clearing firewall
        if unban_fail2ban and not f2b_ok and unban_firewall and fw_ok:
            err = str((out['fail2ban'] or {}).get('error') or '').lower()
            if 'not found' in err or 'already' in err or 'is not banned' in err:
                f2b_ok = True
        out['success'] = bool(f2b_ok and fw_ok)
        if out['success']:
            out['message'] = 'Unban completed for %s' % ip
        else:
            out['error'] = (
                ((out['fail2ban'] or {}).get('error'))
                or ((out['firewall'] or {}).get('error'))
                or 'Unban failed'
            )
        return out
    
    def restart_service(self):
        """Restart fail2ban service"""
        try:
            result = self.run_command(['systemctl', 'restart', 'fail2ban'])
            
            if not result['success']:
                return {'success': False, 'error': f'Failed to restart service: {result["stderr"]}'}
            
            return {'success': True, 'message': 'Fail2ban service restarted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_logs(self, lines=100):
        """Get recent lines from /var/log/fail2ban.log (via allowlisted sudo helper)."""
        try:
            try:
                n = int(lines)
            except (TypeError, ValueError):
                n = 100
            n = max(1, min(n, 5000))

            logs = []
            # Panel workers run as cyberpanel and cannot read root-only fail2ban.log.
            if os.path.isfile(SAFE_FAIL2BAN_LOGS):
                result = self.run_command(['sudo', '-n', SAFE_FAIL2BAN_LOGS, str(n)])
                if result.get('success'):
                    for line in (result.get('stdout') or '').split('\n'):
                        if line.strip():
                            logs.append(line.strip())
                    # Empty file is a valid result (e.g. after Clear log); do not fall back to journal.
                    return logs

            # Direct read when process can open the file (e.g. root CLI).
            if os.path.isfile(FAIL2BAN_LOG_FILE) and os.access(FAIL2BAN_LOG_FILE, os.R_OK):
                result = self.run_command(['/usr/bin/tail', '-n', str(n), FAIL2BAN_LOG_FILE])
                if result.get('success'):
                    for line in (result.get('stdout') or '').split('\n'):
                        if line.strip():
                            logs.append(line.strip())
                    return logs

            # Last resort: journal (often empty for non-privileged users).
            result = self.run_command(
                ['journalctl', '-u', 'fail2ban', '-n', str(n), '--no-pager']
            )
            if result.get('success') and result.get('stdout'):
                for line in result['stdout'].split('\n'):
                    if line.strip():
                        logs.append(line.strip())
            return logs
        except Exception:
            return []

    def clear_logs(self):
        """Truncate /var/log/fail2ban.log via allowlisted sudo helper."""
        try:
            if os.path.isfile(SAFE_FAIL2BAN_LOGS_CLEAR):
                result = self.run_command(['sudo', '-n', SAFE_FAIL2BAN_LOGS_CLEAR])
                if result.get('success'):
                    return {
                        'success': True,
                        'message': 'fail2ban.log cleared',
                    }
                return {
                    'success': False,
                    'error': (result.get('stderr') or result.get('stdout') or 'Clear failed').strip()[:300],
                }
            if os.path.isfile(FAIL2BAN_LOG_FILE) and os.access(FAIL2BAN_LOG_FILE, os.W_OK):
                with open(FAIL2BAN_LOG_FILE, 'w', encoding='utf-8'):
                    pass
                return {'success': True, 'message': 'fail2ban.log cleared'}
            return {'success': False, 'error': 'Clear helper not available'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:300]}
    
    def is_valid_ip(self, ip):
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address((ip or '').strip())
            return True
        except ValueError:
            return False

    def is_valid_ip_or_cidr(self, value):
        """Validate IPv4/IPv6 address or CIDR network (for ignoreip)."""
        import ipaddress
        token = (value or '').strip()
        if not token:
            return False
        try:
            if '/' in token:
                ipaddress.ip_network(token, strict=False)
            else:
                ipaddress.ip_address(token)
            return True
        except ValueError:
            return False
    
    def start_service(self):
        """Start fail2ban service"""
        try:
            result = self.run_command(['systemctl', 'start', 'fail2ban'])
            
            if not result['success']:
                return {'success': False, 'error': f'Failed to start service: {result["stderr"]}'}
            
            return {'success': True, 'message': 'Fail2ban service started successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_service(self):
        """Stop fail2ban service"""
        try:
            result = self.run_command(['systemctl', 'stop', 'fail2ban'])
            
            if not result['success']:
                return {'success': False, 'error': f'Failed to stop service: {result["stderr"]}'}
            
            return {'success': True, 'message': 'Fail2ban service stopped successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
