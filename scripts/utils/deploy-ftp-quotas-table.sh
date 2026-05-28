#!/bin/bash
# Create the missing ftp_quotas table in the CyberPanel database.
# Fixes: (1146, "Table 'cyberpanel.ftp_quotas' doesn't exist") on /ftp/quotaManagement
#
# Usage:
#   sudo bash /home/cyberpanel-repo/deploy-ftp-quotas-table.sh
#   sudo bash deploy-ftp-quotas-table.sh [REPO_DIR] [CP_DIR]

set -e

log() { echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*"; }
err() { log "ERROR: $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

if [[ -n "$1" && -f "$1/sql/create_ftp_quotas.sql" ]]; then
    REPO_DIR="$1"
    shift
elif [[ -f "$REPO_ROOT/sql/create_ftp_quotas.sql" ]]; then
    REPO_DIR="$REPO_ROOT"
elif [[ -f "/home/cyberpanel-repo/sql/create_ftp_quotas.sql" ]]; then
    REPO_DIR="/home/cyberpanel-repo"
else
    err "sql/create_ftp_quotas.sql not found."
    exit 1
fi

CP_DIR="${1:-/usr/local/CyberCP}"
SQL_FILE="$REPO_DIR/sql/create_ftp_quotas.sql"

if [[ ! -d "$CP_DIR" ]]; then
    err "CyberPanel directory not found: $CP_DIR"
    exit 1
fi

log "REPO_DIR=$REPO_DIR"
log "CP_DIR=$CP_DIR"

mkdir -p "$CP_DIR/sql"
cp -f "$SQL_FILE" "$CP_DIR/sql/create_ftp_quotas.sql"
log "Copied create_ftp_quotas.sql to $CP_DIR/sql/"

# Run SQL using Django DB connection (no password on command line)
log "Creating ftp_quotas table..."
export CP_DIR
python3 << 'PYEOF'
import os
import sys

cp_dir = os.environ.get('CP_DIR', '/usr/local/CyberCP')
sys.path.insert(0, cp_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django
django.setup()

from django.db import connection

with open(os.path.join(cp_dir, 'sql', 'create_ftp_quotas.sql'), 'r') as f:
    sql = f.read()

with connection.cursor() as cursor:
    cursor.execute(sql)
    print('Executed CREATE TABLE IF NOT EXISTS ftp_quotas.')
PYEOF

log "Done. Reload https://207.180.193.210:2087/ftp/quotaManagement"
