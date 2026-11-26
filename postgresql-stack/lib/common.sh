#!/usr/bin/env bash
# Shared helpers for postgresql-stack installer.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export STACK_ROOT

LOG_FILE="${STACK_ROOT}/logs/install.log"
CONFIG_PHP="${STACK_ROOT}/config.php"

log() {
    local level="$1"
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*"
    echo "${msg}" | tee -a "${LOG_FILE}"
}

log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        log_error "This script must run as root."
        exit 1
    fi
}

require_almalinux() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot detect OS."
        exit 1
    fi
    # shellcheck source=/dev/null
    source /etc/os-release
    if [[ "${ID:-}" != "almalinux" && "${ID:-}" != "rhel" && "${ID:-}" != "rocky" ]]; then
        log_warn "OS is ${ID:-unknown}; installer targets AlmaLinux/RHEL 9."
    fi
}

retry() {
    local max_attempts="${1:-5}"
    local delay="${2:-5}"
    shift 2
    local attempt=1
    while true; do
        if "$@"; then
            return 0
        fi
        if [[ "${attempt}" -ge "${max_attempts}" ]]; then
            log_error "Command failed after ${max_attempts} attempts: $*"
            return 1
        fi
        log_warn "Attempt ${attempt}/${max_attempts} failed; retry in ${delay}s: $*"
        sleep "${delay}"
        attempt=$((attempt + 1))
    done
}

gen_secret() {
    local len="${1:-32}"
    python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(${len})))"
}

ensure_dirs() {
    mkdir -p "${STACK_ROOT}/logs" "${STACK_ROOT}/tmp" "${STACK_ROOT}/Test"
    touch "${LOG_FILE}"
    chmod 750 "${STACK_ROOT}/logs"
}

load_config() {
    if [[ ! -f "${CONFIG_PHP}" ]]; then
        log_error "Missing config.php at ${CONFIG_PHP}. Run install.sh first."
        exit 1
    fi
}

cfg_get() {
    local key="$1"
    php -r "
        define('APP_INIT', true);
        require '${CONFIG_PHP}';
        if (!isset(\$config['${key}'])) { fwrite(STDERR, 'missing key'); exit(2); }
        echo \$config['${key}'];
    " 2>/dev/null
}

init_config_if_missing() {
    if [[ -f "${CONFIG_PHP}" ]]; then
        log_info "config.php exists; preserving secrets."
        return 0
    fi

    local pg_pass pgadmin_pass pgadmin_email
    pg_pass="$(gen_secret 24)"
    pgadmin_pass="$(gen_secret 20)"
    pgadmin_email="pgadmin@$(hostname -f 2>/dev/null || echo 'localhost')"

    cat > "${CONFIG_PHP}" <<EOFPHP
<?php
if (!defined('APP_INIT')) {
    http_response_code(404);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!DOCTYPE html><html><head><title>404 Not Found</title></head><body><h1>404 Not Found</h1></body></html>';
    exit;
}

\$config = array(
    'pg_version' => '17',
    'pg_port' => 5432,
    'pg_superuser' => 'postgres',
    'pg_superuser_password' => '${pg_pass}',
    'pg_app_user' => 'pgstack_app',
    'pg_app_password' => '$(gen_secret 24)',
    'pg_cron_database' => 'postgres',
    'pgadmin_email' => '${pgadmin_email}',
    'pgadmin_password' => '${pgadmin_pass}',
    'pgadmin_bind_host' => '127.0.0.1',
    'pgadmin_bind_port' => 5050,
    'pgadmin_domain' => 'pgadmin.newstargeted.com',
    'master_domain' => 'newstargeted.com',
    'cyberpanel_owner' => 'Admin',
    'cyberpanel_php' => '8.3',
    'with_pgagent' => false,
    'install_tile' => true,
    'installed_at' => '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
);
EOFPHP
    chmod 600 "${CONFIG_PHP}"
    log_info "Generated config.php (secrets not logged)."
}

update_config_value() {
    local key="$1"
    local value="$2"
    CONFIG_PHP="${CONFIG_PHP}" CFG_KEY="${key}" CFG_VALUE="${value}" php -r '
        define("APP_INIT", true);
        $path = getenv("CONFIG_PHP");
        require $path;
        $k = getenv("CFG_KEY");
        $v = getenv("CFG_VALUE");
        if ($v === "true") {
            $v = true;
        } elseif ($v === "false") {
            $v = false;
        } elseif (preg_match("/^[0-9]+$/", (string) $v)) {
            $v = (int) $v;
        }
        $config[$k] = $v;
        $body = "<?php\nif (!defined(\"APP_INIT\")) { http_response_code(404); exit; }\n\n\$config = " . var_export($config, true) . ";\n";
        file_put_contents($path, $body);
    '
    chmod 600 "${CONFIG_PHP}"
}

restart_lsws() {
    log_info "Restarting LiteSpeed (lsws)..."
    if systemctl is-active --quiet lsws 2>/dev/null; then
        systemctl restart lsws
    elif [[ -x /usr/local/lsws/bin/lsctl ]]; then
        /usr/local/lsws/bin/lsctl restart
    else
        service lsws restart
    fi
    sleep 2
}

pg_service_name() {
    local ver
    ver="$(cfg_get pg_version 2>/dev/null || echo '17')"
    echo "postgresql-${ver}"
}

pg_bin_dir() {
    local ver
    ver="$(cfg_get pg_version 2>/dev/null || echo '17')"
    if [[ -d "/usr/pgsql-${ver}/bin" ]]; then
        echo "/usr/pgsql-${ver}/bin"
    else
        echo "/usr/bin"
    fi
}

pg_data_dir() {
    local ver
    ver="$(cfg_get pg_version 2>/dev/null || echo '17')"
    echo "/var/lib/pgsql/${ver}/data"
}

pg_conf_file() {
    echo "$(pg_data_dir)/postgresql.conf"
}

run_module() {
    local script="${STACK_ROOT}/modules/${1}"
    if [[ ! -f "${script}" ]]; then
        log_error "Missing module: ${script}"
        exit 1
    fi
    log_info "Running module: $(basename "${script}")"
    # shellcheck source=/dev/null
    source "${STACK_ROOT}/lib/common.sh"
    bash "${script}"
}
