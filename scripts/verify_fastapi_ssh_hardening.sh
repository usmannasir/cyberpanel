#!/usr/bin/env bash
# Verify fastapi_ssh_server (Web Terminal) is hardened per v2.5.5-dev security migration.
# CyberPanel standard panel port is 8090; custom installs may bind lscpd to another port (e.g. 2087).
# Exit 0 when safe to keep enabled; non-zero when remediation is required.
set -euo pipefail

MARKER="/etc/cyberpanel/fastapi_ssh_server_hardening_v1.done"
CONF="/etc/cyberpanel/fastapi_ssh_server.conf"
UNIT="/etc/systemd/system/fastapi_ssh_server.service"
FAIL=0

log() { echo "[verify_fastapi_ssh] $*"; }

if [[ ! -f "$MARKER" ]]; then
  log "FAIL: missing hardening marker $MARKER"
  FAIL=1
fi

if [[ ! -f "$CONF" ]]; then
  log "FAIL: missing JWT config $CONF"
  FAIL=1
else
  perms="$(stat -c '%a' "$CONF" 2>/dev/null || echo '')"
  if [[ "$perms" != "600" ]]; then
    log "WARN: $CONF permissions are $perms (expected 600)"
  fi
fi

if [[ -f "$UNIT" ]]; then
  if grep -F '0.0.0.0' "$UNIT" | grep -q -- '--host'; then
    log "FAIL: $UNIT may bind 0.0.0.0 (public exposure)"
    FAIL=1
  fi
  if ! grep -F '127.0.0.1' "$UNIT" >/dev/null; then
    log "FAIL: $UNIT does not bind 127.0.0.1"
    FAIL=1
  fi
else
  log "FAIL: missing systemd unit $UNIT"
  FAIL=1
fi

if command -v ss >/dev/null 2>&1; then
  if ss -tln 2>/dev/null | grep -q '127.0.0.1:8888'; then
    log "OK: port 8888 listens on 127.0.0.1 only"
  elif ss -tln 2>/dev/null | grep -q ':8888'; then
    log "FAIL: port 8888 is not localhost-only"
    FAIL=1
  else
    log "WARN: fastapi_ssh_server not listening on 8888 (service may be stopped)"
  fi
fi

if [[ "$FAIL" -eq 0 ]]; then
  log "PASS: keep fastapi_ssh_server enabled (localhost + conf JWT; Web Terminal available)"
  exit 0
fi

log "REMEDIATION: run plogical.fastapi_ssh_config.apply_security_migration() via CyberPanel upgrade, or disable: systemctl disable --now fastapi_ssh_server"
exit 1
