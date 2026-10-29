#!/usr/bin/env bash
# Optional pgAgent install (deprecated upstream; use pg_cron instead).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PG_VER="$(cfg_get pg_version)"
PG_SVC="$(pg_service_name)"
PG_BIN="$(pg_bin_dir)"
CRON_DB="$(cfg_get pg_cron_database)"

log_warn "pgAgent is deprecated by the pgAdmin team. Prefer pg_cron (already installed)."
log_warn "See: https://www.pgadmin.org/download/pgagent-source-code/"

retry 3 10 dnf install -y "pgagent_${PG_VER}" 2>/dev/null || {
    log_warn "pgagent_${PG_VER} package not found in PGDG; trying pgagent..."
    retry 3 10 dnf install -y pgagent || {
        log_error "pgAgent package unavailable. Skipping."
        exit 0
    }
}

if [[ -f /usr/share/pgagent/pgagent.sql ]]; then
    sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -d "${CRON_DB}" -f /usr/share/pgagent/pgagent.sql 2>/dev/null || \
        log_warn "pgAgent SQL may already be applied."
fi

if systemctl list-unit-files | grep -q pgagent; then
    systemctl enable pgagent 2>/dev/null || true
    systemctl start pgagent 2>/dev/null || log_warn "pgagent service failed to start; configure manually."
fi

log_info "pgAgent install step finished (optional component)."
