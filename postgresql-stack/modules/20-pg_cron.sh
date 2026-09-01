#!/usr/bin/env bash
# Install and configure pg_cron extension.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PG_VER="$(cfg_get pg_version)"
PG_SVC="$(pg_service_name)"
PG_BIN="$(pg_bin_dir)"
PG_DATA="$(pg_data_dir)"
CRON_DB="$(cfg_get pg_cron_database)"
CONF="$(pg_conf_file)"

install_pg_cron_package() {
    log_info "Installing pg_cron for PostgreSQL ${PG_VER}..."
    retry 3 10 dnf install -y "pg_cron_${PG_VER}"
}

configure_shared_preload() {
    log_info "Configuring shared_preload_libraries for pg_cron..."
    if grep -qE "^shared_preload_libraries\s*=" "${CONF}"; then
        if grep -q "pg_cron" "${CONF}"; then
            log_info "pg_cron already in shared_preload_libraries."
        else
            sed -i -E "s/^shared_preload_libraries\s*=\s*'([^']*)'/shared_preload_libraries = '\1,pg_cron'/" "${CONF}"
        fi
    elif grep -qE "^#shared_preload_libraries\s*=" "${CONF}"; then
        sed -i -E "s/^#shared_preload_libraries\s*=.*/shared_preload_libraries = 'pg_cron'/" "${CONF}"
    else
        echo "shared_preload_libraries = 'pg_cron'" >> "${CONF}"
    fi

    if grep -q "^cron.database_name" "${CONF}"; then
        sed -i "s/^#*cron.database_name.*/cron.database_name = '${CRON_DB}'/" "${CONF}"
    else
        echo "cron.database_name = '${CRON_DB}'" >> "${CONF}"
    fi
}

create_extension() {
    log_info "Creating pg_cron extension in database ${CRON_DB}..."
    systemctl restart "${PG_SVC}"
    retry 8 5 systemctl is-active --quiet "${PG_SVC}"
    sleep 2

    sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -d "${CRON_DB}" -c \
        "CREATE EXTENSION IF NOT EXISTS pg_cron;"
}

install_pg_cron_package
configure_shared_preload
create_extension

log_info "pg_cron installed and active."
