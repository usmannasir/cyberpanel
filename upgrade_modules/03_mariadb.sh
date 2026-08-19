#!/usr/bin/env bash
# CyberPanel upgrade – MariaDB backup, optional UTF-8 migration.
# Sourced by cyberpanel_upgrade.sh.

Maybe_Backup_MariaDB_Before_Upgrade() {
  if [[ "$Backup_DB_Before_Upgrade" = "no" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped (--no-backup-db)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 0
  fi
  if [[ "$Backup_DB_Before_Upgrade" = "" ]]; then
    echo -e "\nDo you want to backup all databases before MariaDB upgrade? (may take a while) [y/N]: "
    read -r -t 60 Tmp_Backup_Choice 2>/dev/null || Tmp_Backup_Choice=""
    if [[ "$Tmp_Backup_Choice" =~ ^[yY] ]] || [[ "$Tmp_Backup_Choice" =~ ^[yY][eE][sS] ]]; then
      Backup_DB_Before_Upgrade="yes"
    else
      Backup_DB_Before_Upgrade="no"
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped (user chose no or timeout)." | tee -a /var/log/cyberpanel_upgrade_debug.log
      return 0
    fi
  fi
  Backup_MariaDB_Datadir_Tarball
  Backup_MariaDB_Before_Upgrade
}

Backup_MariaDB_Before_Upgrade() {
  local pass="" backup_dir="/root/cyberpanel_mariadb_backups" backup_file=""
  local std_backup_base="/root/db-upgrade-backups"
  local std_backup_dir="${std_backup_base}/$(date +%Y-%m-%d_%H%M%S)"
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting MariaDB pre-upgrade backup... (this may take a few minutes)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  [[ -f /etc/cyberpanel/mysqlPassword ]] || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped (no password file)." | tee -a /var/log/cyberpanel_upgrade_debug.log; return 0; }
  if grep -q '"mysqlpassword"' /etc/cyberpanel/mysqlPassword 2>/dev/null; then
    pass=$(python3 -c "import json; print(json.load(open('/etc/cyberpanel/mysqlPassword')).get('mysqlpassword',''))" 2>/dev/null)
  else
    pass=$(head -1 /etc/cyberpanel/mysqlPassword 2>/dev/null | tr -d '\r\n')
  fi
  [[ -z "$pass" ]] && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Could not read MariaDB password, skipping pre-upgrade backup." | tee -a /var/log/cyberpanel_upgrade_debug.log && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped." | tee -a /var/log/cyberpanel_upgrade_debug.log && return 0
  mkdir -p "$backup_dir"
  backup_file="${backup_dir}/mariadb_backup_before_upgrade_$(date +%Y%m%d_%H%M%S).sql.gz"
  if mariadb --skip-ssl -u root -p"$pass" -e "SELECT 1" 2>/dev/null | grep -q 1; then
    (mariadb-dump --skip-ssl -u root -p"$pass" --all-databases --single-transaction --routines --triggers --events 2>/dev/null || mysqldump --skip-ssl -u root -p"$pass" --all-databases --single-transaction --routines --triggers --events 2>/dev/null) | gzip > "$backup_file" 2>/dev/null
    if [[ -s "$backup_file" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB backup created: $backup_file" | tee -a /var/log/cyberpanel_upgrade_debug.log
      mkdir -p "$std_backup_dir"
      cp -a "$backup_file" "$std_backup_dir/all_databases.sql.gz" 2>/dev/null && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB backup also saved to: $std_backup_dir/all_databases.sql.gz" | tee -a /var/log/cyberpanel_upgrade_debug.log || true
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: done." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: MariaDB backup file empty or failed." | tee -a /var/log/cyberpanel_upgrade_debug.log
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped (dump failed)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Could not connect to MariaDB for backup (skip-ssl). Skipping backup." | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB pre-upgrade backup: skipped (no connection)." | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
}

Migrate_MariaDB_To_UTF8() {
  local pass="" dbs="" db="" t=""
  [[ -f /etc/cyberpanel/mysqlPassword ]] || return 0
  if grep -q '"mysqlpassword"' /etc/cyberpanel/mysqlPassword 2>/dev/null; then
    pass=$(python3 -c "import json; print(json.load(open('/etc/cyberpanel/mysqlPassword')).get('mysqlpassword',''))" 2>/dev/null)
  else
    pass=$(head -1 /etc/cyberpanel/mysqlPassword 2>/dev/null | tr -d '\r\n')
  fi
  [[ -z "$pass" ]] && return 0
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Migrating MariaDB to UTF-8 (utf8mb4)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  mariadb --skip-ssl -u root -p"$pass" -e "SET GLOBAL character_set_server = 'utf8mb4'; SET GLOBAL collation_server = 'utf8mb4_unicode_ci';" 2>/dev/null || true
  dbs=$(mariadb --skip-ssl -u root -p"$pass" -sN -e "SHOW DATABASES;" 2>/dev/null) || true
  for db in $dbs; do
    [[ "$db" = "information_schema" ]] || [[ "$db" = "performance_schema" ]] || [[ "$db" = "sys" ]] || [[ "$db" = "mysql" ]] && continue
    mariadb --skip-ssl -u root -p"$pass" -e "ALTER DATABASE \`$db\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
    for t in $(mariadb --skip-ssl -u root -p"$pass" -sN -e "SHOW TABLES FROM \`$db\`;" 2>/dev/null); do
      mariadb --skip-ssl -u root -p"$pass" "$db" -e "ALTER TABLE \`$t\` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
    done
  done
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB UTF-8 (utf8mb4) migration completed." | tee -a /var/log/cyberpanel_upgrade_debug.log
}

# Ensure MariaDB client connects without SSL (avoids ERROR 2026 when server has have_ssl=DISABLED).
# Call after any MariaDB install/upgrade so install and upgrade paths both get the fix.
Ensure_MariaDB_Client_No_SSL() {
  mkdir -p /etc/my.cnf.d
  printf "[client]\nssl=0\nskip-ssl\n" > /etc/my.cnf.d/cyberpanel-client.cnf 2>/dev/null || true
  if [[ -f /etc/my.cnf ]] && ! grep -q '^\[client\]' /etc/my.cnf 2>/dev/null; then
    echo -e "\n[client]\nssl=0\nskip-ssl" >> /etc/my.cnf
  fi
  if [[ -d /etc/mysql/mariadb.conf.d ]]; then
    printf "[client]\nssl=0\nskip-ssl\n" > /etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf 2>/dev/null || true
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB client no-SSL config ensured (cyberpanel-client.cnf, optional my.cnf [client])." | tee -a /var/log/cyberpanel_upgrade_debug.log
}

# Echo MariaDB root password from /etc/cyberpanel/mysqlPassword (plain or JSON). Empty if unreadable.
CyberPanel_Read_Mysql_Root_Password() {
  local pass=""
  [[ -f /etc/cyberpanel/mysqlPassword ]] || { echo ""; return 1; }
  if grep -q '"mysqlpassword"' /etc/cyberpanel/mysqlPassword 2>/dev/null; then
    pass=$(python3 -c "import json; print(json.load(open('/etc/cyberpanel/mysqlPassword')).get('mysqlpassword',''))" 2>/dev/null)
  else
    pass=$(head -1 /etc/cyberpanel/mysqlPassword 2>/dev/null | tr -d '\r\n')
  fi
  printf '%s' "$pass"
}

# Tarball /var/lib/mysql when backups are enabled (same flag as SQL dump). Skipped with --no-backup-db.
Backup_MariaDB_Datadir_Tarball() {
  if [[ "$Backup_DB_Before_Upgrade" = "no" ]]; then
    return 0
  fi
  local DEST="/root/cyberpanel_mariadb_backups"
  local TS OUT
  mkdir -p "$DEST"
  TS=$(date +%Y%m%d-%H%M%S)
  OUT="${DEST}/var-lib-mysql-pre-${MARIADB_VER:-unknown}-${TS}.tar.gz"
  if [[ ! -d /var/lib/mysql ]] || [[ -z "$(ls -A /var/lib/mysql 2>/dev/null)" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB datadir tarball: skipped (empty or missing /var/lib/mysql)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 0
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backing up /var/lib/mysql to ${OUT}" | tee -a /var/log/cyberpanel_upgrade_debug.log
  if tar --warning=no-file-changed -czf "$OUT" -C /var/lib mysql 2>/dev/null; then
    sha256sum "$OUT" | tee "${OUT}.sha256" >/dev/null 2>&1 || true
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Datadir backup OK ($(du -h "$OUT" 2>/dev/null | awk '{print $1}'))" | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Datadir tarball failed." | tee -a /var/log/cyberpanel_upgrade_debug.log
    exit 1
  fi
}

CyberPanel_Disable_Dnf_Mariadb_Module() {
  if ! command -v dnf >/dev/null 2>&1; then
    return 0
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Disabling AppStream mariadb DNF module (allows MariaDB.org repo packages)." | tee -a /var/log/cyberpanel_upgrade_debug.log
  dnf module reset -y mariadb 2>/dev/null || true
  if ! dnf module disable -y mariadb 2>/dev/null; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: dnf module disable mariadb failed; MariaDB.repo uses module_hotfixes=1 as fallback." | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
}

# Write MariaDB YUM/DNF repo for EL (mirror.mariadb.org). Args: MARIADB_VER_REPO (e.g. 12.3), rhel path (rhel8-amd64|rhel9-amd64).
CyberPanel_Write_MariaDB_Yum_Repo_EL() {
  local ver_repo="${1:?}"
  local rhel_arch="${2:?}"
  cat << EOF > /etc/yum.repos.d/MariaDB.repo
# MariaDB ${ver_repo} repository - CyberPanel upgrade
[mariadb]
name = MariaDB ${ver_repo}
baseurl = https://mirror.mariadb.org/yum/${ver_repo}/${rhel_arch}
gpgkey=https://supplychain.mariadb.com/MariaDB-Server-GPG-KEY
       https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
module_hotfixes=1
EOF
  if [[ "$Server_Country" = "CN" ]]; then
    sed -i 's|http://yum.mariadb.org|https://cyberpanel.sh/yum.mariadb.org|g' /etc/yum.repos.d/MariaDB.repo 2>/dev/null || true
    sed -i 's|https://yum.mariadb.org/RPM-GPG-KEY-MariaDB|https://cyberpanel.sh/yum.mariadb.org/RPM-GPG-KEY-MariaDB|g' /etc/yum.repos.d/MariaDB.repo 2>/dev/null || true
    sed -i 's|https://mirror.mariadb.org/yum/|https://cyberpanel.sh/mirror.mariadb.org/yum/|g' /etc/yum.repos.d/MariaDB.repo 2>/dev/null || true
  fi
  rpm --import https://supplychain.mariadb.com/MariaDB-Server-GPG-KEY 2>/dev/null || \
    rpm --import https://yum.mariadb.org/RPM-GPG-KEY-MariaDB 2>/dev/null || \
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: Could not import MariaDB GPG key." | tee -a /var/log/cyberpanel_upgrade_debug.log
}

CyberPanel_Remove_AppStream_Mariadb_Packages_EL() {
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing AppStream MariaDB 10.x packages where present (data dir untouched)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  systemctl stop mariadb 2>/dev/null || true
  local _i
  for ((_i = 1; _i <= 30; _i++)); do
    [[ ! -S /var/lib/mysql/mysql.sock ]] && break
    sleep 1
  done
  dnf remove -y \
    mariadb mariadb-server mariadb-server-utils \
    mariadb-backup mariadb-common mariadb-errmsg \
    mariadb-gssapi-server mariadb-devel \
    mariadb-connector-c mariadb-connector-c-config mariadb-connector-c-devel \
    2>/dev/null || true
}

CyberPanel_Dnf_Install_Full_MariaDB_From_Repo() {
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing MariaDB packages from MariaDB.org repo (canonical names)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  if ! dnf install -y --enablerepo=mariadb \
    MariaDB-server MariaDB-client MariaDB-shared \
    MariaDB-backup MariaDB-common MariaDB-devel; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: dnf install MariaDB-* failed." | tee -a /var/log/cyberpanel_upgrade_debug.log
    exit 1
  fi
  if ! rpm -q MariaDB-server >/dev/null 2>&1; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: MariaDB-server RPM not present after install." | tee -a /var/log/cyberpanel_upgrade_debug.log
    exit 1
  fi
}

CyberPanel_Ensure_Local_Mariadb_Client_Cnf() {
  mkdir -p /etc/my.cnf.d
  printf "[client]\nssl=0\nskip-ssl\n" > /etc/my.cnf.d/cyberpanel-client.cnf 2>/dev/null || true
  if [[ -f /etc/my.cnf ]] && ! grep -q '^\[client\]' /etc/my.cnf 2>/dev/null; then
    echo -e "\n[client]\nssl=0\nskip-ssl" >> /etc/my.cnf
  fi
}

# Start mariadb, wait for socket, run mariadb-upgrade with root password when available.
CyberPanel_Post_Install_Mariadb_Upgrade_Tool() {
  local pw=""
  systemctl enable mariadb 2>/dev/null || true
  systemctl start mariadb 2>/dev/null || systemctl restart mariadb 2>/dev/null || true
  local _i
  for ((_i = 1; _i <= 30; _i++)); do
    [[ -S /var/lib/mysql/mysql.sock ]] && break
    sleep 1
  done
  pw=$(CyberPanel_Read_Mysql_Root_Password || true)
  if [[ -n "$pw" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running mariadb-upgrade for system tables..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    if ! mariadb-upgrade -u root -p"$pw" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: mariadb-upgrade reported issues (review log)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: No root password file; running mariadb-upgrade as root socket auth if possible." | tee -a /var/log/cyberpanel_upgrade_debug.log
    mariadb-upgrade --force -u root 2>/dev/null || true
  fi
  if ! systemctl is-active --quiet mariadb 2>/dev/null; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: mariadb service not active after upgrade steps." | tee -a /var/log/cyberpanel_upgrade_debug.log
    exit 1
  fi
}

CyberPanel_Print_MariaDB_Upgrade_Banner() {
  local cur="(could not detect)"
  command -v mariadb >/dev/null 2>&1 && cur=$(mariadb --version 2>/dev/null | head -1 || echo "(unknown)")
  echo "+--------------------------------------------------------------+"
  echo "|  CyberPanel MariaDB upgrade                                  |"
  echo "|  Target version line: ${MARIADB_VER:-} (repo ${MARIADB_VER_REPO:-})"
  echo "|  Current client: ${cur}"
  echo "|  - /var/lib/mysql may be backed up when backups enabled      |"
  echo "|    under /root/cyberpanel_mariadb_backups/                   |"
  echo "|  - AppStream mariadb DNF module will be disabled             |"
  echo "|  - mariadb-upgrade runs after the new server starts          |"
  echo "|  Estimated downtime for MariaDB: 60-120s                    |"
  echo "+--------------------------------------------------------------+"
}

# AlmaLinux/RHEL 10: AppStream MariaDB only (MariaDB.org el9 RPMs need RHEL 9 boost).
CyberPanel_EL10_AppStream_MariaDB_Install() {
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/RHEL 10: using AppStream MariaDB (MariaDB.org el9 RPMs are incompatible)." | tee -a /var/log/cyberpanel_upgrade_debug.log
  Maybe_Backup_MariaDB_Before_Upgrade
  CyberPanel_Print_MariaDB_Upgrade_Banner | tee -a /var/log/cyberpanel_upgrade_debug.log

  rm -f /etc/yum.repos.d/MariaDB.repo /etc/yum.repos.d/mariadb.repo 2>/dev/null || true

  dnf install -y mariadb-server mariadb mariadb-backup mariadb-devel 2>/dev/null || \
    dnf install -y --nobest mariadb-server mariadb mariadb-backup mariadb-devel

  CyberPanel_Ensure_Local_Mariadb_Client_Cnf
  CyberPanel_Post_Install_Mariadb_Upgrade_Tool

  if [[ "$Migrate_MariaDB_To_UTF8_Requested" = "yes" ]]; then
    Migrate_MariaDB_To_UTF8
  fi
}

# EL8/EL9: full MariaDB upgrade path using MariaDB.org repo (called from Pre_Upgrade_Setup_Repository).
# EL10 uses CyberPanel_EL10_AppStream_MariaDB_Install instead.
CyberPanel_EL89_Apply_MariaDB_Repository_And_Packages() {
  local MARIADB_REPO=""
  if [[ "$Server_OS_Version" = "10" ]]; then
    CyberPanel_EL10_AppStream_MariaDB_Install
    return 0
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Configuring MariaDB $MARIADB_VER_REPO repository and upgrading MariaDB..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  Maybe_Backup_MariaDB_Before_Upgrade
  CyberPanel_Print_MariaDB_Upgrade_Banner | tee -a /var/log/cyberpanel_upgrade_debug.log

  if [[ "$Server_OS_Version" = "9" ]]; then
    MARIADB_REPO="rhel9-amd64"
  else
    MARIADB_REPO="rhel8-amd64"
  fi

  CyberPanel_Disable_Dnf_Mariadb_Module

  for f in /etc/yum.repos.d/mariadb.repo /etc/yum.repos.d/MariaDB.repo.rpmsave; do
    if [[ -f "$f" ]] && grep -q '10\.11\|10.6\|10.5' "$f" 2>/dev/null && [[ "$MARIADB_VER_REPO" != "10.11" ]]; then
      mv -f "$f" "${f}.bak.cyberpanel" 2>/dev/null && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backed up old repo $f" | tee -a /var/log/cyberpanel_upgrade_debug.log || true
    fi
  done

  CyberPanel_Write_MariaDB_Yum_Repo_EL "$MARIADB_VER_REPO" "$MARIADB_REPO"
  dnf clean metadata --disablerepo='*' --enablerepo=mariadb 2>/dev/null || true
  dnf makecache --refresh -y 2>/dev/null || true

  local MARIADB_OLD_10 MARIADB_OLD_11 STILL_11

  MARIADB_OLD_10=$(rpm -qa 'MariaDB-server-10*' 2>/dev/null | head -1)
  [[ -z "$MARIADB_OLD_10" ]] && MARIADB_OLD_10=$(rpm -qa 2>/dev/null | grep -E '^MariaDB-server-10\.' | head -1)
  MARIADB_OLD_11=$(rpm -qa 'MariaDB-server-11*' 2>/dev/null | head -1)
  [[ -z "$MARIADB_OLD_11" ]] && MARIADB_OLD_11=$(rpm -qa 'MariaDB-server*' 2>/dev/null | grep -E 'MariaDB-server-11\.' | head -1)

  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB detected: MARIADB_OLD_10=${MARIADB_OLD_10:-none} MARIADB_OLD_11=${MARIADB_OLD_11:-none} target=${MARIADB_VER_REPO}" | tee -a /var/log/cyberpanel_upgrade_debug.log

  if [[ -n "$MARIADB_OLD_10" ]] && { [[ "$MARIADB_VER_REPO" =~ ^11\. ]] || [[ "$MARIADB_VER_REPO" =~ ^12\. ]]; }; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB 10.x to ${MARIADB_VER_REPO}: remove old server RPM, install from MariaDB.org..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    CyberPanel_Remove_AppStream_Mariadb_Packages_EL
    [[ -f /etc/my.cnf ]] && cp -a /etc/my.cnf /etc/my.cnf.bak.cyberpanel 2>/dev/null || true
    [[ -d /etc/my.cnf.d ]] && cp -a /etc/my.cnf.d /etc/my.cnf.d.bak.cyberpanel 2>/dev/null || true
    rpm -e "$MARIADB_OLD_10" --nodeps 2>/dev/null || true
    CyberPanel_Dnf_Install_Full_MariaDB_From_Repo
    CyberPanel_Ensure_Local_Mariadb_Client_Cnf
    CyberPanel_Post_Install_Mariadb_Upgrade_Tool
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB manual upgrade from 10.x completed." | tee -a /var/log/cyberpanel_upgrade_debug.log

  elif [[ -n "$MARIADB_OLD_11" ]] && [[ "$MARIADB_VER_REPO" =~ ^12\. ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB 11.x to ${MARIADB_VER_REPO}: remove old server RPM, install from MariaDB.org..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    systemctl stop mariadb 2>/dev/null || true
    sleep 2
    [[ -f /etc/my.cnf ]] && cp -a /etc/my.cnf /etc/my.cnf.bak.cyberpanel 2>/dev/null || true
    [[ -d /etc/my.cnf.d ]] && cp -a /etc/my.cnf.d /etc/my.cnf.d.bak.cyberpanel 2>/dev/null || true
    rpm -e "$MARIADB_OLD_11" --nodeps 2>/dev/null || true
    CyberPanel_Dnf_Install_Full_MariaDB_From_Repo
    CyberPanel_Ensure_Local_Mariadb_Client_Cnf
    CyberPanel_Post_Install_Mariadb_Upgrade_Tool
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB 11 to 12 upgrade completed." | tee -a /var/log/cyberpanel_upgrade_debug.log

  else
    CyberPanel_Dnf_Install_Full_MariaDB_From_Repo
    dnf upgrade -y --enablerepo=mariadb \
      MariaDB-server MariaDB-client MariaDB-shared MariaDB-backup MariaDB-common MariaDB-devel 2>/dev/null || true
    systemctl restart mariadb 2>/dev/null || true
    CyberPanel_Ensure_Local_Mariadb_Client_Cnf
    CyberPanel_Post_Install_Mariadb_Upgrade_Tool

    if [[ "$MARIADB_VER_REPO" =~ ^12\. ]]; then
      STILL_11=$(rpm -qa 'MariaDB-server-11*' 2>/dev/null | head -1)
      [[ -z "$STILL_11" ]] && STILL_11=$(rpm -qa 'MariaDB-server*' 2>/dev/null | grep -E 'MariaDB-server-11\.' | head -1)
      if [[ -n "$STILL_11" ]]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB still 11.x; forcing manual 11 to 12 upgrade..." | tee -a /var/log/cyberpanel_upgrade_debug.log
        systemctl stop mariadb 2>/dev/null || true
        sleep 2
        rpm -e "$STILL_11" --nodeps 2>/dev/null || true
        CyberPanel_Dnf_Install_Full_MariaDB_From_Repo
        CyberPanel_Ensure_Local_Mariadb_Client_Cnf
        CyberPanel_Post_Install_Mariadb_Upgrade_Tool
      fi
    fi
  fi

  mkdir -p /etc/my.cnf.d
  printf "[client]\nssl=0\nskip-ssl\n" > /etc/my.cnf.d/cyberpanel-client.cnf 2>/dev/null || true
  if [[ -f /etc/my.cnf ]] && ! grep -q '^\[client\]' /etc/my.cnf 2>/dev/null; then
    echo -e "\n[client]\nssl=0\nskip-ssl" >> /etc/my.cnf
  fi
  if [[ "$Migrate_MariaDB_To_UTF8_Requested" = "yes" ]] && { [[ "$MARIADB_VER_REPO" =~ ^11\. ]] || [[ "$MARIADB_VER_REPO" =~ ^12\. ]]; }; then
    Migrate_MariaDB_To_UTF8
  fi
}
