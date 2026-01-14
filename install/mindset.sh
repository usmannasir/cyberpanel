#!/bin/bash
#####################################################################
#                                                                   #
#   MINDSET - Laravel-Native Hosting Platform                       #
#   Single-Script Installer                                         #
#                                                                   #
#   Usage: curl -fsSL https://mindset.sh/install.sh | bash          #
#                                                                   #
#   Supported: Ubuntu 20.04, 22.04, 24.04                          #
#                                                                   #
#####################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Mindset version
MINDSET_VERSION="1.0.0"
MINDSET_REPO="https://github.com/mindset-hosting/mindset.git"
MINDSET_BRANCH="main"

# Installation paths
MINDSET_PATH="/opt/mindset"
CONFIG_PATH="/etc/mindset"
DATA_PATH="/var/lib/mindset"
LOG_PATH="/var/log/mindset"

# Default settings
PHP_VERSION="8.3"
MYSQL_ROOT_PASSWORD=""
ADMIN_EMAIL=""
ADMIN_PASSWORD=""
HOSTNAME=""
INSTALL_MAIL="no"
INSTALL_DNS="no"
INSTALL_REDIS="yes"
INSTALL_OLLAMA="no"

#####################################################################
# Helper Functions
#####################################################################

print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║   ███╗   ███╗██╗███╗   ██╗██████╗ ███████╗███████╗████████╗  ║"
    echo "║   ████╗ ████║██║████╗  ██║██╔══██╗██╔════╝██╔════╝╚══██╔══╝  ║"
    echo "║   ██╔████╔██║██║██╔██╗ ██║██║  ██║███████╗█████╗     ██║     ║"
    echo "║   ██║╚██╔╝██║██║██║╚██╗██║██║  ██║╚════██║██╔══╝     ██║     ║"
    echo "║   ██║ ╚═╝ ██║██║██║ ╚████║██████╔╝███████║███████╗   ██║     ║"
    echo "║   ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚══════╝   ╚═╝     ║"
    echo "║                                                              ║"
    echo "║          Laravel-Native Hosting Platform v${MINDSET_VERSION}              ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo bash install.sh"
    fi
}

generate_password() {
    openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24
}

#####################################################################
# Pre-flight Checks
#####################################################################

preflight_checks() {
    log "Running pre-flight checks..."

    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        error "Cannot detect operating system"
    fi

    source /etc/os-release

    if [[ "$ID" != "ubuntu" ]]; then
        error "This installer only supports Ubuntu. Detected: $ID"
    fi

    case "$VERSION_ID" in
        "20.04"|"22.04"|"24.04")
            log "Detected Ubuntu $VERSION_ID - Supported"
            ;;
        *)
            error "Ubuntu $VERSION_ID is not supported. Supported versions: 20.04, 22.04, 24.04"
            ;;
    esac

    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
        error "Unsupported architecture: $ARCH. Only x86_64 and aarch64 are supported."
    fi

    # Check minimum resources
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_MEM -lt 1800 ]]; then
        warn "Minimum 2GB RAM recommended. Found: ${TOTAL_MEM}MB"
    fi

    DISK_FREE=$(df -BG / | awk 'NR==2 {print $4}' | tr -dc '0-9')
    if [[ $DISK_FREE -lt 15 ]]; then
        error "Minimum 15GB free disk space required. Found: ${DISK_FREE}GB"
    fi

    # Check network
    if ! ping -c 1 google.com &> /dev/null; then
        error "No network connectivity. Please check your internet connection."
    fi

    # Check for existing installations
    if [[ -d "$MINDSET_PATH" ]]; then
        warn "Existing Mindset installation found at $MINDSET_PATH"
        read -p "Do you want to upgrade/reinstall? [y/N]: " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            error "Installation cancelled"
        fi
    fi

    # Check for conflicting software
    if systemctl is-active --quiet apache2 2>/dev/null; then
        warn "Apache2 is running and will be stopped"
        systemctl stop apache2 || true
        systemctl disable apache2 || true
    fi

    if systemctl is-active --quiet nginx 2>/dev/null; then
        warn "Nginx is running and will be stopped"
        systemctl stop nginx || true
        systemctl disable nginx || true
    fi

    log "Pre-flight checks completed successfully"
}

#####################################################################
# Interactive Setup
#####################################################################

interactive_setup() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    MINDSET INSTALLATION                        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Hostname
    DEFAULT_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
    read -p "Server hostname [$DEFAULT_HOSTNAME]: " input_hostname
    HOSTNAME=${input_hostname:-$DEFAULT_HOSTNAME}

    # Admin email
    while [[ -z "$ADMIN_EMAIL" ]]; do
        read -p "Admin email address: " ADMIN_EMAIL
        if [[ ! "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            warn "Invalid email format. Please try again."
            ADMIN_EMAIL=""
        fi
    done

    # Admin password
    while [[ -z "$ADMIN_PASSWORD" ]]; do
        read -sp "Admin password (min 8 chars): " ADMIN_PASSWORD
        echo ""
        if [[ ${#ADMIN_PASSWORD} -lt 8 ]]; then
            warn "Password must be at least 8 characters"
            ADMIN_PASSWORD=""
        fi
    done

    # MySQL root password
    MYSQL_ROOT_PASSWORD=$(generate_password)
    info "Generated MySQL root password (saved to /root/.mindset-credentials)"

    # Optional components
    echo ""
    echo -e "${CYAN}Optional Components:${NC}"

    read -p "Install Redis for caching/queues? [Y/n]: " input_redis
    INSTALL_REDIS=${input_redis:-yes}
    [[ "$INSTALL_REDIS" =~ ^[Yy]$ || "$INSTALL_REDIS" == "yes" ]] && INSTALL_REDIS="yes" || INSTALL_REDIS="no"

    read -p "Install Ollama for local AI? [y/N]: " input_ollama
    INSTALL_OLLAMA=${input_ollama:-no}
    [[ "$INSTALL_OLLAMA" =~ ^[Yy]$ || "$INSTALL_OLLAMA" == "yes" ]] && INSTALL_OLLAMA="yes" || INSTALL_OLLAMA="no"

    read -p "Install email server (Postfix/Dovecot)? [y/N]: " input_mail
    INSTALL_MAIL=${input_mail:-no}
    [[ "$INSTALL_MAIL" =~ ^[Yy]$ || "$INSTALL_MAIL" == "yes" ]] && INSTALL_MAIL="yes" || INSTALL_MAIL="no"

    read -p "Install DNS server (PowerDNS)? [y/N]: " input_dns
    INSTALL_DNS=${input_dns:-no}
    [[ "$INSTALL_DNS" =~ ^[Yy]$ || "$INSTALL_DNS" == "yes" ]] && INSTALL_DNS="yes" || INSTALL_DNS="no"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    INSTALLATION SUMMARY                        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Hostname:     $HOSTNAME"
    echo "  Admin Email:  $ADMIN_EMAIL"
    echo "  PHP Version:  $PHP_VERSION"
    echo "  Redis:        $INSTALL_REDIS"
    echo "  Ollama AI:    $INSTALL_OLLAMA"
    echo "  Mail Server:  $INSTALL_MAIL"
    echo "  DNS Server:   $INSTALL_DNS"
    echo ""

    read -p "Proceed with installation? [Y/n]: " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        error "Installation cancelled"
    fi
}

#####################################################################
# System Preparation
#####################################################################

prepare_system() {
    log "Preparing system..."

    # Update package lists
    apt-get update -y

    # Install essential packages
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        wget \
        git \
        unzip \
        zip \
        acl \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        jq

    # Set timezone
    timedatectl set-timezone UTC

    # Create mindset user
    if ! id "mindset" &>/dev/null; then
        useradd -r -s /bin/false mindset
    fi

    # Create directories
    mkdir -p "$MINDSET_PATH"
    mkdir -p "$CONFIG_PATH"
    mkdir -p "$DATA_PATH"/{backups,secrets,cache}
    mkdir -p "$LOG_PATH"

    # Set ownership
    chown -R mindset:mindset "$DATA_PATH"
    chown -R mindset:mindset "$LOG_PATH"

    log "System preparation completed"
}

#####################################################################
# Security Hardening
#####################################################################

harden_security() {
    log "Applying security hardening..."

    # Configure UFW firewall
    apt-get install -y ufw

    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH
    ufw allow 22/tcp

    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Allow Mindset panel
    ufw allow 8090/tcp

    # Allow OpenLiteSpeed admin (localhost only by default)
    # ufw allow 7080/tcp

    # Enable UFW
    echo "y" | ufw enable

    # Install and configure Fail2Ban
    apt-get install -y fail2ban

    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

[mindset-auth]
enabled = true
port = 8090
filter = mindset-auth
logpath = /var/log/mindset/access.log
maxretry = 5
bantime = 3600
EOF

    cat > /etc/fail2ban/filter.d/mindset-auth.conf << 'EOF'
[Definition]
failregex = ^<HOST>.*"(POST|GET).*/(login|api/auth).*" (401|403)
ignoreregex =
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban

    # SSH hardening
    if [[ -f /etc/ssh/sshd_config ]]; then
        # Backup original
        cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

        # Apply hardening
        sed -i 's/#PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
        sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
        sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config

        systemctl restart sshd
    fi

    # Enable automatic security updates
    apt-get install -y unattended-upgrades

    cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

    dpkg-reconfigure -plow unattended-upgrades

    log "Security hardening completed"
}

#####################################################################
# Install OpenLiteSpeed
#####################################################################

install_openlitespeed() {
    log "Installing OpenLiteSpeed..."

    # Add LiteSpeed repository
    wget -qO - https://repo.litespeed.sh | bash

    # Install OpenLiteSpeed
    apt-get install -y openlitespeed

    # Install PHP
    apt-get install -y \
        lsphp${PHP_VERSION//./} \
        lsphp${PHP_VERSION//./}-common \
        lsphp${PHP_VERSION//./}-curl \
        lsphp${PHP_VERSION//./}-mysql \
        lsphp${PHP_VERSION//./}-opcache \
        lsphp${PHP_VERSION//./}-imap \
        lsphp${PHP_VERSION//./}-intl \
        lsphp${PHP_VERSION//./}-pgsql \
        lsphp${PHP_VERSION//./}-sqlite3 \
        lsphp${PHP_VERSION//./}-redis \
        lsphp${PHP_VERSION//./}-imagick \
        lsphp${PHP_VERSION//./}-mbstring \
        lsphp${PHP_VERSION//./}-xml \
        lsphp${PHP_VERSION//./}-zip \
        lsphp${PHP_VERSION//./}-bcmath \
        lsphp${PHP_VERSION//./}-gd \
        lsphp${PHP_VERSION//./}-soap

    # Set default PHP for CLI
    update-alternatives --install /usr/bin/php php /usr/local/lsws/lsphp${PHP_VERSION//./}/bin/php 100

    # Configure PHP
    PHP_INI="/usr/local/lsws/lsphp${PHP_VERSION//./}/etc/php/${PHP_VERSION}/litespeed/php.ini"

    if [[ -f "$PHP_INI" ]]; then
        # Performance settings
        sed -i 's/memory_limit = .*/memory_limit = 512M/' "$PHP_INI"
        sed -i 's/upload_max_filesize = .*/upload_max_filesize = 256M/' "$PHP_INI"
        sed -i 's/post_max_size = .*/post_max_size = 256M/' "$PHP_INI"
        sed -i 's/max_execution_time = .*/max_execution_time = 300/' "$PHP_INI"
        sed -i 's/max_input_time = .*/max_input_time = 300/' "$PHP_INI"

        # Security settings
        sed -i 's/expose_php = .*/expose_php = Off/' "$PHP_INI"
        sed -i 's/display_errors = .*/display_errors = Off/' "$PHP_INI"
        sed -i 's/log_errors = .*/log_errors = On/' "$PHP_INI"

        # OPcache settings
        cat >> "$PHP_INI" << 'EOF'

; OPcache Configuration
opcache.enable=1
opcache.memory_consumption=256
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.revalidate_freq=0
opcache.validate_timestamps=0
opcache.save_comments=1
opcache.jit=1255
opcache.jit_buffer_size=128M
EOF
    fi

    # Set OLS admin password
    OLS_ADMIN_PASSWORD=$(generate_password)
    /usr/local/lsws/admin/misc/admpass.sh <<< "admin
$OLS_ADMIN_PASSWORD
$OLS_ADMIN_PASSWORD"

    # Start OpenLiteSpeed
    systemctl enable lsws
    systemctl start lsws

    log "OpenLiteSpeed installed successfully"
}

#####################################################################
# Install MySQL
#####################################################################

install_mysql() {
    log "Installing MySQL 8.0..."

    # Set root password for non-interactive install
    debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_ROOT_PASSWORD"
    debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_ROOT_PASSWORD"

    apt-get install -y mysql-server mysql-client

    # Start MySQL
    systemctl enable mysql
    systemctl start mysql

    # Secure installation
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" << EOF
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF

    # Create Mindset database and user
    MINDSET_DB_PASSWORD=$(generate_password)

    mysql -u root -p"$MYSQL_ROOT_PASSWORD" << EOF
CREATE DATABASE IF NOT EXISTS mindset CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'mindset'@'localhost' IDENTIFIED BY '$MINDSET_DB_PASSWORD';
GRANT ALL PRIVILEGES ON mindset.* TO 'mindset'@'localhost';
FLUSH PRIVILEGES;
EOF

    log "MySQL installed successfully"
}

#####################################################################
# Install Redis
#####################################################################

install_redis() {
    if [[ "$INSTALL_REDIS" != "yes" ]]; then
        return
    fi

    log "Installing Redis..."

    apt-get install -y redis-server

    # Configure Redis
    cat > /etc/redis/redis.conf << 'EOF'
bind 127.0.0.1 ::1
port 6379
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly no
EOF

    systemctl enable redis-server
    systemctl restart redis-server

    log "Redis installed successfully"
}

#####################################################################
# Install Node.js
#####################################################################

install_nodejs() {
    log "Installing Node.js LTS..."

    # Install Node.js 20.x LTS
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs

    # Install global packages
    npm install -g npm@latest

    log "Node.js installed successfully"
}

#####################################################################
# Install Composer
#####################################################################

install_composer() {
    log "Installing Composer..."

    EXPECTED_CHECKSUM="$(php -r 'copy("https://composer.github.io/installer.sig", "php://stdout");')"
    php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
    ACTUAL_CHECKSUM="$(php -r "echo hash_file('sha384', 'composer-setup.php');")"

    if [[ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ]]; then
        rm composer-setup.php
        error "Composer installer checksum mismatch"
    fi

    php composer-setup.php --install-dir=/usr/local/bin --filename=composer
    rm composer-setup.php

    log "Composer installed successfully"
}

#####################################################################
# Install Ollama (Optional)
#####################################################################

install_ollama() {
    if [[ "$INSTALL_OLLAMA" != "yes" ]]; then
        return
    fi

    log "Installing Ollama for local AI..."

    curl -fsSL https://ollama.com/install.sh | sh

    # Enable and start Ollama
    systemctl enable ollama
    systemctl start ollama

    # Pull a lightweight model
    info "Pulling Llama 3.1 8B model (this may take a while)..."
    ollama pull llama3.1:8b &

    log "Ollama installed successfully"
}

#####################################################################
# Install Mindset Platform
#####################################################################

install_mindset() {
    log "Installing Mindset Platform..."

    # Clone repository
    if [[ -d "$MINDSET_PATH/.git" ]]; then
        cd "$MINDSET_PATH"
        git fetch origin
        git checkout "$MINDSET_BRANCH"
        git pull origin "$MINDSET_BRANCH"
    else
        git clone --branch "$MINDSET_BRANCH" "$MINDSET_REPO" "$MINDSET_PATH"
    fi

    cd "$MINDSET_PATH"

    # Create Python virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install Python dependencies
    pip install --upgrade pip
    pip install -r requirements.txt

    # Generate Django secret key
    DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

    # Create .env file
    cat > "$MINDSET_PATH/.env" << EOF
# Mindset Configuration
SECRET_KEY=$DJANGO_SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$HOSTNAME,localhost,127.0.0.1

# Database
DB_NAME=mindset
DB_USER=mindset
DB_PASSWORD=$MINDSET_DB_PASSWORD
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_SSL_REDIRECT=False

# Logging
LOG_LEVEL=WARNING
EOF

    # Run migrations
    python manage.py migrate

    # Collect static files
    python manage.py collectstatic --noinput

    # Create admin user
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '$ADMIN_EMAIL', '$ADMIN_PASSWORD')
    print('Admin user created')
else:
    print('Admin user already exists')
EOF

    # Create systemd service for Gunicorn
    cat > /etc/systemd/system/mindset.service << EOF
[Unit]
Description=Mindset Gunicorn Daemon
After=network.target mysql.service redis.service

[Service]
User=mindset
Group=mindset
WorkingDirectory=$MINDSET_PATH
Environment="PATH=$MINDSET_PATH/venv/bin"
ExecStart=$MINDSET_PATH/venv/bin/gunicorn \\
    --workers 4 \\
    --bind 127.0.0.1:8091 \\
    --access-logfile $LOG_PATH/access.log \\
    --error-logfile $LOG_PATH/error.log \\
    CyberCP.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd service for FastAPI
    cat > /etc/systemd/system/mindset-api.service << EOF
[Unit]
Description=Mindset FastAPI Service
After=network.target mysql.service redis.service

[Service]
User=mindset
Group=mindset
WorkingDirectory=$MINDSET_PATH
Environment="PATH=$MINDSET_PATH/venv/bin"
ExecStart=$MINDSET_PATH/venv/bin/uvicorn \\
    api.main:app \\
    --host 127.0.0.1 \\
    --port 8092 \\
    --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    # Set permissions
    chown -R mindset:mindset "$MINDSET_PATH"

    # Enable and start services
    systemctl daemon-reload
    systemctl enable mindset
    systemctl enable mindset-api
    systemctl start mindset
    systemctl start mindset-api

    log "Mindset Platform installed successfully"
}

#####################################################################
# Configure SSL
#####################################################################

configure_ssl() {
    log "Configuring SSL..."

    # Install Certbot
    apt-get install -y certbot

    # Generate self-signed certificate for initial setup
    mkdir -p /etc/ssl/mindset

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/mindset/server.key \
        -out /etc/ssl/mindset/server.crt \
        -subj "/C=US/ST=State/L=City/O=Mindset/CN=$HOSTNAME"

    # Configure OLS for HTTPS
    cat > /usr/local/lsws/conf/vhosts/mindset/vhconf.conf << 'EOF'
docRoot                   $VH_ROOT/public
enableGzip                1

index  {
  useServer               0
  indexFiles              index.php, index.html
}

rewrite  {
  enable                  1
  autoLoadHtaccess        1
}

context / {
  type                    proxy
  handler                 127.0.0.1:8091
  addDefaultCharset       off
}

context /api {
  type                    proxy
  handler                 127.0.0.1:8092
  addDefaultCharset       off
}
EOF

    systemctl restart lsws

    log "SSL configured successfully"
}

#####################################################################
# Save Credentials
#####################################################################

save_credentials() {
    log "Saving credentials..."

    cat > /root/.mindset-credentials << EOF
#####################################################################
#                   MINDSET CREDENTIALS                              #
#             KEEP THIS FILE SECURE - DELETE AFTER NOTING            #
#####################################################################

Installation Date: $(date)
Server Hostname: $HOSTNAME

=== MINDSET ADMIN ===
URL:      https://$HOSTNAME:8090
Username: admin
Password: $ADMIN_PASSWORD
Email:    $ADMIN_EMAIL

=== MYSQL ===
Root Password: $MYSQL_ROOT_PASSWORD
Mindset DB:    mindset
Mindset User:  mindset
Mindset Pass:  $MINDSET_DB_PASSWORD

=== OPENLITESPEED ===
Admin URL:  https://$HOSTNAME:7080
Username:   admin
Password:   $OLS_ADMIN_PASSWORD

=== REDIS ===
Host: 127.0.0.1
Port: 6379

EOF

    if [[ "$INSTALL_OLLAMA" == "yes" ]]; then
        cat >> /root/.mindset-credentials << EOF
=== OLLAMA AI ===
Host: 127.0.0.1
Port: 11434
Model: llama3.1:8b

EOF
    fi

    chmod 600 /root/.mindset-credentials

    log "Credentials saved to /root/.mindset-credentials"
}

#####################################################################
# Final Steps
#####################################################################

final_steps() {
    log "Running final steps..."

    # Health check
    sleep 5

    if systemctl is-active --quiet mindset; then
        info "Mindset service is running"
    else
        warn "Mindset service may not be running properly. Check: systemctl status mindset"
    fi

    if systemctl is-active --quiet lsws; then
        info "OpenLiteSpeed is running"
    else
        warn "OpenLiteSpeed may not be running properly. Check: systemctl status lsws"
    fi

    if systemctl is-active --quiet mysql; then
        info "MySQL is running"
    else
        warn "MySQL may not be running properly. Check: systemctl status mysql"
    fi

    if [[ "$INSTALL_REDIS" == "yes" ]] && systemctl is-active --quiet redis-server; then
        info "Redis is running"
    fi

    # Print completion message
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}           MINDSET INSTALLATION COMPLETED SUCCESSFULLY!         ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Access Mindset:${NC}"
    echo -e "  URL:      ${GREEN}https://$HOSTNAME:8090${NC}"
    echo -e "  Username: ${GREEN}admin${NC}"
    echo -e "  Password: ${GREEN}[see /root/.mindset-credentials]${NC}"
    echo ""
    echo -e "  ${CYAN}OpenLiteSpeed Admin:${NC}"
    echo -e "  URL:      ${GREEN}https://$HOSTNAME:7080${NC}"
    echo ""
    echo -e "  ${YELLOW}IMPORTANT:${NC}"
    echo -e "  1. Save your credentials from ${GREEN}/root/.mindset-credentials${NC}"
    echo -e "  2. Configure DNS to point your domain to this server"
    echo -e "  3. Set up SSL certificate: ${GREEN}certbot --webroot -w /var/www/html -d $HOSTNAME${NC}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

#####################################################################
# Main Installation Flow
#####################################################################

main() {
    print_banner

    check_root

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unattended)
                UNATTENDED=true
                shift
                ;;
            --admin-email=*)
                ADMIN_EMAIL="${1#*=}"
                shift
                ;;
            --admin-password=*)
                ADMIN_PASSWORD="${1#*=}"
                shift
                ;;
            --hostname=*)
                HOSTNAME="${1#*=}"
                shift
                ;;
            --with-mail)
                INSTALL_MAIL="yes"
                shift
                ;;
            --with-dns)
                INSTALL_DNS="yes"
                shift
                ;;
            --with-ollama)
                INSTALL_OLLAMA="yes"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --unattended           Run in unattended mode"
                echo "  --admin-email=EMAIL    Set admin email"
                echo "  --admin-password=PASS  Set admin password"
                echo "  --hostname=HOST        Set server hostname"
                echo "  --with-mail            Install email server"
                echo "  --with-dns             Install DNS server"
                echo "  --with-ollama          Install Ollama AI"
                echo ""
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    preflight_checks

    if [[ "$UNATTENDED" != "true" ]]; then
        interactive_setup
    else
        # Validate required parameters for unattended mode
        if [[ -z "$ADMIN_EMAIL" || -z "$ADMIN_PASSWORD" ]]; then
            error "Unattended mode requires --admin-email and --admin-password"
        fi
        HOSTNAME=${HOSTNAME:-$(hostname -f)}
        MYSQL_ROOT_PASSWORD=$(generate_password)
    fi

    # Run installation steps
    prepare_system
    harden_security
    install_openlitespeed
    install_mysql
    install_redis
    install_nodejs
    install_composer
    install_ollama
    install_mindset
    configure_ssl
    save_credentials
    final_steps
}

# Run main function
main "$@"
