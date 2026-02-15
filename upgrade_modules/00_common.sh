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

Retry_Command() {
  for i in {1..50}; do
    eval "$1"  && break || echo -e "\n$1 has failed for $i times\nWait for 3 seconds and try again...\n"; sleep 3;
  done
}
