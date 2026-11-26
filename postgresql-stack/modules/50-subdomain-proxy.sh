#!/usr/bin/env bash
# Create CyberPanel child domain and configure LiteSpeed reverse proxy to pgAdmin.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PGADMIN_DOMAIN="$(cfg_get pgadmin_domain)"
MASTER_DOMAIN="$(cfg_get master_domain)"
OWNER="$(cfg_get cyberpanel_owner)"
PHP_VER="$(cfg_get cyberpanel_php)"
BIND_HOST="$(cfg_get pgadmin_bind_host)"
BIND_PORT="$(cfg_get pgadmin_bind_port)"
DOCROOT="/home/${MASTER_DOMAIN}/${PGADMIN_DOMAIN}"
VHOST_CONF="/usr/local/lsws/conf/vhosts/${PGADMIN_DOMAIN}/vhost.conf"
MARKER="# POSTGRESQL_STACK_PROXY"

create_child_domain() {
    if [[ -f "${VHOST_CONF}" ]]; then
        log_info "Vhost already exists: ${VHOST_CONF}"
        return 0
    fi
    log_info "Creating child domain ${PGADMIN_DOMAIN} under ${MASTER_DOMAIN}..."
    retry 3 10 cyberpanel createChild \
        --masterDomain "${MASTER_DOMAIN}" \
        --childDomain "${PGADMIN_DOMAIN}" \
        --owner "${OWNER}" \
        --php "${PHP_VER}" \
        --ssl 1 \
        --path "${PGADMIN_DOMAIN}" || {
            log_warn "createChild returned non-zero; checking vhost again."
        }
    sleep 5
    if [[ ! -f "${VHOST_CONF}" ]]; then
        log_error "Failed to create vhost ${VHOST_CONF}. Check CyberPanel owner (${OWNER}) and DNS."
        exit 1
    fi
}

issue_ssl() {
    log_info "Issuing SSL for ${PGADMIN_DOMAIN}..."
    retry 3 15 cyberpanel issueSSL --domainName "${PGADMIN_DOMAIN}" || \
        log_warn "SSL issuance may need DNS propagation; retry later."
}

write_docroot_htaccess() {
    mkdir -p "${DOCROOT}/.well-known/acme-challenge"
    cat > "${DOCROOT}/.htaccess" <<'EOF'
# postgresql-stack: proxy handled in vhost.conf (ExtProcessor pgadmin4)
RewriteEngine On
RewriteCond %{HTTPS} !=on
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]

<Files "config.php">
    Order Allow,Deny
    Deny from all
</Files>
<Files ".env*">
    Order Allow,Deny
    Deny from all
</Files>
<FilesMatch "\.(log|sql|bak|backup|key|pem|crt|tmp|temp|cache)$">
    Order Allow,Deny
    Deny from all
</FilesMatch>
EOF
    chown newst3922:nobody "${DOCROOT}" 2>/dev/null || true
    find "${DOCROOT}" -exec chown newst3922:newst3922 {} \; 2>/dev/null || true
    chmod 755 "${DOCROOT}"
    chmod 644 "${DOCROOT}/.htaccess"
}

configure_vhost_proxy() {
    if [[ ! -f "${VHOST_CONF}" ]]; then
        log_error "Vhost not found: ${VHOST_CONF}. Create domain in CyberPanel first."
        exit 1
    fi

    fix_acme_challenge_context

    if grep -q "${MARKER}" "${VHOST_CONF}"; then
        log_info "Reverse proxy already configured in vhost."
        return 0
    fi

    log_info "Patching vhost.conf for pgAdmin reverse proxy..."
    cp -a "${VHOST_CONF}" "${VHOST_CONF}.bak.postgresql-stack"

    # Remove default PHP scripthandler block if present (proxy replaces it)
    python3 <<PY
from pathlib import Path
import re

path = Path("${VHOST_CONF}")
text = path.read_text()
marker = "${MARKER}"

proxy_block = f'''
{marker}
extprocessor pgadmin4 {{
  type                    proxy
  address                 http://${BIND_HOST}:${BIND_PORT}
  maxConns                60
  pcKeepAliveTimeout      -1
  initTimeout             60
  retryTimeout            60
  respBuffer              0
}}

context / {{
  type                    proxy
  handler                 pgadmin4
  addDefaultCharset       off
}}
'''

# Strip existing scripthandler / extprocessor lsapi blocks for clean proxy
text = re.sub(r'scripthandler\s*\{[^}]*\}\s*', '', text, flags=re.DOTALL)
text = re.sub(r'extprocessor\s+\w+\s*\{[^}]*type\s+lsapi[^}]*\}\s*', '', text, flags=re.DOTALL)

if 'rewrite  {' in text:
    text = re.sub(
        r'rewrite\s*\{[^}]*autoLoadHtaccess\s+1[^}]*\}',
        'rewrite  {\\n  enable                  1\\n  autoLoadHtaccess        1\\n}',
        text,
        count=1,
        flags=re.DOTALL,
    )

if 'vhssl {' in text:
    parts = text.split('vhssl {', 1)
    text = parts[0].rstrip() + '\\n' + proxy_block + '\\nvhssl {' + parts[1]
else:
    text = text.rstrip() + '\\n' + proxy_block

path.write_text(text)
PY

    log_info "vhost.conf updated."
}

fix_acme_challenge_context() {
    if [[ ! -f "${VHOST_CONF}" ]]; then
        return 0
    fi
    local challenge_dir="${DOCROOT}/.well-known/acme-challenge"
    mkdir -p "${challenge_dir}"
    chmod 755 "${DOCROOT}/.well-known" "${challenge_dir}" 2>/dev/null || true
    find "${DOCROOT}/.well-known" -exec chown newst3922:newst3922 {} \; 2>/dev/null || true

    TARGET="${VHOST_CONF}" CHALLENGE_DIR="${challenge_dir}" python3 <<'PY'
import os, re
from pathlib import Path

path = Path(os.environ["TARGET"])
challenge_dir = os.environ["CHALLENGE_DIR"]
text = path.read_text()

block = f'''context /.well-known/acme-challenge {{
  location                {challenge_dir}
  allowBrowse             1

  rewrite  {{
     enable                  0
  }}
  addDefaultCharset       off

  phpIniOverride  {{

  }}
}}'''

if 'context /.well-known/acme-challenge' in text:
    text = re.sub(
        r'context /\.well-known/acme-challenge\s*\{.*?\n\}',
        block,
        text,
        count=1,
        flags=re.DOTALL,
    )
else:
    anchor = 'rewrite  {'
    if anchor not in text:
        raise SystemExit('rewrite block not found in vhost.conf')
    text = text.replace(anchor, block + '\n\n' + anchor, 1)

path.write_text(text)
print('acme challenge context updated')
PY
    log_info "ACME challenge path set to ${challenge_dir}"
}

create_child_domain
write_docroot_htaccess
configure_vhost_proxy
issue_ssl
restart_lsws

log_info "Reverse proxy configured: https://${PGADMIN_DOMAIN}/ -> http://${BIND_HOST}:${BIND_PORT}/"
