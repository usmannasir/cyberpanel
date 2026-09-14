#!/usr/bin/env bash
# Post-install verification with retries.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PG_SVC="$(pg_service_name)"
PG_BIN="$(pg_bin_dir)"
PGADMIN_DOMAIN="$(cfg_get pgadmin_domain)"
BIND_HOST="$(cfg_get pgadmin_bind_host)"
BIND_PORT="$(cfg_get pgadmin_bind_port)"
CRON_DB="$(cfg_get pg_cron_database)"
FAIL=0

check_service() {
    local svc="$1"
    if systemctl is-active --quiet "${svc}"; then
        log_info "OK: service ${svc} is active"
        return 0
    fi
    log_error "FAIL: service ${svc} is not active"
    FAIL=1
    return 1
}

check_psql() {
    if sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -c 'SELECT 1;' >/dev/null 2>&1; then
        log_info "OK: psql connects as postgres"
        return 0
    fi
    log_error "FAIL: psql connection failed"
    FAIL=1
    return 1
}

check_pg_cron() {
    if sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -d "${CRON_DB}" -tAc \
        "SELECT 1 FROM pg_extension WHERE extname='pg_cron';" 2>/dev/null | grep -q 1; then
        log_info "OK: pg_cron extension present"
        return 0
    fi
    log_error "FAIL: pg_cron extension missing"
    FAIL=1
    return 1
}

check_system_stats() {
    if sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -d postgres -tAc \
        "SELECT 1 FROM pg_extension WHERE extname='system_stats';" 2>/dev/null | grep -q 1; then
        log_info "OK: system_stats extension present (pgAdmin Dashboard System tab)"
        return 0
    fi
    log_warn "system_stats extension missing; pgAdmin System tab limited (run modules/10-postgresql.sh)"
    return 0
}

check_pgadmin_local() {
    local code
    code="$(curl -sk -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/login" 2>/dev/null || echo 000)"
    if echo "${code}" | grep -qE '200|302|301'; then
        log_info "OK: pgAdmin local backend HTTP ${code}"
        return 0
    fi
    log_error "FAIL: pgAdmin local backend returned HTTP ${code}"
    FAIL=1
    return 1
}

check_pgadmin_server() {
    local pg_ver count
    pg_ver="$(cfg_get pg_version)"
    count="$(sqlite3 /var/lib/pgadmin/pgadmin4.db "SELECT COUNT(*) FROM server WHERE discovery_id='POSTGRESQL_STACK/${pg_ver}';" 2>/dev/null || echo 0)"
    if [[ "${count}" -ge 1 ]]; then
        log_info "OK: pgAdmin has registered PostgreSQL server (POSTGRESQL_STACK/${pg_ver})"
        return 0
    fi
    log_error "FAIL: pgAdmin server registration missing (run modules/45-pgadmin-server.sh)"
    FAIL=1
    return 1
}

check_sso() {
    local token good bad
    token="$(cfg_get pgadmin_sso_token 2>/dev/null || true)"
    if [[ -z "${token}" || "${token}" == "missing key" ]]; then
        log_warn "SSO token not configured; skipping SSO check."
        return 0
    fi
    good="$(curl -s -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/sso/?key=${token}" 2>/dev/null || echo 000)"
    bad="$(curl -s -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/sso/?key=invalid" 2>/dev/null || echo 000)"
    if [[ "${good}" == "302" && "${bad}" == "403" ]]; then
        log_info "OK: SSO auto-login (302 valid token, 403 invalid token)"
    else
        log_error "FAIL: SSO check (valid=${good} expected 302, invalid=${bad} expected 403)"
        FAIL=1
        return 1
    fi

    local cj ref csrf hdr gid sid count sess
    cj="$(mktemp)"
    ref="https://${PGADMIN_DOMAIN}/browser/"
    sess="$(curl -sk -H "Host: ${PGADMIN_DOMAIN}" \
        --resolve "${PGADMIN_DOMAIN}:443:127.0.0.1" \
        -D - "https://${PGADMIN_DOMAIN}/sso/?key=${token}" -o /dev/null 2>/dev/null | \
        sed -n 's/.*pga4_session=\([^;]*\).*/\1/p' | head -1)"
    if [[ -z "${sess}" ]]; then
        log_warn "SSO session cookie not returned; skipping post-login API checks."
        rm -f "${cj}"
        return 0
    fi
    curl -sk -H "Host: ${PGADMIN_DOMAIN}" -H "Cookie: pga4_session=${sess}" \
        --resolve "${PGADMIN_DOMAIN}:443:127.0.0.1" \
        "https://${PGADMIN_DOMAIN}/browser/js/utils.js" -o /tmp/pgstack-utils.js 2>/dev/null || true
    csrf="$(sed -n "s/.*pgAdmin\['csrf_token'\] = '\([^']*\)'.*/\1/p" /tmp/pgstack-utils.js | head -1)"
    hdr="$(sed -n "s/.*pgAdmin\['csrf_token_header'\] = '\([^']*\)'.*/\1/p" /tmp/pgstack-utils.js | head -1)"
    if [[ -z "${csrf}" || -z "${hdr}" ]]; then
        log_warn "SSO session CSRF not available; skipping post-login API checks."
        rm -f "${cj}"
        return 0
    fi
    gid="$(python3 -c "import json;print(json.load(open('/var/lib/pgadmin/.pgstack-sso.json')).get('server_gid',''))" 2>/dev/null || true)"
    sid="$(python3 -c "import json;print(json.load(open('/var/lib/pgadmin/.pgstack-sso.json')).get('server_sid',''))" 2>/dev/null || true)"
    if [[ -n "${gid}" && -n "${sid}" ]]; then
        local conn_code
        conn_code="$(curl -sk -H "Host: ${PGADMIN_DOMAIN}" -H "Cookie: pga4_session=${sess}" \
            -X POST -H "${hdr}: ${csrf}" -H "Referer: ${ref}" -H "Content-Type: application/json" -d '{}' \
            --resolve "${PGADMIN_DOMAIN}:443:127.0.0.1" \
            "https://${PGADMIN_DOMAIN}/browser/server/connect/${gid}/${sid}" \
            -o /tmp/pgstack-conn.json -w '%{http_code}' 2>/dev/null || echo 000)"
        if [[ "${conn_code}" == "200" ]]; then
            log_info "OK: SSO post-login server connect (gid=${gid} sid=${sid})"
        else
            log_warn "SSO post-login connect returned HTTP ${conn_code} (gid=${gid} sid=${sid})"
        fi
    fi
    count="$(curl -sk -H "Host: ${PGADMIN_DOMAIN}" -H "Cookie: pga4_session=${sess}" \
        -H "${hdr}: ${csrf}" -H "Referer: ${ref}" \
        --resolve "${PGADMIN_DOMAIN}:443:127.0.0.1" \
        "https://${PGADMIN_DOMAIN}/sqleditor/new_connection_dialog" 2>/dev/null | \
        python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d.get('data',{}).get('result',{}).get('server_list',{}).get('Servers',[])))" 2>/dev/null || echo 0)"
    rm -f "${cj}"
    if [[ "${count}" -ge 1 ]]; then
        log_info "OK: Query Tool server list API returns ${count} server(s) after SSO"
        return 0
    fi
    log_warn "Query Tool server list API returned 0 servers after SSO"
    return 0
}

check_public_url() {
    local code
    code="$(curl -sk -o /dev/null -w '%{http_code}' "https://${PGADMIN_DOMAIN}/login" 2>/dev/null || echo 000)"
    if echo "${code}" | grep -qE '200|302|301'; then
        log_info "OK: public URL https://${PGADMIN_DOMAIN}/ returned HTTP ${code}"
        return 0
    fi
    code="$(curl -sk -o /dev/null -w '%{http_code}' --resolve "${PGADMIN_DOMAIN}:443:127.0.0.1" "https://${PGADMIN_DOMAIN}/login" 2>/dev/null || echo 000)"
    if echo "${code}" | grep -qE '200|302|301'; then
        log_info "OK: reverse proxy via LiteSpeed returned HTTP ${code} (DNS may need A record for ${PGADMIN_DOMAIN})"
        return 0
    fi
    log_warn "Public URL returned HTTP ${code}; add DNS A record for ${PGADMIN_DOMAIN} and re-run: cyberpanel issueSSL --domainName ${PGADMIN_DOMAIN}"
    return 0
}

retry 3 5 check_service "${PG_SVC}"
retry 3 5 check_service pgadmin4
retry 5 5 check_psql
retry 3 5 check_pg_cron
check_system_stats
retry 8 5 check_pgadmin_local
retry 3 5 check_pgadmin_server
retry 3 5 check_sso
check_public_url

if [[ "${FAIL}" -ne 0 ]]; then
    log_error "Verification failed. See ${LOG_FILE}"
    exit 1
fi

log_info "All critical verification checks passed."
