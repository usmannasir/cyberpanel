#!/usr/bin/env bash
# Register the local PostgreSQL server in pgAdmin with a saved password.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PGADMIN_EMAIL="$(cfg_get pgadmin_email)"
PGADMIN_PASS="$(cfg_get pgadmin_password)"
PG_SUPER="$(cfg_get pg_superuser)"
PG_SUPER_PASS="$(cfg_get pg_superuser_password)"
PG_PORT="$(cfg_get pg_port)"
PG_VER="$(cfg_get pg_version)"
SERVER_NAME="PostgreSQL ${PG_VER} (localhost)"
DISCOVERY_ID="POSTGRESQL_STACK/${PG_VER}"

register_server() {
    log_info "Registering pgAdmin server '${SERVER_NAME}'..."
    export PGADMIN_EMAIL="${PGADMIN_EMAIL}"
    export PGADMIN_PASSWORD="${PGADMIN_PASS}"
    export PG_SUPERUSER="${PG_SUPER}"
    export PG_SUPERUSER_PASSWORD="${PG_SUPER_PASS}"
    export PG_HOST="127.0.0.1"
    export PG_PORT="${PG_PORT}"
    export PG_MAINT_DB="postgres"
    export PG_SERVER_NAME="${SERVER_NAME}"
    export PG_DISCOVERY_ID="${DISCOVERY_ID}"

    local out
    if ! out="$(/usr/pgadmin4/venv/bin/python3 "${STACK_ROOT}/lib/register_pg_server.py" 2>&1 | tee -a "${LOG_FILE}")"; then
        log_error "Failed to register PostgreSQL server in pgAdmin."
        return 1
    fi
    local gid sid
    gid="$(echo "${out}" | sed -n 's/^SERVER_GID=//p' | tail -1)"
    sid="$(echo "${out}" | sed -n 's/^SERVER_SID=//p' | tail -1)"
    if [[ -n "${gid}" && -n "${sid}" ]]; then
        if /usr/pgadmin4/venv/bin/python3 "${STACK_ROOT}/lib/update_sso_server_ids.py" "${gid}" "${sid}" >>"${LOG_FILE}" 2>&1; then
            log_info "SSO secret updated with server_gid=${gid} server_sid=${sid}"
        else
            log_warn "Could not update SSO secret with server ids (run modules/55-sso.sh after SSO is configured)."
        fi
    fi
}

register_server

count="$(sqlite3 /var/lib/pgadmin/pgadmin4.db "SELECT COUNT(*) FROM server WHERE discovery_id='${DISCOVERY_ID}';" 2>/dev/null || echo 0)"
if [[ "${count}" -ge 1 ]]; then
    log_info "OK: pgAdmin has registered server '${SERVER_NAME}'."
else
    log_warn "Server row not found after registration; check ${LOG_FILE}"
fi

# postgres-reg.ini auto-discovery creates passwordless duplicate servers; do not use it.
if [[ -f /etc/postgres-reg.ini ]] && grep -q "POSTGRESQL_STACK" /etc/postgres-reg.ini 2>/dev/null; then
    log_info "Removing legacy postgres-reg.ini stack entry (causes duplicate servers)..."
    sed -i '/\[PostgreSQL\/POSTGRESQL_STACK/,/^$/d' /etc/postgres-reg.ini
fi

log_info "Server registration complete. After SSO login, pick '${SERVER_NAME}' in Query Tool or connect from the Browser tree."
