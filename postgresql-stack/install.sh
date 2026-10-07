#!/usr/bin/env bash
# PostgreSQL + pgAdmin stack installer for CyberPanel hosts.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

PG_VERSION="17"
PGADMIN_DOMAIN="pgadmin.newstargeted.com"
MASTER_DOMAIN="newstargeted.com"
WITH_PGAGENT=0
NO_TILE=0
SKIP_VERIFY=0

usage() {
    cat <<EOF
Usage: $0 [options]

Options:
  --domain DOMAIN       pgAdmin subdomain (default: pgadmin.newstargeted.com)
  --master-domain DOM   CyberPanel master domain (default: newstargeted.com)
  --pg-version VER      PostgreSQL major version (default: 17)
  --with-pgagent        Install deprecated pgAgent (not recommended)
  --no-tile             Skip CyberPanel Quick App tile injection
  --skip-verify         Skip post-install verification
  -h, --help            Show this help

Re-run safely: existing config.php secrets are preserved.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain) PGADMIN_DOMAIN="$2"; shift 2 ;;
        --master-domain) MASTER_DOMAIN="$2"; shift 2 ;;
        --pg-version) PG_VERSION="$2"; shift 2 ;;
        --with-pgagent) WITH_PGAGENT=1; shift ;;
        --no-tile) NO_TILE=1; shift ;;
        --skip-verify) SKIP_VERIFY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

require_root
require_almalinux
ensure_dirs
init_config_if_missing
load_config

update_config_value "pg_version" "${PG_VERSION}"
update_config_value "pgadmin_domain" "${PGADMIN_DOMAIN}"
update_config_value "master_domain" "${MASTER_DOMAIN}"
update_config_value "with_pgagent" "$([[ "${WITH_PGAGENT}" -eq 1 ]] && echo true || echo false)"
update_config_value "install_tile" "$([[ "${NO_TILE}" -eq 1 ]] && echo false || echo true)"

log_info "Starting PostgreSQL stack install (PG ${PG_VERSION}, domain ${PGADMIN_DOMAIN})"

MODULES=(
    "10-postgresql.sh"
    "20-pg_cron.sh"
)
if [[ "${WITH_PGAGENT}" -eq 1 ]]; then
    MODULES+=("30-pgagent.sh")
fi
MODULES+=(
    "40-pgadmin.sh"
    "45-pgadmin-server.sh"
    "47-pgadmin-patches.sh"
    "50-subdomain-proxy.sh"
    "55-sso.sh"
)
if [[ "${NO_TILE}" -eq 0 ]]; then
    MODULES+=("60-tile.sh")
fi
if [[ "${SKIP_VERIFY}" -eq 0 ]]; then
    MODULES+=("90-verify.sh")
fi

for mod in "${MODULES[@]}"; do
    run_module "${mod}"
done

log_info "Install complete. pgAdmin URL: https://${PGADMIN_DOMAIN}/"
log_info "Credentials are stored in ${CONFIG_PHP} (chmod 600). Do not expose this file."
