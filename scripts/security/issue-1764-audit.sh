#!/usr/bin/env bash
# Issue #1764 compromise audit (adapted from community checklist).
# Usage: bash /usr/local/CyberCP/scripts/security/issue-1764-audit.sh
# Output: stdout; redirect to /home/cyberpanel/to-do/issue-1764-audit-YYYY-MM-DD.txt
set -uo pipefail

echo "=== INITIAL COMPROMISE CHECK ==="
hostname
date

echo
echo "=== 1) known bad services: defunct / fastapi_ssh_server ==="
for s in defunct.service fastapi_ssh_server.service; do
  echo "--- $s ---"
  systemctl is-enabled "$s" 2>/dev/null || echo "not enabled / not found"
  systemctl is-active "$s" 2>/dev/null || echo "not active"
  systemctl status "$s" --no-pager -l 2>/dev/null | head -20 || true
done

echo
echo "=== 2) port 8888 and unusual listening ports ==="
ss -tulpnH 2>/dev/null | grep ':8888' || echo "OK: 8888 not on all interfaces (or closed)"
echo "--- bind detail ---"
ss -tlnp 2>/dev/null | grep ':8888' || echo "OK: nothing on 8888"

echo
echo "=== 3) known bad filenames ==="
find /usr/bin /usr/sbin /usr/local/bin /etc/systemd/system /usr/local/CyberCP \
  -maxdepth 3 \( -iname '*defunct*' -o -iname '*fastapi_ssh_server*' \) \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS %m %p\n' 2>/dev/null | sort

echo
echo "=== 4) known malicious SSH key fingerprint ==="
FOUND_BAD=0
while IFS= read -r f; do
  ssh-keygen -lf "$f" 2>/dev/null
done < <(find /root /home -path '*/.ssh/authorized_keys' -type f 2>/dev/null) \
  | grep -E 'w79EbEKrlqugvMc8n|Q2LzSLUbmtRh37BPAUbpgXCtI|9wK5rY\+itD1CH' && FOUND_BAD=1 || true
[[ "$FOUND_BAD" -eq 0 ]] && echo "OK: known malicious key fingerprint not found"

echo
echo "=== 5) root authorized_keys ==="
ls -la /root/.ssh/authorized_keys 2>/dev/null || true
lsattr /root/.ssh/authorized_keys 2>/dev/null || true
ssh-keygen -lf /root/.ssh/authorized_keys 2>/dev/null || true

echo
echo "=== 6) lscpd sudo scope ==="
sudo -l -U lscpd 2>/dev/null | tail -20 || true

echo
echo "=== 7) attacker IP 94.102.55.18 in auth logs ==="
grep -h '94.102.55.18' /var/log/secure /var/log/auth.log 2>/dev/null | tail -5 || echo "OK: no hits"

echo
echo "=== 8) recent root SSH (last 15) ==="
grep -hE 'Accepted (publickey|password) for root' /var/log/secure /var/log/auth.log 2>/dev/null | tail -15 || true

echo
echo "=== 9) suspicious processes ==="
ps -eo pid,ppid,user,stat,cmd --sort=start_time 2>/dev/null \
  | grep -Ei 'defunct|fastapi_ssh|uvicorn.*8888|/tmp/|card0|mm_percpu' \
  | grep -v grep || echo "OK: no known suspicious live processes"

echo
echo "=== 10) fastapi hardening marker ==="
ls -la /etc/cyberpanel/fastapi_ssh_server_hardening_v1.done 2>/dev/null || echo "MISSING hardening marker"
if [[ -x /usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh ]]; then
  /usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh || true
fi

echo
echo "=== 11) lscpd integrity log ==="
grep -i 'lscpd_integrity' /home/cyberpanel/error-logs.txt 2>/dev/null | tail -3 || echo "no lscpd_integrity lines in error-logs"

echo
echo "=== 12) cron persistence sample ==="
grep -RInE 'defunct|fastapi|8888|94\.102\.55' /etc/cron* /var/spool/cron 2>/dev/null | head -20 || echo "OK: no suspicious cron hits"

echo
echo "=== 13) firewall 8888 rules ==="
firewall-cmd --list-rich-rules 2>/dev/null | grep 8888 || echo "no 8888 rich rules"

echo
echo "=== 18) sshd effective config (root auth) ==="
sshd -T 2>/dev/null | grep -Ei 'permitrootlogin|passwordauthentication|pubkeyauthentication' || true

echo
echo "=== 19) cryptominer IoC ==="
ls -la /usr/bin/systemd-logind-helpers 2>/dev/null || echo "OK: no cryptominer binary"

echo
echo "=== 20) CyberPanel version ==="
cat /usr/local/CyberCP/version.txt 2>/dev/null || true

echo
echo "=== 21) audit complete ==="
