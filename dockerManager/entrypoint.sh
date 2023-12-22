#!/bin/bash

# Environment variables for WordPress installation
DB_NAME=${DB_NAME:-"wordpress"}
DB_USER=${DB_USER:-"wpuser"}
DB_PASSWORD=${DB_PASSWORD:-"wppassword"}
WP_ADMIN_EMAIL=${WP_ADMIN_EMAIL:-"admin@example.com"}
WP_ADMIN_USER=${WP_ADMIN_USER:-"admin"}
WP_ADMIN_PASSWORD=${WP_ADMIN_PASSWORD:-"adminpass"}
WP_URL=${WP_URL:-"docker.cyberpanel.net"}
DB_Host=${DB_Host:-"mariadb:3306"}
SITE_NAME=${SITE_NAME:-"CyberPanel Site"}

# Install WordPress using WP CLI
/usr/local/lsws/lsphp82/bin/php /usr/bin/wp core download --path=/usr/local/lsws/Example/html --allow-root

# Set up WP config
/usr/local/lsws/lsphp82/bin/php /usr/bin/wp core config --dbname="$DB_NAME" --dbuser="$DB_USER" --dbpass="$DB_PASSWORD" --path="/usr/local/lsws/Example/html" --dbhost="$DB_Host" --skip-check --allow-root

# Install WordPress
/usr/local/lsws/lsphp82/bin/php /usr/bin/wp core install --title="$SITE_NAME" --url="$WP_URL" --title="My WordPress Site" --admin_user="$WP_ADMIN_USER" --admin_password="$WP_ADMIN_PASSWORD" --admin_email="$WP_ADMIN_EMAIL" --path="/usr/local/lsws/Example/html" --skip-email --allow-root

### Install LSCache plugin

/usr/local/lsws/lsphp82/bin/php /usr/bin/wp plugin install litespeed-cache --allow-root --path="/usr/local/lsws/Example/html" --activate

# Start OpenLiteSpeed
/usr/local/lsws/bin/lswsctrl start

# Keep container running
tail -f /dev/null