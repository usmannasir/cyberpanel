#!/usr/bin/env bash
# CyberPanel upgrade – MariaDB backup, optional UTF-8 migration, CentOS 7 MySQL upgrade.
# Sourced by cyberpanel_upgrade.sh.

Pre_Upgrade_CentOS7_MySQL() {
  if [[ "$MySQL_Version" = "10.1" ]]; then
    cp /etc/my.cnf /etc/my.cnf.bak
    mkdir /etc/cnfbackup
    cp -R /etc/my.cnf.d/ /etc/cnfbackup/
    yum remove MariaDB-server MariaDB-client galera -y
    yum --enablerepo=mariadb -y install MariaDB-server MariaDB-client galera
    cp -f /etc/my.cnf.bak /etc/my.cnf
    rm -rf /etc/my.cnf.d/
    mv /etc/cnfbackup/my.cnf.d /etc/
    systemctl enable mariadb 2>/dev/null || systemctl enable mysql
    systemctl start mariadb 2>/dev/null || systemctl start mysql
    mariadb-upgrade -uroot -p"$MySQL_Password" 2>/dev/null || mysql_upgrade -uroot -p"$MySQL_Password"
  fi
  mariadb -uroot -p"$MySQL_Password" -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '$MySQL_Password';flush privileges" 2>/dev/null || mysql -uroot -p"$MySQL_Password" -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '$MySQL_Password';flush privileges"
  Ensure_MariaDB_Client_No_SSL
}

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
  Backup_MariaDB_Before_Upgrade
}

Backup_MariaDB_Before_Upgrade() {
  local pass="" backup_dir="/root/cyberpanel_mariadb_backups" backup_file=""
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
