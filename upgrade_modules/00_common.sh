#!/usr/bin/env bash
# CyberPanel upgrade – common helpers (logging, check return, retry, branch check).
# Sourced by cyberpanel_upgrade.sh. Do not run standalone.

Debug_Log() {
  echo -e "\n${1}=${2}\n" >>  "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
}

Debug_Log2() {
  echo -e "\n${1}" >> /var/log/upgradeLogs.txt
}

Branch_Check() {
  if [[ "$1" = *.*.* ]]; then
    Output=$(awk -v num1="$Base_Number" -v num2="${1//[[:space:]]/}" '
  BEGIN {
    print "num1", (num1 < num2 ? "<" : ">="), "num2"
  }
  ')
    if [[ $Output = *">="* ]]; then
      echo -e "\nYou must use version number higher than 2.3.4"
      exit
    else
      raw="${1//[[:space:]]/}"
      if [[ "$raw" = v* ]]; then
        Branch_Name="$raw"
      else
        Branch_Name="v$raw"
      fi
      echo -e "\nSet branch name to $Branch_Name...\n"
    fi
  else
    echo -e "\nPlease input a valid format version number."
    exit
  fi
}

Check_Return() {
  local LAST_EXIT_CODE=$?
  if [[ $LAST_EXIT_CODE != "0" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Command failed with exit code: $LAST_EXIT_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
    if [[ -n "$1" ]] ; then
      echo -e "\n\n\n$1"
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Error message: $1" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    echo -e  "above command failed..."
    Debug_Log2 "command failed. For more information read /var/log/installLogs.txt [404]"
    if [[ "$2" = "no_exit" ]] || [[ "$3" = "continue" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Continuing despite error..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      if [[ "$1" == *"Virtualenv creation failed"* ]] || [[ "$1" == *"Python upgrade.py"* ]]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] FATAL: Critical error, exiting" | tee -a /var/log/cyberpanel_upgrade_debug.log
        exit $LAST_EXIT_CODE
      else
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Non-critical error, continuing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      fi
    fi
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Command succeeded" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
}

Regenerate_Cert() {
  cat <<EOF >/usr/local/CyberCP/cert_conf
[req]
prompt=no
distinguished_name=cyberpanel
[cyberpanel]
commonName = www.example.com
countryName = CP
localityName = CyberPanel
organizationName = CyberPanel
organizationalUnitName = CyberPanel
stateOrProvinceName = CP
emailAddress = mail@example.com
name = CyberPanel
surname = CyberPanel
givenName = CyberPanel
initials = CP
dnQualifier = CyberPanel
[server_exts]
extendedKeyUsage = 1.3.6.1.5.5.7.3.1
EOF
  if [[ $1 == "8090" ]]; then
    openssl req -x509 -config /usr/local/CyberCP/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout /usr/local/lscp/conf/key.pem -out /usr/local/lscp/conf/cert.pem
  fi
  if [[ $1 == "7080" ]]; then
    if [[ -f /usr/local/lsws/admin/conf/webadmin.key ]]; then
      key_path="/usr/local/lsws/admin/conf/webadmin.key"
      cert_path="/usr/local/lsws/admin/conf/webadmin.crt"
    else
      key_path="/usr/local/lsws/admin/conf/cert/admin.key"
      cert_path="/usr/local/lsws/admin/conf/cert/admin.crt"
    fi
    openssl req -x509 -config /usr/local/CyberCP/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout $key_path -out $cert_path
  fi
  rm -f /usr/local/CyberCP/cert_conf
}

# Prefer Python 3.11+ for temporary /usr/local/CyberPanel venv and CyberCP venv (shared with 08_main_upgrade.sh).
CYBERCP_UPGRADE_VENV_PY="/usr/bin/python3"
CyberCP_Upgrade_Select_VenvBootstrapPython() {
  CYBERCP_UPGRADE_VENV_PY="/usr/bin/python3"
  local p
  for p in /usr/bin/python3.11 /usr/local/bin/python3.11 /usr/bin/python3.12 /usr/bin/python3.13 /usr/bin/python3.10; do
    if [[ -x "$p" ]] && "$p" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
      CYBERCP_UPGRADE_VENV_PY="$p"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
    CYBERCP_UPGRADE_VENV_PY="$(command -v python3)"
    return 0
  fi
}

# Before python3 -m venv on RHEL EL8+: ensure Python.h, gcc, MariaDB headers (mysqlclient).
CyberCP_Upgrade_Ensure_Rhel_Venv_Build_Deps() {
  if [[ "$Server_OS" != "CentOS" ]] && [[ "$Server_OS" != "AlmaLinux9" ]] && [[ "$Server_OS" != "AlmaLinux" ]] && [[ "$Server_OS" != "RockyLinux" ]]; then
    return 0
  fi
  if [[ "$Server_OS_Version" != "8" ]] && [[ "$Server_OS_Version" != "9" ]] && [[ "$Server_OS_Version" != "10" ]]; then
    return 0
  fi
  if ! command -v dnf >/dev/null 2>&1; then
    return 0
  fi
  CyberCP_Upgrade_Select_VenvBootstrapPython
  local maj min pyheader
  maj=$("$CYBERCP_UPGRADE_VENV_PY" -c 'import sys; print(sys.version_info[0])' 2>/dev/null || echo 3)
  min=$("$CYBERCP_UPGRADE_VENV_PY" -c 'import sys; print(sys.version_info[1])' 2>/dev/null || echo 11)
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ensuring Python ${maj}.${min} devel and build tools for CyberCP venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  if dnf install -y \
    "python${maj}.${min}" "python${maj}.${min}-devel" "python${maj}.${min}-pip" \
    gcc gcc-c++ make pkgconf-pkg-config redhat-rpm-config \
    openssl-devel libffi-devel zlib-devel bzip2-devel \
    MariaDB-devel 2>/dev/null; then
    :
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Retrying build deps with python3-devel / MariaDB-devel..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    dnf install -y python3-devel python3-pip gcc gcc-c++ make pkgconf-pkg-config redhat-rpm-config \
      openssl-devel libffi-devel zlib-devel bzip2-devel MariaDB-devel 2>/dev/null || true
  fi
  pyheader="/usr/include/python${maj}.${min}/Python.h"
  if [[ ! -f "$pyheader" ]]; then
    pyheader=$(find /usr/include -maxdepth 2 -name Python.h -path '*/python*' 2>/dev/null | head -1 || true)
  fi
  if [[ ! -f "${pyheader:-}" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Python.h missing after dnf install (python${maj}.${min}-devel)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    exit 1
  fi
  if [[ ! -f /usr/include/mysql/mysql.h ]] && [[ ! -f /usr/include/mariadb/mysql.h ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: mysql.h not found; installing MariaDB-devel if possible..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    dnf install -y MariaDB-devel 2>/dev/null || true
  fi
}

Retry_Command() {
  for i in {1..50}; do
    eval "$1"  && break || echo -e "\n$1 has failed for $i times\nWait for 3 seconds and try again...\n"; sleep 3;
  done
}

# Sets CYBERPANEL_UPGRADE_VERIFY_OK=1 when critical services respond (exported).
CyberPanel_Final_Upgrade_Verification() {
  CYBERPANEL_UPGRADE_VERIFY_OK=0
  local errors=0
  local panel_port="8090"
  if [[ -f /usr/local/lscp/conf/bind.conf ]]; then
    panel_port=$(tr -d '\r\n' < /usr/local/lscp/conf/bind.conf)
    panel_port="${panel_port##*:}"
  fi
  [[ -z "$panel_port" ]] && panel_port="8090"
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running post-upgrade verification..." | tee -a /var/log/cyberpanel_upgrade_debug.log

  systemctl is-active --quiet mariadb 2>/dev/null || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: mariadb not active" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }

  if systemctl cat cyberpanel.service >/dev/null 2>&1; then
    systemctl is-active --quiet cyberpanel.service 2>/dev/null || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: cyberpanel.service not active" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -lntp 2>/dev/null | grep -q '127.0.0.1:5003' || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: nothing listening on 127.0.0.1:5003" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }
    ss -lntp 2>/dev/null | grep -q ":${panel_port}" || ss -lntp 2>/dev/null | grep -q ':8090' || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: panel port not listening (${panel_port})" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }
  fi

  systemctl is-active --quiet lsws 2>/dev/null || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: lsws not active" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }

  local code="000"
  code=$(curl -k -L -sS --max-time 30 -o /dev/null -w '%{http_code}' "https://127.0.0.1:${panel_port}/" 2>/dev/null || echo "000")
  # Accept any of 200/302/401/403: the panel is up and answering; 401/403 just means an auth gate
  # (commit e7635b0 upstream). Treating those as failures produced false "Seems something wrong" reports.
  [[ "$code" =~ ^(200|302|401|403)$ ]] || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: panel HTTPS returned ${code}" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }

  if [[ -x /usr/local/CyberCP/bin/python ]]; then
    /usr/local/CyberCP/bin/python -c 'import django, MySQLdb, gunicorn; assert django.VERSION[0] >= 4' 2>/dev/null || { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: CyberCP venv imports failed" | tee -a /var/log/cyberpanel_upgrade_debug.log; errors=$((errors + 1)); }
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] VERIFY WARN: /usr/local/CyberCP/bin/python missing" | tee -a /var/log/cyberpanel_upgrade_debug.log
    errors=$((errors + 1))
  fi

  if [[ $errors -eq 0 ]]; then
    CYBERPANEL_UPGRADE_VERIFY_OK=1
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Post-upgrade verification passed." | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Post-upgrade verification failed (${errors} issue(s)). See warnings above." | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  export CYBERPANEL_UPGRADE_VERIFY_OK
}
