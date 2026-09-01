#!/usr/bin/env bash
# Run inside the guest after provision, or via up.ps1 smoke-* (SSH).
set -euo pipefail
fail=0

if systemctl is-active --quiet lscpd; then
  echo "OK lscpd active"
else
  echo "FAIL lscpd not active"
  fail=1
fi

code=$(curl -k -s -o /dev/null -w '%{http_code}' https://127.0.0.1:8090/ || true)
if [[ "$code" =~ ^(200|301|302|303|401|403)$ ]]; then
  echo "OK panel HTTPS :8090 http=$code"
else
  echo "FAIL panel HTTPS :8090 http=${code:-none}"
  fail=1
fi

python3 - << 'PY' || fail=1
import os, sys
sys.path.insert(0, '/usr/local/CyberCP')
os.chdir('/usr/local/CyberCP')
from re import search
path = '/usr/local/CyberCP/plogical/acl.py'
src = open(path, encoding='utf-8').read()
assert r'\d+\.\d+' in src, 'acl.py missing #1834 regex'
assert 'digits[-2:]' not in src, 'acl.py still uses last-two-digit fallback'
start = src.index('    def getPHPString')
end = src.index('\n    @staticmethod', start + 1)
body = src[start:end]
lines = [line[4:] if line.startswith('    ') else line for line in body.splitlines()]
ns = {}
exec('from re import search\n' + '\n'.join(lines) + '\n', ns)
fn = ns['getPHPString']
assert fn('PHP 8.6') == '86', fn('PHP 8.6')
assert fn('PHP 9.0') == '90', fn('PHP 9.0')
assert fn('PHP 8.10') == '810', fn('PHP 8.10')
assert fn('nope') == '85', fn('nope')
print('OK getPHPString 8.6/9.0/8.10/malformed')
PY

if [[ "$fail" -ne 0 ]]; then
  echo "SMOKE_FAIL"
  exit 1
fi
echo "SMOKE_OK"
