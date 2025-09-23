#!/bin/bash

# Enable FTP User Quota Feature
# This script applies the quota configuration and restarts Pure-FTPd

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/cyberpanel_ftp_quota.log
}

log_message "${BLUE}Starting FTP Quota Feature Setup...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_message "${RED}Please run as root${NC}"
    exit 1
fi

# Backup existing configurations
log_message "${YELLOW}Backing up existing Pure-FTPd configurations...${NC}"

if [ -f /etc/pure-ftpd/pure-ftpd.conf ]; then
    cp /etc/pure-ftpd/pure-ftpd.conf /etc/pure-ftpd/pure-ftpd.conf.backup.$(date +%Y%m%d_%H%M%S)
    log_message "${GREEN}Backed up pure-ftpd.conf${NC}"
fi

if [ -f /etc/pure-ftpd/pureftpd-mysql.conf ]; then
    cp /etc/pure-ftpd/pureftpd-mysql.conf /etc/pure-ftpd/pureftpd-mysql.conf.backup.$(date +%Y%m%d_%H%M%S)
    log_message "${GREEN}Backed up pureftpd-mysql.conf${NC}"
fi

# Apply new configurations
log_message "${YELLOW}Applying FTP quota configurations...${NC}"

# Copy the updated configurations
if [ -f /usr/local/CyberCP/install/pure-ftpd/pure-ftpd.conf ]; then
    cp /usr/local/CyberCP/install/pure-ftpd/pure-ftpd.conf /etc/pure-ftpd/pure-ftpd.conf
    log_message "${GREEN}Updated pure-ftpd.conf${NC}"
fi

if [ -f /usr/local/CyberCP/install/pure-ftpd/pureftpd-mysql.conf ]; then
    cp /usr/local/CyberCP/install/pure-ftpd/pureftpd-mysql.conf /etc/pure-ftpd/pureftpd-mysql.conf
    log_message "${GREEN}Updated pureftpd-mysql.conf${NC}"
fi

# Check if Pure-FTPd is running
if systemctl is-active --quiet pure-ftpd; then
    log_message "${YELLOW}Restarting Pure-FTPd service...${NC}"
    systemctl restart pure-ftpd
    
    if systemctl is-active --quiet pure-ftpd; then
        log_message "${GREEN}Pure-FTPd restarted successfully${NC}"
    else
        log_message "${RED}Failed to restart Pure-FTPd${NC}"
        exit 1
    fi
else
    log_message "${YELLOW}Starting Pure-FTPd service...${NC}"
    systemctl start pure-ftpd
    
    if systemctl is-active --quiet pure-ftpd; then
        log_message "${GREEN}Pure-FTPd started successfully${NC}"
    else
        log_message "${RED}Failed to start Pure-FTPd${NC}"
        exit 1
    fi
fi

# Verify quota enforcement is working
log_message "${YELLOW}Verifying quota enforcement...${NC}"

# Check if quota queries are in the configuration
if grep -q "MYSQLGetQTAFS" /etc/pure-ftpd/pureftpd-mysql.conf; then
    log_message "${GREEN}Quota queries found in MySQL configuration${NC}"
else
    log_message "${RED}Quota queries not found in MySQL configuration${NC}"
    exit 1
fi

if grep -q "Quota.*yes" /etc/pure-ftpd/pure-ftpd.conf; then
    log_message "${GREEN}Quota enforcement enabled in Pure-FTPd configuration${NC}"
else
    log_message "${RED}Quota enforcement not enabled in Pure-FTPd configuration${NC}"
    exit 1
fi

# Test database connection
log_message "${YELLOW}Testing database connection...${NC}"

# Get database credentials from configuration
MYSQL_USER=$(grep "MYSQLUser" /etc/pure-ftpd/pureftpd-mysql.conf | cut -d' ' -f2)
MYSQL_PASS=$(grep "MYSQLPassword" /etc/pure-ftpd/pureftpd-mysql.conf | cut -d' ' -f2)
MYSQL_DB=$(grep "MYSQLDatabase" /etc/pure-ftpd/pureftpd-mysql.conf | cut -d' ' -f2)

if mysql -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "USE $MYSQL_DB; SELECT COUNT(*) FROM users;" >/dev/null 2>&1; then
    log_message "${GREEN}Database connection successful${NC}"
else
    log_message "${RED}Database connection failed${NC}"
    exit 1
fi

log_message "${GREEN}FTP User Quota feature has been successfully enabled!${NC}"
log_message "${BLUE}Features enabled:${NC}"
log_message "  - Individual FTP user quotas"
log_message "  - Custom quota sizes per user"
log_message "  - Package default quota fallback"
log_message "  - Real-time quota enforcement by Pure-FTPd"
log_message "  - Web interface for quota management"

log_message "${YELLOW}Note: Existing FTP users will need to have their quotas updated through the web interface to take effect.${NC}"

exit 0
