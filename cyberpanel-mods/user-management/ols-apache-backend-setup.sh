#!/bin/bash

# OLS + Apache backend auto-config for CyberPanel domains/sub-domains.
# Idempotent: safe to run repeatedly for same domain.

set -u

LOG_FILE="/var/log/cyberpanel_ols_apache_backend.log"
MAX_RETRIES=3

log_msg() {
    local level="$1"
    local module="$2"
    local message="$3"
    local retry="${4:-0}"
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$ts] [$level] [$module] retry=$retry domain=${TARGET_DOMAIN:-unknown} - $message" | tee -a "$LOG_FILE"
}

fail() {
    log_msg "ERROR" "setup" "$1" "${2:-0}"
    exit 1
}

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        fail "This script must run as root"
    fi
}

domain_valid() {
    local d="$1"
    [[ "$d" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]
}

detect_docroot() {
    local domain="$1"
    local vhost_conf="/usr/local/lsws/conf/vhosts/${domain}/vhost.conf"
    local docroot=""

    if [[ -f "$vhost_conf" ]]; then
        docroot="$(awk '$1=="docRoot"{print $2; exit}' "$vhost_conf" 2>/dev/null)"
    fi
    if [[ -z "$docroot" ]]; then
        docroot="/home/${domain}"
    fi
    echo "$docroot"
}

ensure_apache_conf() {
    local domain="$1"
    local docroot="$2"
    local owner="${3:-newst3922}"
    local group="${4:-newst3922}"
    local apache_conf="/etc/httpd/conf.d/${domain}.ols-apache-backend.conf"
    local cert_dir="/etc/letsencrypt/live/${domain}"
    local cert_file="${cert_dir}/fullchain.pem"
    local key_file="${cert_dir}/privkey.pem"

    if [[ ! -f "$cert_file" || ! -f "$key_file" ]]; then
        cert_file="/etc/httpd/conf.d/ssl/.fullchain.pem"
        key_file="/etc/httpd/conf.d/ssl/.privkey.pem"
    fi

    mkdir -p "$(dirname "$apache_conf")" || return 1
    cat > "$apache_conf" <<EOF
<VirtualHost *:8083>
    ServerName ${domain}
    ServerAlias www.${domain}
    ServerAdmin root@localhost
    SuexecUserGroup ${owner} ${group}
    DocumentRoot ${docroot}

    <FilesMatch \\.php$>
        SetHandler "proxy:unix:/var/run/php-fpm/${domain}.sock|fcgi://localhost"
    </FilesMatch>

    <Directory ${docroot}>
        Options Indexes FollowSymLinks
        AllowOverride all
        Require all granted
        DirectoryIndex index.php index.html
    </Directory>
</VirtualHost>

<VirtualHost *:8082>
    ServerName ${domain}
    ServerAlias www.${domain}
    ServerAdmin root@localhost
    SuexecUserGroup ${owner} ${group}
    DocumentRoot ${docroot}

    <FilesMatch \\.php$>
        SetHandler "proxy:unix:/var/run/php-fpm/${domain}.sock|fcgi://localhost"
    </FilesMatch>

    <Directory ${docroot}>
        Options Indexes FollowSymLinks
        AllowOverride all
        Require all granted
        DirectoryIndex index.php index.html
    </Directory>

    SSLEngine on
    SSLVerifyClient none
    SSLCertificateFile ${cert_file}
    SSLCertificateKeyFile ${key_file}
</VirtualHost>
EOF
    return 0
}

ensure_ols_proxy_rewrite() {
    local domain="$1"
    local vhost_conf="/usr/local/lsws/conf/vhosts/${domain}/vhost.conf"
    local tmp_file="${vhost_conf}.tmp.$$"
    local marker="AUTO_OLS_APACHE_BACKEND"

    [[ -f "$vhost_conf" ]] || return 1

    awk '
        BEGIN { in_rewrite=0; depth=0 }
        {
            if ($1=="rewrite" && $2=="{") {
                in_rewrite=1;
                depth=1;
                next;
            }
            if (in_rewrite==1) {
                if (index($0, "{")>0) depth++;
                if (index($0, "}")>0) depth--;
                if (depth<=0) { in_rewrite=0; next; }
                next;
            }
            print $0;
        }
    ' "$vhost_conf" > "$tmp_file" || return 1

    cat >> "$tmp_file" <<'EOF'
rewrite  {
  enable                  1
  autoLoadHtaccess        0
  rules                   <<<END_rules
RewriteEngine On
# AUTO_OLS_APACHE_BACKEND
RewriteCond %{HTTPS} !=on
RewriteRule ^(.*)$ HTTP://apachebackend/$1 [P,L]
RewriteRule ^(.*)$ HTTP://proxyApacheBackendSSL/$1 [P,L]
  END_rules
}
EOF

    mv "$tmp_file" "$vhost_conf" || return 1
    return 0
}

ensure_httpd_running() {
    if ! systemctl is-active --quiet httpd; then
        systemctl start httpd || return 1
    fi
    systemctl enable httpd >/dev/null 2>&1 || true
    return 0
}

check_ports() {
    local has_8082
    local has_8083
    has_8082="$(ss -tln 2>/dev/null | awk '$4 ~ /:8082$/ {print "1"; exit}')"
    has_8083="$(ss -tln 2>/dev/null | awk '$4 ~ /:8083$/ {print "1"; exit}')"
    [[ "$has_8082" == "1" && "$has_8083" == "1" ]] || return 1
    return 0
}

health_check_domain() {
    local domain="$1"
    local code
    code="$(curl -k -sS -o /dev/null -w "%{http_code}" "https://${domain}/" 2>/dev/null || true)"
    [[ "$code" != "503" && "$code" != "000" && "$code" != "" ]]
}

rollback_file_if_needed() {
    local src="$1"
    local backup="$2"
    if [[ -f "$backup" ]]; then
        cp -f "$backup" "$src" >/dev/null 2>&1 || true
    fi
}

main() {
    require_root

    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 --domain <domain> [--owner <user>] [--group <group>] [--docroot <path>]"
        exit 0
    fi

    local owner="newst3922"
    local group="newst3922"
    local docroot=""
    local domain=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --domain) domain="${2:-}"; shift 2 ;;
            --owner) owner="${2:-}"; shift 2 ;;
            --group) group="${2:-}"; shift 2 ;;
            --docroot) docroot="${2:-}"; shift 2 ;;
            *) fail "Unknown argument: $1" ;;
        esac
    done

    TARGET_DOMAIN="$domain"
    domain_valid "$domain" || fail "Invalid or missing domain"
    [[ -n "$docroot" ]] || docroot="$(detect_docroot "$domain")"
    [[ -d "$docroot" ]] || fail "Docroot does not exist: $docroot"

    local vhost_conf="/usr/local/lsws/conf/vhosts/${domain}/vhost.conf"
    local apache_conf="/etc/httpd/conf.d/${domain}.ols-apache-backend.conf"
    [[ -f "$vhost_conf" ]] || fail "OLS vhost config not found: $vhost_conf"

    local vhost_bak="${vhost_conf}.bak.$(date +%s)"
    local apache_bak="${apache_conf}.bak.$(date +%s)"
    cp -f "$vhost_conf" "$vhost_bak" || fail "Failed to backup OLS vhost"
    [[ -f "$apache_conf" ]] && cp -f "$apache_conf" "$apache_bak" || true

    log_msg "INFO" "setup" "Starting OLS+Apache backend setup"

    local attempt=1
    while [[ $attempt -le $MAX_RETRIES ]]; do
        if ! ensure_apache_conf "$domain" "$docroot" "$owner" "$group"; then
            log_msg "WARN" "apache" "Failed writing Apache config" "$attempt"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! ensure_ols_proxy_rewrite "$domain"; then
            log_msg "WARN" "ols" "Failed writing OLS proxy rewrite" "$attempt"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! httpd -t >/dev/null 2>&1; then
            log_msg "WARN" "validate" "Apache syntax validation failed" "$attempt"
            rollback_file_if_needed "$apache_conf" "$apache_bak"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! ensure_httpd_running; then
            log_msg "WARN" "service" "Could not start/enable httpd" "$attempt"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! systemctl restart lsws >/dev/null 2>&1; then
            log_msg "WARN" "service" "LSWS restart failed" "$attempt"
            rollback_file_if_needed "$vhost_conf" "$vhost_bak"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! check_ports; then
            log_msg "WARN" "validate" "Ports 8082/8083 are not listening" "$attempt"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        if ! health_check_domain "$domain"; then
            log_msg "WARN" "health" "Domain health check failed (503/000)" "$attempt"
            attempt=$((attempt + 1))
            sleep 1
            continue
        fi

        log_msg "INFO" "setup" "Apache backend configured, ports verified, vhost health check passed"
        exit 0
    done

    rollback_file_if_needed "$vhost_conf" "$vhost_bak"
    rollback_file_if_needed "$apache_conf" "$apache_bak"
    fail "Failed to configure OLS+Apache backend after ${MAX_RETRIES} retries" "$MAX_RETRIES"
}

main "$@"
