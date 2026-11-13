#!/usr/bin/env bash
# Remove PostgreSQL stack (services, tile, optional data purge).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

PURGE_DATA=0
REMOVE_TILE=1

usage() {
    echo "Usage: $0 [--purge-data] [--keep-tile]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge-data) PURGE_DATA=1; shift ;;
        --keep-tile) REMOVE_TILE=0; shift ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

require_root

if [[ -f "${CONFIG_PHP}" ]]; then
    load_config
    PG_VER="$(cfg_get pg_version)"
    PGADMIN_DOMAIN="$(cfg_get pgadmin_domain)"
else
    PG_VER="17"
    PGADMIN_DOMAIN="pgadmin.newstargeted.com"
fi

log_info "Stopping pgAdmin service..."
systemctl stop pgadmin4 2>/dev/null || true
systemctl disable pgadmin4 2>/dev/null || true
rm -f /etc/systemd/system/pgadmin4.service
systemctl daemon-reload

log_info "Removing SSO secret file..."
rm -f /var/lib/pgadmin/.pgstack-sso.json

if [[ "${REMOVE_TILE}" -eq 1 ]]; then
    for html in \
        "/usr/local/CyberCP/websiteFunctions/templates/websiteFunctions/website.html" \
        "/usr/local/CyberCP/websiteFunctions/templates/websiteFunctions/applicationInstaller.html"; do
        if [[ -f "${html}" ]] && grep -q "POSTGRESQL_STACK_TILE" "${html}"; then
            log_info "Removing PostgreSQL card from $(basename "${html}")..."
            TARGET="${html}" python3 <<'PY'
import os, re
from pathlib import Path
path = Path(os.environ["TARGET"])
text = path.read_text()
text = re.sub(r"\n\s*<!-- POSTGRESQL_STACK_TILE -->.*?</a>\n", "\n", text, flags=re.DOTALL)
path.write_text(text)
PY
        fi
    done
fi

log_info "PostgreSQL server left installed by default (shared system service)."
log_info "To remove packages: dnf remove postgresql${PG_VER}-server pgadmin4-web pg_cron_${PG_VER}"

if [[ "${PURGE_DATA}" -eq 1 ]]; then
    read -r -p "Purge PostgreSQL data directory? This destroys all databases [y/N]: " ans
    if [[ "${ans}" == "y" || "${ans}" == "Y" ]]; then
        systemctl stop "postgresql-${PG_VER}" 2>/dev/null || true
        rm -rf "/var/lib/pgsql/${PG_VER}"
        log_warn "PostgreSQL data purged."
    fi
fi

log_info "Uninstall steps completed. Remove child domain ${PGADMIN_DOMAIN} manually in CyberPanel if desired."
