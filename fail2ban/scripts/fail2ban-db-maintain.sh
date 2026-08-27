#!/usr/bin/env bash
# fail2ban SQLite maintain: integrity check, repair, and install-time hardening.
# AlmaLinux 8/9/10 + CyberPanel. Safe for cron/systemd and fresh installs.
#
# Usage:
#   fail2ban-db-maintain.sh check
#   fail2ban-db-maintain.sh repair
#   fail2ban-db-maintain.sh harden
#   fail2ban-db-maintain.sh install-hardening
#   fail2ban-db-maintain.sh all
#
set -euo pipefail

DB="${FAIL2BAN_DB:-/var/lib/fail2ban/fail2ban.sqlite3}"
BAK_DIR="${FAIL2BAN_DB_BACKUP_DIR:-/var/lib/fail2ban/backups}"
LOG_TAG="fail2ban-db-maintain"
F2B_LOCAL="/etc/fail2ban/fail2ban.local"
DROPIN_DIR="/etc/systemd/system/fail2ban.service.d"
TIMER_UNIT="fail2ban-db-maintain.timer"
SERVICE_UNIT="fail2ban-db-maintain.service"

log() {
  local msg="$1"
  echo "[$(date '+%d/%m/%Y %H:%M:%S')] $msg"
  logger -t "$LOG_TAG" -- "$msg" 2>/dev/null || true
}

die() {
  log "ERROR: $1"
  exit 1
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Run as root"
  fi
}

ensure_dirs() {
  mkdir -p /var/lib/fail2ban "$BAK_DIR"
  chmod 755 /var/lib/fail2ban
  chmod 700 "$BAK_DIR"
}

stop_fail2ban() {
  systemctl stop fail2ban 2>/dev/null || true
  sleep 1
  # Never use pkill -f (matches caller shells). Use PID file only.
  if [[ -f /run/fail2ban/fail2ban.pid ]]; then
    local pid
    pid="$(cat /run/fail2ban/fail2ban.pid 2>/dev/null || true)"
    if [[ -n "${pid:-}" && -d "/proc/$pid" ]]; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      if [[ -d "/proc/$pid" ]]; then
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
  fi
}

start_fail2ban() {
  systemctl start fail2ban
  sleep 2
  fail2ban-client ping >/dev/null
}

db_integrity() {
  if [[ ! -f "$DB" ]]; then
    echo "missing"
    return 0
  fi
  sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null || echo "error"
}

apply_pragmas() {
  local target="$1"
  sqlite3 "$target" <<'SQL'
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=30000;
PRAGMA temp_store=MEMORY;
PRAGMA wal_checkpoint(PASSIVE);
SQL
}

create_empty_schema() {
  local target="$1"
  rm -f "$target" "${target}-wal" "${target}-shm"
  sqlite3 "$target" <<'SQL'
CREATE TABLE fail2banDb(version INTEGER);
INSERT INTO fail2banDb(version) VALUES(4);
CREATE TABLE jails(name TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL DEFAULT 1);
CREATE INDEX jails_name ON jails(name);
CREATE TABLE logs(
  jail TEXT NOT NULL,
  path TEXT,
  firstlinemd5 TEXT,
  lastfilepos INTEGER DEFAULT 0,
  FOREIGN KEY(jail) REFERENCES jails(name) ON DELETE CASCADE,
  UNIQUE(jail, path),
  UNIQUE(jail, path, firstlinemd5)
);
CREATE INDEX logs_path ON logs(path);
CREATE INDEX logs_jail_path ON logs(jail, path);
CREATE TABLE bans(
  jail TEXT NOT NULL,
  ip TEXT,
  timeofban INTEGER NOT NULL,
  bantime INTEGER NOT NULL,
  bancount INTEGER NOT NULL DEFAULT 1,
  data JSON,
  FOREIGN KEY(jail) REFERENCES jails(name)
);
CREATE INDEX bans_jail_timeofban_ip ON bans(jail, timeofban);
CREATE INDEX bans_jail_ip ON bans(jail, ip);
CREATE INDEX bans_ip ON bans(ip);
CREATE TABLE bips(
  ip TEXT NOT NULL,
  jail TEXT NOT NULL,
  timeofban INTEGER NOT NULL,
  bantime INTEGER NOT NULL,
  bancount INTEGER NOT NULL DEFAULT 1,
  data JSON,
  PRIMARY KEY(ip, jail),
  FOREIGN KEY(jail) REFERENCES jails(name)
);
CREATE INDEX bips_timeofban ON bips(timeofban);
CREATE INDEX bips_ip ON bips(ip);
SQL
}

cmd_check() {
  require_root
  ensure_dirs
  if [[ ! -f "$DB" ]]; then
    log "DB missing at $DB"
    return 1
  fi
  local result
  result="$(db_integrity)"
  local mode
  mode="$(sqlite3 "$DB" 'PRAGMA journal_mode;' 2>/dev/null || echo unknown)"
  log "integrity=$result journal_mode=$mode"
  if [[ "$result" != "ok" ]]; then
    return 1
  fi
  if [[ "$mode" != "wal" ]]; then
    log "WARN: journal_mode is '$mode' (want wal); run harden"
    return 2
  fi
  return 0
}

cmd_repair() {
  require_root
  ensure_dirs
  command -v sqlite3 >/dev/null || die "sqlite3 not installed"

  local was_active=0
  if systemctl is-active --quiet fail2ban 2>/dev/null; then
    was_active=1
  fi

  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  stop_fail2ban

  if [[ -f "$DB" ]]; then
    cp -a "$DB" "$BAK_DIR/fail2ban.sqlite3.pre-repair.$ts"
    log "Backup: $BAK_DIR/fail2ban.sqlite3.pre-repair.$ts"
  else
    log "No existing DB; creating empty hardened DB"
    create_empty_schema "$DB"
    apply_pragmas "$DB"
    chown root:root "$DB"
    chmod 600 "$DB"
    [[ "$was_active" -eq 1 ]] && start_fail2ban
    log "Created fresh DB"
    return 0
  fi

  local recover="/tmp/fail2ban-recover-$ts.sql"
  local newdb="/var/lib/fail2ban/fail2ban.sqlite3.new.$$"
  rm -f "$newdb" "${newdb}-wal" "${newdb}-shm"

  if sqlite3 "$DB" ".recover" >"$recover" 2>/tmp/fail2ban-recover-$ts.err; then
    sqlite3 "$newdb" <"$recover"
  else
    log "WARN: .recover failed; creating empty schema"
    create_empty_schema "$newdb"
  fi

  local check
  check="$(sqlite3 "$newdb" 'PRAGMA integrity_check;' 2>/dev/null || echo error)"
  if [[ "$check" != "ok" ]]; then
    log "WARN: recovered DB integrity=$check; using empty schema"
    create_empty_schema "$newdb"
  fi

  apply_pragmas "$newdb"
  check="$(sqlite3 "$newdb" 'PRAGMA integrity_check;')"
  [[ "$check" == "ok" ]] || die "New DB still corrupt after rebuild"

  rm -f "${DB}-wal" "${DB}-shm"
  mv -f "$DB" "$BAK_DIR/fail2ban.sqlite3.replaced.$ts"
  mv -f "$newdb" "$DB"
  apply_pragmas "$DB"
  chown root:root "$DB"
  chmod 600 "$DB"
  chmod 600 "${DB}-wal" 2>/dev/null || true
  chmod 600 "${DB}-shm" 2>/dev/null || true
  rm -f "$recover" /tmp/fail2ban-recover-$ts.err

  # Keep last 10 backups
  ls -1t "$BAK_DIR"/fail2ban.sqlite3.* 2>/dev/null | tail -n +11 | xargs -r rm -f --

  if [[ "$was_active" -eq 1 ]]; then
    start_fail2ban
  fi
  log "Repair complete; integrity=ok journal_mode=$(sqlite3 "$DB" 'PRAGMA journal_mode;')"
}

find_fail2ban_database_py() {
  local f
  for f in /usr/lib/python3.*/site-packages/fail2ban/server/database.py; do
    if [[ -f "$f" ]]; then
      echo "$f"
      return 0
    fi
  done
  return 1
}

# fail2ban upstream sets journal_mode=MEMORY + synchronous=OFF (speed over safety).
# That is the main corruption source on abrupt stop / CPU starve. Re-apply after RPM updates.
ensure_python_sqlite_patch() {
  local dbpy
  dbpy="$(find_fail2ban_database_py || true)"
  if [[ -z "${dbpy:-}" ]]; then
    log "WARN: fail2ban database.py not found; skip Python patch"
    return 0
  fi
  if grep -q 'NT_SQLITE_HARDENING' "$dbpy" 2>/dev/null \
    && grep -q 'journal_mode = WAL' "$dbpy" 2>/dev/null \
    && grep -q 'synchronous = NORMAL' "$dbpy" 2>/dev/null; then
    log "Python SQLite hardening already present: $dbpy"
    return 0
  fi
  cp -a "$dbpy" "${dbpy}.bak.pre-wal-harden.$(date +%Y%m%d_%H%M%S)"
  python3 - "$dbpy" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
text = text.replace(
    'cur.execute("PRAGMA synchronous = OFF")',
    'cur.execute("PRAGMA synchronous = NORMAL")  # NT_SQLITE_HARDENING: was OFF',
)
text = text.replace(
    'cur.execute("PRAGMA journal_mode = MEMORY")',
    'cur.execute("PRAGMA journal_mode = WAL")  # NT_SQLITE_HARDENING: was MEMORY',
)
if 'busy_timeout' not in text.split('_connectDB')[1].split('def close')[0]:
    text = text.replace(
        'cur.execute("PRAGMA foreign_keys = ON")',
        'cur.execute("PRAGMA foreign_keys = ON")\n'
        '\t\t\tcur.execute("PRAGMA busy_timeout = 30000")  # NT_SQLITE_HARDENING',
        1,
    )
p.write_text(text)
print('patched', p)
PY
  log "Patched fail2ban SQLite pragmas in $dbpy (WAL + NORMAL sync)"
}

write_fail2ban_local() {
  mkdir -p /etc/fail2ban
  if [[ -f "$F2B_LOCAL" ]] && grep -q 'dbfile' "$F2B_LOCAL" 2>/dev/null; then
    # Ensure purge age is not too large (bloat increases corruption risk)
    if ! grep -q '^dbpurgeage' "$F2B_LOCAL"; then
      sed -i '/^dbfile/a dbpurgeage = 1d' "$F2B_LOCAL" || true
    fi
    if ! grep -q '^dbmaxmatches' "$F2B_LOCAL"; then
      sed -i '/^dbfile/a dbmaxmatches = 10' "$F2B_LOCAL" || true
    fi
    log "Updated existing $F2B_LOCAL"
    return 0
  fi

  cat >"$F2B_LOCAL" <<'EOF'
[Definition]
# Hardened persistent DB settings for CyberPanel / AlmaLinux.
# Upstream fail2ban uses MEMORY journal + synchronous=OFF; we patch database.py
# to WAL + NORMAL via fail2ban-db-maintain.sh (NT_SQLITE_HARDENING).
dbfile = /var/lib/fail2ban/fail2ban.sqlite3
dbpurgeage = 1d
dbmaxmatches = 10
EOF
  chmod 644 "$F2B_LOCAL"
  log "Wrote $F2B_LOCAL"
}

write_systemd_dropin() {
  mkdir -p "$DROPIN_DIR"
  # 30% CPUQuota previously starved filtersystemd/SQLite under load.
  cat >"$DROPIN_DIR/db-hardening.conf" <<'EOF'
[Service]
# Do not starve SQLite writes (corruption risk under journal load).
CPUQuota=100%
CPUAccounting=true
TimeoutStopSec=120
KillMode=mixed
EOF
  # Neutralize older aggressive CPU cap if present
  if [[ -f "$DROPIN_DIR/cpu-limit.conf" ]]; then
    cat >"$DROPIN_DIR/cpu-limit.conf" <<'EOF'
[Service]
# Superseded by db-hardening.conf (was CPUQuota=30%).
# Kept as empty override file so package updates do not recreate 30%.
EOF
  fi
  systemctl daemon-reload
  log "Installed systemd drop-in $DROPIN_DIR/db-hardening.conf"
}

write_timer_units() {
  local script
  script="$(readlink -f "$0" 2>/dev/null || echo /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh)"

  cat >/etc/systemd/system/"$SERVICE_UNIT" <<EOF
[Unit]
Description=Fail2ban SQLite integrity check and auto-repair
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$script auto
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
EOF

  cat >/etc/systemd/system/"$TIMER_UNIT" <<'EOF'
[Unit]
Description=Daily fail2ban SQLite integrity check

[Timer]
OnCalendar=daily
OnBootSec=5min
Persistent=true
RandomizedDelaySec=15min

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$TIMER_UNIT"
  log "Enabled $TIMER_UNIT"
}

install_symlink() {
  ln -sfn /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh \
    /usr/local/bin/fail2ban-db-maintain
  chmod 755 /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh
  log "Symlinked /usr/local/bin/fail2ban-db-maintain"
}

cmd_harden() {
  require_root
  ensure_dirs
  command -v sqlite3 >/dev/null || die "sqlite3 not installed (dnf install sqlite -y)"

  write_fail2ban_local
  write_systemd_dropin
  ensure_python_sqlite_patch

  if [[ -f "$DB" ]]; then
    # Apply WAL while stopped if possible; otherwise apply live (SQLite allows journal_mode switch carefully)
    local was_active=0
    if systemctl is-active --quiet fail2ban 2>/dev/null; then
      was_active=1
      stop_fail2ban
    fi
    apply_pragmas "$DB"
    chown root:root "$DB"
    chmod 600 "$DB"
    chmod 600 "${DB}-wal" 2>/dev/null || true
    chmod 600 "${DB}-shm" 2>/dev/null || true
    if [[ "$was_active" -eq 1 ]]; then
      start_fail2ban
    fi
    log "Applied WAL pragmas to $DB"
  else
    create_empty_schema "$DB"
    apply_pragmas "$DB"
    chown root:root "$DB"
    chmod 600 "$DB"
    log "Created hardened empty DB"
  fi
}

cmd_install_hardening() {
  require_root
  install_symlink
  cmd_harden
  write_timer_units
  # Ensure DB healthy on install
  if ! cmd_check; then
    log "Integrity failed on install; repairing"
    cmd_repair
  fi
  log "Install hardening complete"
}

cmd_auto() {
  require_root
  ensure_dirs
  # Re-apply Python patch if an RPM update restored MEMORY/OFF defaults
  ensure_python_sqlite_patch

  if [[ ! -f "$DB" ]]; then
    log "DB missing; creating hardened DB"
    create_empty_schema "$DB"
    apply_pragmas "$DB"
    chown root:root "$DB"
    chmod 600 "$DB"
    return 0
  fi

  local result mode
  result="$(db_integrity)"
  mode="$(sqlite3 "$DB" 'PRAGMA journal_mode;' 2>/dev/null || echo unknown)"

  if [[ "$result" != "ok" ]]; then
    log "Auto-repair triggered (integrity=$result)"
    cmd_repair
    return 0
  fi

  if [[ "$mode" != "wal" ]]; then
    log "Auto-harden journal_mode=$mode -> wal"
    apply_pragmas "$DB"
  fi

  # Soft checkpoint to keep WAL from growing forever (skip if fail2ban holds lock tightly)
  sqlite3 "$DB" "PRAGMA busy_timeout=30000; PRAGMA wal_checkpoint(PASSIVE);" >/dev/null 2>&1 || true
  log "Auto check OK (journal_mode=$(sqlite3 "$DB" 'PRAGMA journal_mode;'))"
}

cmd_all() {
  cmd_install_hardening
  if ! cmd_check; then
    cmd_repair
  fi
  cmd_check
}

usage() {
  cat <<'EOF'
Usage: fail2ban-db-maintain.sh <command>

Commands:
  check              Integrity + WAL check (exit 0=ok, 1=bad, 2=needs harden)
  repair             Stop fail2ban, rebuild SQLite from .recover, restart
  harden             fail2ban.local + WAL pragmas + systemd drop-in
  install-hardening  Full install: symlink, harden, daily timer, repair if needed
  auto               Cron/timer entry: check and repair/harden if needed
  all                install-hardening + verify
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    check) cmd_check ;;
    repair) cmd_repair ;;
    harden) cmd_harden ;;
    install-hardening) cmd_install_hardening ;;
    auto) cmd_auto ;;
    all) cmd_all ;;
    -h|--help|help|"") usage; [[ -n "$cmd" ]] || exit 1 ;;
    *) usage; die "Unknown command: $cmd" ;;
  esac
}

main "$@"
