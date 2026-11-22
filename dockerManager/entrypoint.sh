#!/bin/bash
set -eu

PHP=/usr/local/lsws/lsphp82/bin/php
ROOT=/usr/local/lsws/Example/html
READY=/tmp/cyberpanel-wordpress-ready
: "${DB_NAME:?Database name required}"
: "${DB_USER:?Database user required}"
: "${DB_PASSWORD:?Database password required}"
: "${WP_ADMIN_EMAIL:?Administrator email required}"
: "${WP_ADMIN_USER:?Administrator username required}"
: "${WP_ADMIN_PASSWORD:?Administrator password required}"
: "${WP_URL:?Public URL required}"
: "${DB_Host:?Database host required}"
SITE_NAME=${SITE_NAME:-"CyberPanel Site"}

# WordPress, its plugins and wp-config.php are files the website itself can
# rewrite, and wp-cli runs them. It therefore runs as the web server's user,
# never as root. An image without a tool to change user keeps the old way.
if command -v setpriv >/dev/null 2>&1; then
    as_site() { setpriv --reuid=nobody --regid=nogroup --clear-groups "$@"; }
elif command -v runuser >/dev/null 2>&1; then
    as_site() { runuser -u nobody -g nogroup -- "$@"; }
else
    as_site() { "$@" --allow-root; }
fi

wp() {
    HOME=/tmp WP_CLI_CACHE_DIR=/tmp/.wp-cli-cache \
        as_site "$PHP" -d memory_limit=512M /usr/bin/wp --path="$ROOT" "$@"
}

rm -f "$READY"
chown -R nobody:nogroup "$ROOT"
if [ ! -f "$ROOT/wp-includes/version.php" ]; then
    wp core download
fi

# Database containers may be running before their initial database is ready.
ready=0
for attempt in $(seq 1 120); do
    if "$PHP" -r 'mysqli_report(MYSQLI_REPORT_OFF); $host=explode(":", getenv("DB_Host"), 2); $db=@new mysqli($host[0], getenv("DB_USER"), getenv("DB_PASSWORD"), getenv("DB_NAME"), isset($host[1]) ? (int)$host[1] : 3306); exit($db->connect_errno ? 1 : 0);' 2>/dev/null; then
        ready=1
        break
    fi
    sleep 2
 done
[ "$ready" = 1 ] || { echo 'WordPress database did not become ready.' >&2; exit 1; }

if [ ! -f "$ROOT/wp-config.php" ]; then
    HTTPS_CONFIG=''
    case "$WP_URL" in
        https://*) HTTPS_CONFIG="\$_SERVER['HTTPS'] = 'on';" ;;
    esac
    wp config create --dbname="$DB_NAME" --dbuser="$DB_USER" --dbpass="$DB_PASSWORD" \
        --dbhost="$DB_Host" --skip-check --extra-php <<PHP
// TLS terminates at CyberPanel; the container port is bound to loopback only.
$HTTPS_CONFIG
PHP
fi

# Restarts must preserve the existing database, credentials and content.
if ! wp core is-installed >/dev/null 2>&1; then
    wp core install --title="$SITE_NAME" --url="$WP_URL" --admin_user="$WP_ADMIN_USER" \
        --admin_password="$WP_ADMIN_PASSWORD" --admin_email="$WP_ADMIN_EMAIL" --skip-email
    wp plugin install litespeed-cache --activate
fi
wp core is-installed
/usr/local/lsws/bin/lswsctrl start
touch "$READY"

trap '/usr/local/lsws/bin/lswsctrl stop; exit 0' TERM INT
tail -f /dev/null &
wait $!
