#!/usr/bin/env bash
# Install PostgreSQL server from PGDG (AlmaLinux 9).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PG_VER="$(cfg_get pg_version)"
PG_SVC="$(pg_service_name)"
PG_BIN="$(pg_bin_dir)"
PG_DATA="$(pg_data_dir)"
PG_PASS="$(cfg_get pg_superuser_password)"
APP_USER="$(cfg_get pg_app_user)"
APP_PASS="$(cfg_get pg_app_password)"

install_pgdg_repo() {
    if rpm -q pgdg-redhat-repo >/dev/null 2>&1; then
        log_info "PGDG repo already installed."
        return 0
    fi
    log_info "Installing PGDG repository..."
    retry 3 5 dnf install -y "https://download.postgresql.org/pub/repos/yum/reporpms/EL-$(rpm -E '%{rhel}')-$(uname -m)/pgdg-redhat-repo-latest.noarch.rpm"
    dnf -qy module disable postgresql 2>/dev/null || true
}

install_packages() {
    log_info "Installing PostgreSQL ${PG_VER} packages..."
    retry 3 10 dnf install -y \
        "postgresql${PG_VER}-server" \
        "postgresql${PG_VER}-contrib" \
        "postgresql${PG_VER}"
    # system_stats powers the pgAdmin Dashboard > System tab.
    if ! dnf install -y "system_stats_${PG_VER}" 2>/dev/null; then
        log_warn "system_stats_${PG_VER} package not available; pgAdmin System tab will be limited."
    fi
}

create_system_stats_extension() {
    # Created in the maintenance DB so pgAdmin's Dashboard > System tab works.
    if ! rpm -q "system_stats_${PG_VER}" >/dev/null 2>&1; then
        return 0
    fi
    log_info "Creating system_stats extension in 'postgres' database..."
    sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -d postgres -c \
        "CREATE EXTENSION IF NOT EXISTS system_stats;" || \
        log_warn "Could not create system_stats extension."
}

init_database() {
    if [[ -f "${PG_DATA}/PG_VERSION" ]]; then
        log_info "PostgreSQL data directory already initialized."
        return 0
    fi
    log_info "Initializing PostgreSQL cluster..."
    "${PG_BIN}/postgresql-${PG_VER}-setup" initdb
}

configure_postgresql() {
    local conf="${PG_DATA}/postgresql.conf"
    local hba="${PG_DATA}/pg_hba.conf"

    log_info "Configuring PostgreSQL (localhost only)..."
    if grep -q "^listen_addresses" "${conf}"; then
        sed -i "s/^#*listen_addresses.*/listen_addresses = 'localhost'/" "${conf}"
    else
        echo "listen_addresses = 'localhost'" >> "${conf}"
    fi

    if ! grep -q "^port" "${conf}"; then
        echo "port = $(cfg_get pg_port)" >> "${conf}"
    fi

    # Local peer for postgres OS user; scram for TCP localhost
    if ! grep -q "postgresql-stack" "${hba}"; then
        cat >> "${hba}" <<'EOF'

# postgresql-stack
local   all             postgres                                peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
EOF
    fi
}

set_postgres_password() {
    log_info "Setting postgres superuser password..."
    systemctl enable "${PG_SVC}"
    systemctl start "${PG_SVC}"
    retry 5 3 systemctl is-active --quiet "${PG_SVC}"

    sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -c \
        "ALTER USER postgres WITH PASSWORD '$(echo "${PG_PASS}" | sed "s/'/''/g")';"
}

run_bootstrap_sql() {
    local sql_file="/tmp/postgresql-stack-bootstrap-$$.sql"
    sed -e "s/__PG_APP_USER__/${APP_USER}/g" \
        -e "s/__PG_APP_PASSWORD__/$(echo "${APP_PASS}" | sed "s/'/''/g")/g" \
        "${STACK_ROOT}/sql/bootstrap.sql" > "${sql_file}"
    chmod 644 "${sql_file}"

    log_info "Running bootstrap SQL..."
    sudo -u postgres env PATH="${PG_BIN}:$PATH" psql -v ON_ERROR_STOP=1 -f "${sql_file}"
    rm -f "${sql_file}"
}

install_pgdg_repo
install_packages
init_database
configure_postgresql
systemctl enable "${PG_SVC}"
systemctl restart "${PG_SVC}"
retry 5 3 systemctl is-active --quiet "${PG_SVC}"
set_postgres_password
run_bootstrap_sql
create_system_stats_extension

log_info "PostgreSQL ${PG_VER} is running (localhost only)."
