#!/usr/bin/env bash
# Core panel smoke (full or minimal).
set -euo pipefail
fail=0

if systemctl is-active --quiet lscpd; then echo "OK lscpd active"; else echo "FAIL lscpd"; fail=1; fi
code=$(curl -k -s -o /dev/null -w '%{http_code}' https://127.0.0.1:8090/ || true)
if [[ "$code" =~ ^(200|301|302|303|401|403)$ ]]; then echo "OK panel :8090 http=$code"; else echo "FAIL panel http=${code:-none}"; fail=1; fi
systemctl is-active --quiet mariadb || systemctl is-active --quiet mysql || { echo "FAIL mariadb"; fail=1; }
systemctl is-active --quiet docker || { echo "FAIL docker"; fail=1; }
systemctl is-active --quiet firewalld || { echo "FAIL firewalld"; fail=1; }

python3 - << 'PY' || fail=1
import os, sys
sys.path.insert(0, '/usr/local/CyberCP')
os.chdir('/usr/local/CyberCP')
from re import search
src = open('/usr/local/CyberCP/plogical/acl.py', encoding='utf-8').read()
start = src.index('    def getPHPString')
end = src.index('\n    @staticmethod', start + 1)
body = src[start:end]
lines = [line[4:] if line.startswith('    ') else line for line in body.splitlines()]
ns = {}
exec('from re import search\n' + '\n'.join(lines) + '\n', ns)
fn = ns['getPHPString']
assert fn('PHP 8.10') == '810', fn('PHP 8.10')
print('OK getPHPString 8.10')
PY

if grep -q avx2 /proc/cpuinfo 2>/dev/null; then echo "AVX2_OK"; else echo "AVX2_WARN"; fi

[[ "$fail" -eq 0 ]] && echo "SMOKE_OK" || { echo "SMOKE_FAIL"; exit 1; }
