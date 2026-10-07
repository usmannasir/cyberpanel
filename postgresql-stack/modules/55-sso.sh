#!/usr/bin/env bash
# Configure one-click SSO launcher for pgAdmin.
# - Generates a per-install SSO token (stored in config.php).
# - Writes an apache-readable secret file consumed by lib/pgadmin_wsgi.py.
# - Disables the pgAdmin master-password prompt for frictionless entry.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

SECRET_FILE="/var/lib/pgadmin/.pgstack-sso.json"
LOCAL_CFG="/usr/pgadmin4/web/config_local.py"

ensure_token() {
    local token
    token="$(cfg_get pgadmin_sso_token 2>/dev/null || true)"
    if [[ -z "${token}" || "${token}" == "missing key" ]]; then
        token="$(gen_secret 48)"
        update_config_value "pgadmin_sso_token" "${token}"
        log_info "Generated new pgAdmin SSO token."
    else
        log_info "Existing pgAdmin SSO token preserved."
    fi
}

write_secret_file() {
    local token email pass bhost bport
    token="$(cfg_get pgadmin_sso_token)"
    email="$(cfg_get pgadmin_email)"
    pass="$(cfg_get pgadmin_password)"
    bhost="$(cfg_get pgadmin_bind_host)"
    bport="$(cfg_get pgadmin_bind_port)"

    mkdir -p /var/lib/pgadmin
    TOKEN="${token}" EMAIL="${email}" PASS="${pass}" BHOST="${bhost}" BPORT="${bport}" \
    SECRET_FILE="${SECRET_FILE}" python3 <<'PY'
import json, os
path = os.environ["SECRET_FILE"]
existing = {}
try:
    with open(path, "r", encoding="utf-8") as fh:
        existing = json.load(fh)
except Exception:
    pass
data = {
    "token": os.environ["TOKEN"],
    "email": os.environ["EMAIL"],
    "password": os.environ["PASS"],
    "backend_host": os.environ.get("BHOST") or "127.0.0.1",
    "backend_port": int(os.environ.get("BPORT") or 5050),
}
for key in ("server_gid", "server_sid"):
    if key in existing:
        data[key] = existing[key]
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh)
PY
    chown apache:apache "${SECRET_FILE}" 2>/dev/null || true
    chmod 600 "${SECRET_FILE}"
    log_info "Wrote SSO secret file (chmod 600, apache-owned): ${SECRET_FILE}"
}

set_pgadmin_flag() {
    local key="$1" value="$2"
    if grep -q "^${key}" "${LOCAL_CFG}"; then
        sed -i "s/^${key}.*/${key} = ${value}/" "${LOCAL_CFG}"
    else
        echo "${key} = ${value}" >> "${LOCAL_CFG}"
    fi
}

tune_pgadmin_for_sso() {
    if [[ ! -f "${LOCAL_CFG}" ]]; then
        log_warn "pgAdmin config_local.py not found; skipping SSO tuning."
        return 0
    fi
    # Frictionless: no master-password prompt on first/each login.
    set_pgadmin_flag "MASTER_PASSWORD_REQUIRED" "False"
    # Required for SSO: the launcher logs in server-side, so the session must not
    # be bound to the IP/User-Agent (Paranoid/ENHANCED_COOKIE_PROTECTION).
    set_pgadmin_flag "ENHANCED_COOKIE_PROTECTION" "False"
    log_info "Tuned pgAdmin for SSO (MASTER_PASSWORD_REQUIRED=False, ENHANCED_COOKIE_PROTECTION=False)."
}

restart_pgadmin() {
    log_info "Restarting pgadmin4 to load SSO launcher..."
    systemctl restart pgadmin4
    retry 10 5 systemctl is-active --quiet pgadmin4
}

ensure_token
write_secret_file
tune_pgadmin_for_sso
restart_pgadmin

BIND_HOST="$(cfg_get pgadmin_bind_host)"
BIND_PORT="$(cfg_get pgadmin_bind_port)"
TOKEN="$(cfg_get pgadmin_sso_token)"
sleep 2
good="$(curl -s -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/sso/?key=${TOKEN}" 2>/dev/null || echo 000)"
bad="$(curl -s -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/sso/?key=invalid" 2>/dev/null || echo 000)"
if [[ "${good}" == "302" ]]; then
    log_info "OK: SSO launcher auto-login works (HTTP 302 with valid token)."
else
    log_warn "SSO launcher returned HTTP ${good} for valid token (expected 302); check journalctl -u pgadmin4."
fi
if [[ "${bad}" == "403" ]]; then
    log_info "OK: SSO launcher rejects invalid token (HTTP 403)."
else
    log_warn "SSO launcher returned HTTP ${bad} for invalid token (expected 403)."
fi

log_info "SSO configured. Tile opens: https://$(cfg_get pgadmin_domain)/sso/?key=<token>"
