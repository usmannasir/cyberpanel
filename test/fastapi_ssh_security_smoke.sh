#!/usr/bin/env bash
# Regression checks for Web Terminal (fastapi_ssh_server) hardening.
# Usage: bash test/fastapi_ssh_security_smoke.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() {
	echo "FAIL: $1" >&2
	exit 1
}

if grep -Fq "DAsjK2gl50PE09d1N3uZPTQ6JdwwfiuhlyWKMVbUEpc" fastapi_ssh_server.py 2>/dev/null; then
	fail "legacy shared JWT string must not appear in fastapi_ssh_server.py"
fi

if grep -Eq "^\s*JWT_SECRET\s*=" fastapi_ssh_server.py 2>/dev/null; then
	fail "JWT_SECRET must not be assigned in fastapi_ssh_server.py (use /etc/cyberpanel/fastapi_ssh_server.conf)"
fi

if ! grep -q "EnvironmentFile=-/etc/cyberpanel/fastapi_ssh_server.conf" fastapi_ssh_server.service; then
	fail "fastapi_ssh_server.service must load EnvironmentFile=-/etc/cyberpanel/fastapi_ssh_server.conf"
fi

if grep -q 'FirewallUtilities.addRule("tcp", "8888")' install/install.py; then
	fail "install/install.py must not add public firewalld rule tcp 8888 by default"
fi

if awk '/ports = \[/,/40110-40210\/tcp/' install/install.py | grep -q "8888"; then
	fail "AlmaLinux 9 firewall ports block in install/install.py must not include 8888"
fi

echo "OK: fastapi_ssh_server security smoke tests passed."
