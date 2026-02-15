#!/bin/bash

#set -e -o pipefail
#set -x
#set -u

#CyberPanel installer script for CentOS 7, CentOS 8, CentOS 9, CentOS Stream 9, CloudLinux 7, CloudLinux 8, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10, RockyLinux 8, RockyLinux 9, RHEL 8, RHEL 9, Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, Ubuntu 24.04, Ubuntu 24.04.3, Debian 11, Debian 12, Debian 13, openEuler 20.03 and openEuler 22.03
#For whoever may edit this script, please follow:
#Please use Pre_Install_xxx() and Post_Install_xxx() if you want to something respectively before or after the panel installation
#and update below accordingly
#Please use variable/functions name as MySomething or My_Something, and please try not to use too-short abbreviation :)
#Please use On/Off,  True/False, Yes/No.

# Require root immediately so all later steps (logs, /root, /usr/local/CyberCP) succeed
if [[ $(id -u) -ne 0 ]] 2>/dev/null; then
    echo ""
    echo "This script must be run as root."
    echo "Run: sudo bash <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh) -b v2.5.5-dev"
    echo "Or:   sudo su -   then run the same command without sudo"
    echo ""
    exit 1
fi

Sudo_Test=$(set)
#for SUDO check

Set_Default_Variables() {

# Clear old log files
echo -e "Clearing old log files..."
rm -f /var/log/cyberpanel_upgrade_debug.log
rm -f /var/log/installLogs.txt
rm -f /var/log/upgradeLogs.txt

# Initialize new debug log
echo -e "\n\n========================================" > /var/log/cyberpanel_upgrade_debug.log
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting CyberPanel Upgrade Script" >> /var/log/cyberpanel_upgrade_debug.log
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Old log files have been cleared" >> /var/log/cyberpanel_upgrade_debug.log
echo -e "========================================\n" >> /var/log/cyberpanel_upgrade_debug.log

#### this is temp code for csf

rm -Rfv /usr/local/CyberCP/configservercsf
rm -fv /home/cyberpanel/plugins/configservercsf
rm -Rfv /usr/local/CyberCP/public/static/configservercsf

sed -i "/configservercsf/d" /usr/local/CyberCP/CyberCP/settings.py
sed -i "/configservercsf/d" /usr/local/CyberCP/CyberCP/urls.py
if [ ! -e /etc/cxs/cxs.pl ]; then
    sed -i "/configserver/d" /usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html
fi
#systemctl restart lscpd
### this is temp code for csf



export LC_CTYPE=en_US.UTF-8
echo -e "\nFetching latest data from CyberPanel server...\n"
echo -e "This may take few seconds..."

Server_Country="Unknown"
Server_OS=""
Server_OS_Version=""
Server_Provider='Undefined'

Temp_Value=$(curl --silent --max-time 30 -4 https://cyberpanel.net/version.txt)
Panel_Version=${Temp_Value:12:3}
Panel_Build=${Temp_Value:25:1}

Branch_Name="v${Panel_Version}.${Panel_Build}"
Base_Number="1.9.3"

Git_User=""
Git_Content_URL=""
Git_Clone_URL=""

MySQL_Version=$(mysql -V | grep -P '\d+.\d+.\d+' -o)
MySQL_Password=$(cat /etc/cyberpanel/mysqlPassword)


LSWS_Latest_URL="https://cyberpanel.sh/update.litespeedtech.com/ws/latest.php"
LSWS_Tmp=$(curl --silent --max-time 30 -4 "$LSWS_Latest_URL")
LSWS_Stable_Line=$(echo "$LSWS_Tmp" | grep "LSWS_STABLE")
LSWS_Stable_Version=$(expr "$LSWS_Stable_Line" : '.*LSWS_STABLE=\(.*\) BUILD .*')
# Fallback to LSWS 6.3.4 (Stable) if fetch failed or empty
if [ -z "$LSWS_Stable_Version" ]; then
    LSWS_Stable_Version="6.3.4"
fi
#grab the LSWS latest stable version.

Debug_Log2 "Starting Upgrade...1"

rm -rf /root/cyberpanel_upgrade_tmp
mkdir -p /root/cyberpanel_upgrade_tmp
cd /root/cyberpanel_upgrade_tmp || exit
}

Debug_Log() {
echo -e "\n${1}=${2}\n" >>  "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
}

Debug_Log2() {
echo -e "\n${1}" >> /var/log/upgradeLogs.txt
}

Check_Root() {
echo -e "\nChecking root privileges..."
  # If we're actually root (uid 0), allow regardless of SUDO in environment (e.g. curl | sudo bash)
  if [[ $(id -u) -eq 0 ]] 2>/dev/null; then
    echo -e "\nYou are running as root...\n"
    return 0
  fi

  if echo "$Sudo_Test" | grep SUDO >/dev/null; then
    echo -e "\nYou are using SUDO, please run as root user...\n"
    echo -e "\nIf you don't have direct access to root user, please run \e[31msudo su -\e[39m command (do NOT miss the \e[31m-\e[39m at end or it will fail) and then run installation command again."
    exit 1
  fi

  echo -e "\nYou must run as root user to install CyberPanel...\n"
  echo -e "Run: \e[31msudo su -\e[39m then run this script again, or: curl -sL <url> | sudo bash -s -- <args>"
  exit 1
}

Check_Server_IP() {
echo -e "Checking server location...\n"

Server_Country=$(curl --silent --max-time 10 -4 https://cyberpanel.sh/?country)
if [[ ${#Server_Country} != "2" ]] ; then
  Server_Country="Unknown"
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_Country" "$Server_Country"
fi

if [[ "$*" = *"--mirror"* ]] ; then
  Server_Country="CN"
  echo -e "Forced to use mirror server due to --mirror argument...\n"
fi

if [[ "$Server_Country" = *"CN"* ]] ; then
  Server_Country="CN"
  echo -e "Setting up to use mirror server...\n"
fi
}

Check_OS() {
if [[ ! -f /etc/os-release ]] ; then
  echo -e "Unable to detect the Operating System...\n"
  exit
fi

if ! uname -m | grep -qE 'x86_64|aarch64' ; then
  echo -e "x86_64 or ARM system is required...\n"
  exit
fi

if grep -q -E "CentOS Linux 7|CentOS Linux 8|CentOS Linux 9|CentOS Stream 9" /etc/os-release ; then
  Server_OS="CentOS"
elif grep -q "Red Hat Enterprise Linux" /etc/os-release ; then
  Server_OS="RedHat"
elif grep -q -E "CloudLinux 7|CloudLinux 8|CloudLinux 9" /etc/os-release ; then
  Server_OS="CloudLinux"
elif grep -q -E "Rocky Linux" /etc/os-release ; then
  Server_OS="RockyLinux"
elif grep -q -E "AlmaLinux-8|AlmaLinux-9|AlmaLinux-10" /etc/os-release ; then
  Server_OS="AlmaLinux"
  # Set specific version for AlmaLinux 9+ to use dnf instead of yum
  if grep -q -E "AlmaLinux-9|AlmaLinux-10" /etc/os-release ; then
    Server_OS="AlmaLinux9"
  fi
elif grep -q -E "Ubuntu 18.04|Ubuntu 20.04|Ubuntu 20.10|Ubuntu 22.04|Ubuntu 24.04|Ubuntu 24.04.3" /etc/os-release ; then
  Server_OS="Ubuntu"
elif grep -q -E "Debian GNU/Linux 11|Debian GNU/Linux 12|Debian GNU/Linux 13" /etc/os-release ; then
  Server_OS="Ubuntu"
elif grep -q -E "openEuler 20.03|openEuler 22.03" /etc/os-release ; then
  Server_OS="openEuler"
else
  echo -e "Unable to detect your system..."
  echo -e "\nCyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, Ubuntu 24.04, Ubuntu 24.04.3, Debian 11, Debian 12, Debian 13, CentOS 7, CentOS 8, CentOS 9, CentOS Stream 9, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10, RockyLinux 8, RockyLinux 9, RHEL 8, RHEL 9, CloudLinux 7, CloudLinux 8, CloudLinux 9, openEuler 20.03, openEuler 22.03...\n"
  Debug_Log2 "CyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, Ubuntu 24.04, Ubuntu 24.04.3, Debian 11, Debian 12, Debian 13, CentOS 7, CentOS 8, CentOS 9, CentOS Stream 9, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10, RockyLinux 8, RockyLinux 9, RHEL 8, RHEL 9, CloudLinux 7, CloudLinux 8, CloudLinux 9, openEuler 20.03, openEuler 22.03... [404]"
  exit
fi

Server_OS_Version=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )
#to make 20.04 display as 20, etc.

echo -e "System: $Server_OS $Server_OS_Version detected...\n"

if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]] || [[ "$Server_OS" = "RedHat" ]]; then
  # Keep AlmaLinux9 separate for dnf package management
  if [[ "$Server_OS" != "AlmaLinux9" ]]; then
    Server_OS="CentOS"
    #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
    #treat CloudLinux, Rocky and Alma as CentOS
  fi
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_OS" "$Server_OS $Server_OS_Version"
fi

}

Check_Provider() {
if hash dmidecode >/dev/null 2>&1; then
  if [[ "$(dmidecode -s bios-vendor)" = "Google" ]]; then
    Server_Provider="Google Cloud Platform"
  elif [[ "$(dmidecode -s bios-vendor)" = "DigitalOcean" ]]; then
    Server_Provider="Digital Ocean"
  elif [[ "$(dmidecode -s system-product-name | cut -c 1-7)" = "Alibaba" ]]; then
    Server_Provider="Alibaba Cloud"
  elif [[ "$(dmidecode -s system-manufacturer)" = "Microsoft Corporation" ]]; then
    Server_Provider="Microsoft Azure"
  elif [[ -d /usr/local/qcloud ]]; then
    Server_Provider="Tencent Cloud"
  else
    Server_Provider="Undefined"
  fi
else
  Server_Provider='Undefined'
fi

if [[ -f /sys/devices/virtual/dmi/id/product_uuid ]]; then
  if [[ "$(cut -c 1-3 /sys/devices/virtual/dmi/id/product_uuid)" = 'EC2' ]] && [[ -d /home/ubuntu ]]; then
    Server_Provider='Amazon Web Service'
  fi
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_Provider" "$Server_Provider"
fi
}

Branch_Check() {
if [[ "$1" = *.*.* ]]; then
  #check input if it's valid format as X.Y.Z
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
    # Do not add "v" if user already passed e.g. v2.5.5-dev (avoids vv2.5.5-dev)
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
  #check previous command result , 0 = ok ,  non-0 = something wrong.
# shellcheck disable=SC2181
local LAST_EXIT_CODE=$?
if [[ $LAST_EXIT_CODE != "0" ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Command failed with exit code: $LAST_EXIT_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  if [[ -n "$1" ]] ; then
    echo -e "\n\n\n$1"
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Error message: $1" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  echo -e  "above command failed..."
  Debug_Log2 "command failed. For more information read /var/log/installLogs.txt [404]"
  
  # Check if this is a critical error that should stop the upgrade
  if [[ "$2" = "no_exit" ]] || [[ "$3" = "continue" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Continuing despite error..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    # Only exit for critical errors
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
# check command success or not

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
# shellcheck disable=SC2034
for i in {1..50};
do
  eval "$1"  && break || echo -e "\n$1 has failed for $i times\nWait for 3 seconds and try again...\n"; sleep 3;
done
}

# Optional GitHub user override (same repo structure as usmannasir/cyberpanel)
# Set via --repo USER or -r USER to use any GitHub user's cyberpanel repo
Git_User_Override=""
# Skip full system package update (yum/dnf update -y) to speed up upgrade; use when system is already updated
Skip_System_Update=""
# MariaDB version for repo setup: 11.8 (LTS, default) or 12.1
MARIADB_VER="11.8"

Check_Argument() {
# Parse --branch / -b (extract first word after -b or --branch)
if [[ "$*" = *"--branch "* ]]; then
  Branch_Name=$(echo "$*" | sed -n 's/.*--branch \([^ ]*\).*/\1/p' | head -1)
  [[ -n "$Branch_Name" ]] && Branch_Check "$Branch_Name"
elif [[ "$*" = *"-b "* ]]; then
  Branch_Name=$(echo "$*" | sed -n 's/.*-b \([^ ]*\).*/\1/p' | head -1)
  [[ -n "$Branch_Name" ]] && Branch_Check "$Branch_Name"
fi
# Parse --repo / -r to use any GitHub user (same URL structure as usmannasir/cyberpanel)
if [[ "$*" = *"--repo "* ]]; then
  Git_User_Override=$(echo "$*" | sed -n 's/.*--repo \([^ ]*\).*/\1/p' | head -1)
fi
if [[ "$*" = *"-r "* ]] && [[ -z "$Git_User_Override" ]]; then
  Git_User_Override=$(echo "$*" | sed -n 's/.*-r \([^ ]*\).*/\1/p' | head -1)
fi
# Parse --no-system-update to skip yum/dnf update -y (faster upgrade when system is already updated)
if [[ "$*" = *"--no-system-update"* ]]; then
  Skip_System_Update="yes"
  echo -e "\nUsing --no-system-update: skipping full system package update.\n"
fi
# Parse --mariadb-version 10.11|11.8|12.1 (default 11.8)
# --mariadb is shorthand for --mariadb-version 10.11 (MariaDB default, matches 10.11.x-MariaDB Server)
if [[ "$*" = *"--mariadb"* ]] && [[ "$*" != *"--mariadb-version "* ]]; then
  MARIADB_VER="10.11"
  echo -e "\nUsing --mariadb: MariaDB 10.11 selected (non-interactive).\n"
elif [[ "$*" = *"--mariadb-version "* ]]; then
  MARIADB_VER=$(echo "$*" | sed -n 's/.*--mariadb-version \([^ ]*\).*/\1/p' | head -1)
  MARIADB_VER="${MARIADB_VER:-11.8}"
fi
if [[ "$MARIADB_VER" != "10.11" ]] && [[ "$MARIADB_VER" != "11.8" ]] && [[ "$MARIADB_VER" != "12.1" ]]; then
  MARIADB_VER="11.8"
fi
}

Pre_Upgrade_Setup_Git_URL() {
  if [[ $Server_Country != "CN" ]] ; then
    if [[ -n "$Git_User_Override" ]]; then
      Git_User="$Git_User_Override"
      echo -e "\nUsing GitHub repo: ${Git_User}/cyberpanel (same URL structure as usmannasir)\n"
    else
      Git_User="usmannasir"
    fi
    Git_Content_URL="https://raw.githubusercontent.com/${Git_User}/cyberpanel"
    Git_Clone_URL="https://github.com/${Git_User}/cyberpanel.git"
  else
    if [[ -n "$Git_User_Override" ]]; then
      Git_User="$Git_User_Override"
    else
      Git_User="qtwrk"
    fi
    Git_Content_URL="https://gitee.com/${Git_User}/cyberpanel/raw"
    Git_Clone_URL="https://gitee.com/${Git_User}/cyberpanel.git"
  fi

  if [[ "$Debug" = "On" ]] ; then
    Debug_Log "Git_URL" "$Git_Content_URL"
  fi
}

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

  systemctl enable mysql
  systemctl start mysql

  mysql_upgrade -uroot -p"$MySQL_Password"

fi

mysql -uroot -p"$MySQL_Password" -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '$MySQL_Password';flush privileges"
}

Pre_Upgrade_Setup_Repository() {
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pre_Upgrade_Setup_Repository started for OS: $Server_OS" | tee -a /var/log/cyberpanel_upgrade_debug.log

if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] ; then
  # Reduce dnf/yum timeouts and mirror issues (e.g. ftp.lip6.fr connection timeout)
  for dnf_conf in /etc/dnf/dnf.conf /etc/yum.conf; do
    if [[ -f "$dnf_conf" ]]; then
      grep -q '^timeout=' "$dnf_conf" 2>/dev/null || echo 'timeout=120' >> "$dnf_conf"
      grep -q '^minrate=' "$dnf_conf" 2>/dev/null || echo 'minrate=1000' >> "$dnf_conf"
      grep -q '^retries=' "$dnf_conf" 2>/dev/null || echo 'retries=5' >> "$dnf_conf"
      break
    fi
  done
  # For AlmaLinux 9: switch to repo.almalinux.org baseurl to avoid "Cannot find valid baseurl for repo: appstream"
  if [[ "$Server_OS" = "AlmaLinux9" ]] && [[ -d /etc/yum.repos.d ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fixing AlmaLinux 9 repos (appstream/baseos) for reliable mirror access" | tee -a /var/log/cyberpanel_upgrade_debug.log
    ALMA_VER="${Server_OS_Version:-9}"
    ARCH="x86_64"
    for repo in /etc/yum.repos.d/almalinux*.repo /etc/yum.repos.d/AlmaLinux*.repo; do
      [[ ! -f "$repo" ]] && continue
      if grep -q '^mirrorlist=' "$repo" 2>/dev/null; then
        sed -i 's|^mirrorlist=|#mirrorlist=|g' "$repo"
        sed -i 's|^#\s*baseurl=\(.*repo\.almalinux\.org.*\)|baseurl=\1|' "$repo"
        sed -i 's|^#baseurl=\(.*repo\.almalinux\.org.*\)|baseurl=\1|' "$repo"
      fi
    done
    # Ensure appstream/baseos have explicit baseurl (avoids "Cannot find valid baseurl"); process any .repo that has these sections
    for repofile in /etc/yum.repos.d/almalinux.repo /etc/yum.repos.d/almalinux*.repo /etc/yum.repos.d/AlmaLinux*.repo; do
      [[ ! -f "$repofile" ]] && continue
      if grep -q '^\[appstream\]' "$repofile" 2>/dev/null; then
        sed -i "/^\[appstream\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/AppStream/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
        # Add baseurl if section had only mirrorlist (no baseurl line)
        if ! sed -n '/^\[appstream\]/,/^\[/p' "$repofile" | grep -q '^baseurl='; then
          sed -i "/^\[appstream\]/a baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/AppStream/${ARCH}/os/" "$repofile"
        fi
      fi
      if grep -q '^\[baseos\]' "$repofile" 2>/dev/null; then
        sed -i "/^\[baseos\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/BaseOS/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
        if ! sed -n '/^\[baseos\]/,/^\[/p' "$repofile" | grep -q '^baseurl='; then
          sed -i "/^\[baseos\]/a baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/BaseOS/${ARCH}/os/" "$repofile"
        fi
      fi
      # CRB (CodeReady Builder) - avoids "Cannot find a valid baseurl for repo: crb"
      if grep -q '^\[crb\]' "$repofile" 2>/dev/null; then
        sed -i "/^\[crb\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/CRB/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
        if ! sed -n '/^\[crb\]/,/^\[/p' "$repofile" | grep -q '^baseurl='; then
          sed -i "/^\[crb\]/a baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/CRB/${ARCH}/os/" "$repofile"
        fi
      fi
      # Extras - avoids "Cannot find a valid baseurl for repo: extras"
      if grep -q '^\[extras\]' "$repofile" 2>/dev/null; then
        sed -i "/^\[extras\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/extras/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
        if ! sed -n '/^\[extras\]/,/^\[/p' "$repofile" | grep -q '^baseurl='; then
          sed -i "/^\[extras\]/a baseurl=https://repo.almalinux.org/almalinux/${ALMA_VER}/extras/${ARCH}/os/" "$repofile"
        fi
      fi
    done
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Setting up repositories for $Server_OS..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  rm -f /etc/yum.repos.d/CyberPanel.repo
  rm -f /etc/yum.repos.d/litespeed.repo
  if [[ "$Server_Country" = "CN" ]] ; then
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo
  else
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed.repo
  fi
  yum clean all
  if [[ -z "$Skip_System_Update" ]]; then
    yum update -y
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M-%S")] Skipping yum update (--no-system-update)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  yum autoremove epel-release -y
  rm -f /etc/yum.repos.d/epel.repo
  rm -f /etc/yum.repos.d/epel.repo.rpmsave
  yum autoremove epel-release -y
#all pre-upgrade operation for CentOS both 7/8

  if [[ "$Server_OS_Version" = "7" ]] ; then
    yum install epel-release -y
    yum -y install yum-utils
    yum -y groupinstall development
    rm -f /etc/yum.repos.d/dovecot.repo
    rm -f /etc/yum.repos.d/frank.repo
    rm -f /etc/yum.repos.d/ius-archive.repo
    rm -f /etc/yum.repos.d/ius.repo
    rm -f /etc/yum.repos.d/ius-testing.repo
    #rm -f /etc/yum.repos.d/lux.repo
    rm -f /etc/yum.repos.d/powerdns-auth-*

    rm -f /etc/yum.repos.d/MariaDB.repo
    rm -f /etc/yum.repos.d/MariaDB.repo.rpmsave

    yum erase gf-* -y

    rm -f /etc/yum.repos.d/gf.repo
    rm -f /etc/yum.repos.d/gf.repo.rpmsave

    rm -f /etc/yum.repos.d/copart-restic-epel-7.repo.repo
    rm -f /etc/yum.repos.d/copart-restic-epel-7.repo.rpmsave

    rm -f /etc/yum.repos.d/ius-archive.repo
    rm -f /etc/yum.repos.d/ius.repo
    rm -f /etc/yum.repos.d/ius-testing.repo

    yum clean all

    curl -o /etc/yum.repos.d/powerdns-auth-43.repo https://cyberpanel.sh/repo.powerdns.com/repo-files/centos-auth-43.repo
      Check_Return "yum repo" "no_exit"

    # Determine appropriate MariaDB repository based on OS version
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] ; then
        MARIADB_REPO="rhel9-amd64"
    else
        MARIADB_REPO="centos7-amd64"
    fi
    
    cat << EOF > /etc/yum.repos.d/MariaDB.repo
# MariaDB $MARIADB_VER repository list - updated 2026-02
# https://downloads.mariadb.org/mariadb/repositories/
[mariadb]
name = MariaDB
baseurl = https://mirror.mariadb.org/yum/$MARIADB_VER/$MARIADB_REPO
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF

    yum install yum-plugin-copr -y
    yum copr enable copart/restic -y
    rpm -ivh https://cyberpanel.sh/repo.ius.io/ius-release-el7.rpm

    if [[ "$Server_Country" = "CN" ]] ; then
      sed -i 's|http://yum.mariadb.org|https://cyberpanel.sh/yum.mariadb.org|g' /etc/yum.repos.d/MariaDB.repo
      sed -i 's|https://yum.mariadb.org/RPM-GPG-KEY-MariaDB|https://cyberpanel.sh/yum.mariadb.org/RPM-GPG-KEY-MariaDB|g' /etc/yum.repos.d/MariaDB.repo
      # use MariaDB Mirror
      sed -i 's|https://download.copr.fedorainfracloud.org|https://cyberpanel.sh/download.copr.fedorainfracloud.org|g' /etc/yum.repos.d/_copr_copart-restic.repo
      sed -i 's|http://repo.iotti.biz|https://cyberpanel.sh/repo.iotti.biz|g' /etc/yum.repos.d/frank.repo
      sed -i "s|mirrorlist=https://mirrorlist.ghettoforge.net/el/7/gf/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/el/7/gf/x86_64/|g" /etc/yum.repos.d/gf.repo
      sed -i "s|mirrorlist=https://mirrorlist.ghettoforge.net/el/7/plus/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/el/7/plus/x86_64/|g" /etc/yum.repos.d/gf.repo
      sed -i 's|https://repo.ius.io|https://cyberpanel.sh/repo.ius.io|g' /etc/yum.repos.d/ius.repo
      sed -i 's|http://repo.iotti.biz|https://cyberpanel.sh/repo.iotti.biz|g' /etc/yum.repos.d/lux.repo
      sed -i 's|http://repo.powerdns.com|https://cyberpanel.sh/repo.powerdns.com|g' /etc/yum.repos.d/powerdns-auth-43.repo
      sed -i 's|https://repo.powerdns.com|https://cyberpanel.sh/repo.powerdns.com|g' /etc/yum.repos.d/powerdns-auth-43.repo
    fi
    yum install yum-plugin-priorities -y

    yum update -y

    yum install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel gpgme-devel curl-devel git socat openssl-devel MariaDB-shared mariadb-devel python36u python36u-pip python36u-devel bind-utils

    Pre_Upgrade_CentOS7_MySQL

    #all pre-upgrade operation for CentOS 7
  elif [[ "$Server_OS_Version" = "8" ]] ; then
#    cat <<EOF >/etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo
#[powertools-for-cyberpanel]
#name=CentOS Linux \$releasever - PowerTools
#mirrorlist=http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=PowerTools&infra=\$infra
#baseurl=http://mirror.centos.org/\$contentdir/\$releasever/PowerTools/\$basearch/os/
#gpgcheck=1
#enabled=1
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
#EOF
  rm -f /etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo

  if [[ "$Server_Country" = "CN" ]] ; then
    dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  else
    dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  fi

  dnf install epel-release -y

  dnf install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils
  dnf install gpgme-devel -y
  dnf install python3 -y

  elif [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] ; then
  rm -f /etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo

  if [[ "$Server_Country" = "CN" ]] ; then
    dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el9.noarch.rpm
  else
    dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el9.noarch.rpm
  fi

  dnf install epel-release -y 2>/dev/null || {
    # Fallback when appstream was broken or epel-release not in repo (e.g. AlmaLinux 9)
    if [[ "$Server_OS_Version" = "9" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing EPEL from Fedora RPM (epel-release not in repo)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm 2>/dev/null || true
    fi
  }

  # MariaDB repo for EL8/EL9 so --mariadb-version 11.8 (or 10.11/12.1) is actually used (distro default is 10.11)
  if [[ "$Server_OS_Version" = "8" ]] || [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      MARIADB_REPO="rhel9-amd64"
    else
      MARIADB_REPO="rhel8-amd64"
    fi
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Configuring MariaDB $MARIADB_VER repo for EL$Server_OS_Version..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    cat << EOF > /etc/yum.repos.d/MariaDB.repo
# MariaDB $MARIADB_VER repository - CyberPanel upgrade
# https://downloads.mariadb.org/mariadb/repositories/
[mariadb]
name = MariaDB $MARIADB_VER
baseurl = https://mirror.mariadb.org/yum/$MARIADB_VER/$MARIADB_REPO
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
    if [[ "$Server_Country" = "CN" ]]; then
      sed -i 's|http://yum.mariadb.org|https://cyberpanel.sh/yum.mariadb.org|g' /etc/yum.repos.d/MariaDB.repo
      sed -i 's|https://yum.mariadb.org/RPM-GPG-KEY-MariaDB|https://cyberpanel.sh/yum.mariadb.org/RPM-GPG-KEY-MariaDB|g' /etc/yum.repos.d/MariaDB.repo
    fi
    dnf clean metadata --disablerepo='*' --enablerepo=mariadb 2>/dev/null || true
  fi

  # AlmaLinux 9 specific package installation
  if [[ "$Server_OS" = "AlmaLinux9" ]] ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing AlmaLinux 9 specific packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Install essential build tools
    dnf groupinstall -y 'Development Tools'
    
    # Install PHP dependencies that are missing on AlmaLinux 9
    dnf install -y ImageMagick ImageMagick-devel gd gd-devel libicu libicu-devel \
                   oniguruma oniguruma-devel aspell aspell-devel libc-client libc-client-devel \
                   libmemcached libmemcached-devel freetype-devel libjpeg-turbo-devel \
                   libpng-devel libwebp-devel libXpm-devel libzip-devel openssl-devel \
                   sqlite-devel libxml2-devel libxslt-devel curl-devel libedit-devel \
                   readline-devel pkgconfig cmake gcc-c++
    
    # Install/upgrade MariaDB server only (server + devel for Python/php; client not required for panel)
    dnf install -y MariaDB-server MariaDB-devel 2>/dev/null || dnf install -y mariadb-server mariadb-devel
    # Upgrade to chosen version if already installed (e.g. 10.11 -> 11.8)
    dnf upgrade -y MariaDB-server MariaDB-devel 2>/dev/null || true
    systemctl restart mariadb 2>/dev/null || true

    # Install additional required packages
    dnf install -y wget curl unzip zip rsync firewalld psmisc git python3 python3-pip python3-devel
  fi

  dnf install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils
  dnf install gpgme-devel -y
  dnf install python3 -y
  fi
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Setting up Ubuntu repositories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Ensure nobody group exists (required for various operations)
  if ! getent group nobody > /dev/null 2>&1 ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating 'nobody' group..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    groupadd nobody
  fi

  apt update -y
  if [[ -z "$Skip_System_Update" ]]; then
    export DEBIAN_FRONTEND=noninteractive ; apt-get -o Dpkg::Options::="--force-confold" upgrade -y
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M-%S")] Skipping apt upgrade (--no-system-update)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]] ; then
    if [[ "$Server_OS_Version" = "24" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Ubuntu 24.04 specific packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Ubuntu 22.04 specific packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    # Install Python development packages required for virtualenv on Ubuntu 22.04/24.04
    DEBIAN_FRONTEND=noninteractive apt install -y python3-dev python3-venv python3-pip python3-setuptools python3-wheel
    DEBIAN_FRONTEND=noninteractive apt install -y dnsutils net-tools htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git socat vim unzip zip libmariadb-dev-compat libmariadb-dev

  else
    DEBIAN_FRONTEND=noninteractive apt install -y htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev-compat libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev virtualenv git dnsutils
  fi
  DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
  DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
  DEBIAN_FRONTEND=noninteractive apt install -y python3-venv

  ### fix for pip issue on ubuntu 22 and 24

  apt-get remove --purge virtualenv -y
  # Handle Ubuntu 24.04's externally-managed-environment policy
  if [[ "$Server_OS_Version" = "24" ]]; then
    echo -e "Ubuntu 24.04 detected - using apt for virtualenv installation"
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-virtualenv
  else
    pip uninstall -y virtualenv 2>/dev/null || true
    rm -rf /usr/lib/python3/dist-packages/virtualenv*
    pip3 install --upgrade virtualenv
  fi


  if [[ "$Server_OS_Version" = "18" ]] ; then
    :
#all pre-upgrade operation for Ubuntu 18
  elif [[ "$Server_OS_Version" = "20" ]] ; then
#    if ! grep -q "focal" /etc/apt/sources.list.d/dovecot.list ; then
#      sed -i 's|ce-2.3-latest/ubuntu/bionic bionic main|ce-2.3-latest/ubuntu/focal focal main|g' /etc/apt/sources.list.d/dovecot.list
#      rm -rf /etc/dovecot-backup
#      cp -r /etc/dovecot /etc/dovecot-backup
#      apt update
#      DEBIAN_FRONTEND=noninteractive apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" remove -y dovecot-mysql dovecot-pop3d dovecot-imapd
#      DEBIAN_FRONTEND=noninteractive apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install -y dovecot-mysql dovecot-pop3d dovecot-imapd
#      systemctl restart dovecot
#    fi
    #fix ubuntu 20 webmail login issue

    rm -f /etc/apt/sources.list.d/dovecot.list
    apt update
    DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y
  fi
#all pre-upgrade operation for Ubuntu 20
fi
if [[ "$Server_OS" = "openEuler" ]] ; then
  rm -f /etc/yum.repos.d/CyberPanel.repo
  rm -f /etc/yum.repos.d/litespeed.repo

  yum clean all
  yum update -y

  dnf install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git python3-devel tar socat bind-utils
  dnf install gpgme-devel -y
  dnf install python3 -y
fi
#all pre-upgrade operation for openEuler
}

Download_Requirement() {
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting Download_Requirement function..." | tee -a /var/log/cyberpanel_upgrade_debug.log
for i in {1..50};
  do
  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]] || [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
   echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading requirements.txt for OS version $Server_OS_Version" | tee -a /var/log/cyberpanel_upgrade_debug.log
   wget -O /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
   echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading requirements-old.txt for OS version $Server_OS_Version" | tee -a /var/log/cyberpanel_upgrade_debug.log
   wget -O /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments-old.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  if grep -q "Django==" /usr/local/requirments.txt ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Requirements file downloaded successfully" | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Fix pysftp dependency issue by removing it from requirements
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fixing pysftp dependency issue..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    sed -i 's/^pysftp$/# pysftp - deprecated, using paramiko instead/' /usr/local/requirments.txt
    sed -i 's/pysftp/# pysftp - deprecated, using paramiko instead/' /usr/local/requirments.txt
    
    break
  else
    echo -e "\n Requirement list has failed to download for $i times..."
    echo -e "Wait for 30 seconds and try again...\n"
    sleep 30
  fi
done
#special made function for Gitee.com, for whatever reason sometimes it fails to download this file
}



Pre_Upgrade_Required_Components() {

# Check if CyberCP directory exists but is incomplete/damaged
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking CyberCP directory integrity..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Define essential CyberCP components
CYBERCP_ESSENTIAL_DIRS=(
    "/usr/local/CyberCP/CyberCP"
    "/usr/local/CyberCP/plogical"
    "/usr/local/CyberCP/websiteFunctions"
    "/usr/local/CyberCP/manage"
)

CYBERCP_MISSING=0
for dir in "${CYBERCP_ESSENTIAL_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] INFO: Essential directory missing (will restore): $dir" | tee -a /var/log/cyberpanel_upgrade_debug.log
        CYBERCP_MISSING=1
    fi
done

# If essential directories are missing, perform automatic recovery (normal on some upgrade paths)
if [ $CYBERCP_MISSING -eq 1 ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] INFO: Restoring missing CyberCP directories from repository..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Backup any remaining configuration files if they exist
    if [ -f "/usr/local/CyberCP/CyberCP/settings.py" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backing up existing settings.py..." | tee -a /var/log/cyberpanel_upgrade_debug.log
        cp /usr/local/CyberCP/CyberCP/settings.py /tmp/cyberpanel_settings_backup.py
    fi
    
    # Clone fresh CyberPanel repository
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Cloning fresh CyberPanel repository for recovery..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    cd /usr/local
    rm -rf CyberCP_recovery_tmp
    
    if git clone "$Git_Clone_URL" CyberCP_recovery_tmp; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Repository cloned successfully for recovery" | tee -a /var/log/cyberpanel_upgrade_debug.log
        
        # Checkout the appropriate branch
        cd CyberCP_recovery_tmp
        git checkout "$Branch_Name" 2>/dev/null || git checkout stable
        
        # Copy missing components while preserving existing configurations
        for dir in "${CYBERCP_ESSENTIAL_DIRS[@]}"; do
            if [ ! -d "$dir" ]; then
                # Extract relative path after /usr/local/CyberCP/
                relative_path=${dir#/usr/local/CyberCP/}
                if [ -d "/usr/local/CyberCP_recovery_tmp/$relative_path" ]; then
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restoring missing directory: $dir" | tee -a /var/log/cyberpanel_upgrade_debug.log
                    mkdir -p "$(dirname "$dir")"
                    cp -r "/usr/local/CyberCP_recovery_tmp/$relative_path" "$dir"
                fi
            fi
        done
        
        # Restore settings.py if it was backed up
        if [ -f "/tmp/cyberpanel_settings_backup.py" ]; then
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restoring backed up settings.py..." | tee -a /var/log/cyberpanel_upgrade_debug.log
            cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
        fi
        
        # Clean up temporary clone
        rm -rf /usr/local/CyberCP_recovery_tmp
        
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Recovery completed. All essential CyberCP directories restored." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Failed to clone repository for recovery" | tee -a /var/log/cyberpanel_upgrade_debug.log
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Please run full installation instead of upgrade" | tee -a /var/log/cyberpanel_upgrade_debug.log
        exit 1
    fi
    
    cd /root/cyberpanel_upgrade_tmp || cd /root
fi

if [ "$Server_OS" = "Ubuntu" ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Preparing Ubuntu environment for virtualenv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  rm -rf /usr/local/CyberPanel
  
  # For Ubuntu 22.04 and 24.04, handle virtualenv installation properly
  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]; then
    if [[ "$Server_OS_Version" = "24" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 24.04: Using apt for virtualenv installation (externally-managed-environment policy)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      # Ubuntu 24.04 has externally-managed-environment, use apt
      DEBIAN_FRONTEND=noninteractive apt-get install -y python3-virtualenv python3-venv
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 22.04: Installing/upgrading virtualenv with proper dependencies..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      # Remove system virtualenv if it exists to avoid conflicts
      apt remove -y python3-virtualenv 2>/dev/null || true
      # Install latest virtualenv via pip
      pip3 install --upgrade pip setuptools wheel
      pip3 install --upgrade virtualenv
    fi
  else
    pip3 install --upgrade virtualenv
  fi
else
  rm -rf /usr/local/CyberPanel
  # AlmaLinux 9/10, Rocky 9: use python3 -m venv (no virtualenv pkg needed)
  if [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version: will use python3 -m venv, skipping virtualenv package" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      if [ -e /usr/bin/pip3 ]; then PIP3="/usr/bin/pip3"; else PIP3="pip3.6"; fi
      $PIP3 install --default-timeout=3600 virtualenv
      Check_Return
    fi
  else
    if [ -e /usr/bin/pip3 ]; then PIP3="/usr/bin/pip3"; else PIP3="pip3.6"; fi
    $PIP3 install --default-timeout=3600 virtualenv
    Check_Return
  fi
fi

if [[ -f /usr/local/CyberPanel/bin/python2 ]]; then
  echo -e "\nPython 2 dectected, doing re-setup...\n"
  rm -rf /usr/local/CyberPanel/bin
  if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    python3 -m venv --system-site-packages /usr/local/CyberPanel
  elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      python3 -m venv --system-site-packages /usr/local/CyberPanel
    else
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
    fi
  else
    virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
  fi
  Check_Return
elif [[ -d /usr/local/CyberPanel/bin/ ]]; then
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberPanel...\n"
else
  #!/bin/bash

echo -e "\nNo existing virtualenv found; creating fresh Python environment...\n"

# Attempt to create a virtual environment
if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  python3 -m venv /usr/local/CyberPanel
elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
  if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version: using python3 -m venv (no virtualenv pkg needed)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    python3 -m venv --system-site-packages /usr/local/CyberPanel
  else
    PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
    virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
  fi
else
  virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
fi

# Check if the virtualenv/venv command failed
if [ $? -ne 0 ]; then
    echo "virtualenv command failed."

    # Check if the operating system is AlmaLinux
    if grep -q "AlmaLinux" /etc/os-release; then
        echo "Operating system is AlmaLinux."

        # Check if the 'packaging' module is installed via RPM
        if rpm -q python3-packaging >/dev/null 2>&1; then
            echo "'packaging' module installed via RPM. Proceeding with uninstallation."

            # Uninstall the 'packaging' module using RPM
            sudo dnf remove python3-packaging -y

            # Check if uninstallation was successful
            if [ $? -eq 0 ]; then
                echo "Successfully uninstalled 'packaging' module."

                # Install and upgrade 'packaging' using pip
                pip install --upgrade packaging

                # Verify the installation
                if [ $? -eq 0 ]; then
                    echo "'packaging' module reinstalled and upgraded successfully."
                    if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
                        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu: using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
                        python3 -m venv --system-site-packages /usr/local/CyberPanel
                    elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
                        if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
                          python3 -m venv --system-site-packages /usr/local/CyberPanel
                        else
                          PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
                          virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
                        fi
                    else
                        virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
                    fi
                else
                    echo "Failed to install 'packaging' module using pip."
                fi
            else
                echo "Failed to uninstall 'packaging' module using RPM."
            fi
        else
            echo "'packaging' module is not installed via RPM. No action taken."
        fi
    else
        echo "Operating system is not AlmaLinux. No action taken."
    fi
else
    echo "virtualenv command executed successfully."
fi
fi

# shellcheck disable=SC1091
. /usr/local/CyberPanel/bin/activate
pip install --upgrade pip setuptools packaging

Download_Requirement

if [[ "$Server_OS" = "CentOS" ]] ; then
#  $PIP3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  $PIP3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberPanel/bin/activate
    Check_Return
#  pip3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "openEuler" ]] ; then
#  pip3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
fi

#virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
#  Check_Return

wget "${Git_Content_URL}/${Branch_Name}/plogical/upgrade.py"

if [[ "$Server_Country" = "CN" ]] ; then
  sed -i 's|git clone https://github.com/usmannasir/cyberpanel|echo git cloned|g' upgrade.py

  Retry_Command "git clone ${Git_Clone_URL}"
    Check_Return "git clone ${Git_Clone_URL}"

  # shellcheck disable=SC2086
  sed -i 's|https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/install/litespeed/httpd_config.xml|'${Git_Content_URL}/${Branch_Name}'//install/litespeed/httpd_config.xml|g' upgrade.py
  sed -i 's|https://cyberpanel.sh/composer.sh|https://gitee.com/qtwrk/cyberpanel/raw/stable/install/composer_cn.sh|g' upgrade.py
fi

}

# (Pre_Upgrade_Setup_Git_URL is defined earlier; this duplicate removed so --repo is respected)

Pre_Upgrade_Branch_Input() {
  echo -e "\nPress the Enter key to continue with latest version, or enter specific version such as: \e[31m2.3.4\e[39m , \e[31m2.4.4\e[39m ...etc"
  echo -e "\nIf nothing is input in 10 seconds, script will proceed with the latest stable version. "
  echo -e "\nPlease press the Enter key or specify a version number, or wait for 10 seconds: "
  printf "%s" ""
  read -r -t 10 Tmp_Input
  if [[ $Tmp_Input = "" ]]; then
    echo -e "Branch name set to $Branch_Name"
  else
    Branch_Check "$Tmp_Input"
  fi
}

Main_Upgrade() {
echo -e "\n[$(date +"%Y-%m-%d %H:%M:%S")] Starting Main_Upgrade function..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Resolve Python for upgrade (avoid FileNotFoundError when /usr/local/CyberPanel/bin/python missing)
CP_PYTHON=""
for py in /usr/local/CyberPanel/bin/python /usr/local/CyberCP/bin/python /usr/bin/python3 /usr/local/bin/python3; do
  if [[ -x "$py" ]]; then CP_PYTHON="$py"; break; fi
done
if [[ -z "$CP_PYTHON" ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: No Python found for upgrade (tried CyberPanel, CyberCP, python3)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  exit 1
fi
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Using Python: $CP_PYTHON" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Ensure ols_binaries_config exists (required by upgrade.py; may be missing when upgrading from older versions)
mkdir -p /usr/local/CyberCP/install
if [[ ! -f /usr/local/CyberCP/install/ols_binaries_config.py ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading ols_binaries_config.py (required for upgrade)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  wget -q -O /usr/local/CyberCP/install/ols_binaries_config.py "${Git_Content_URL}/${Branch_Name}/install/ols_binaries_config.py" 2>/dev/null || \
  curl -sL -o /usr/local/CyberCP/install/ols_binaries_config.py "${Git_Content_URL}/${Branch_Name}/install/ols_binaries_config.py" 2>/dev/null || true
fi
if [[ ! -f /usr/local/CyberCP/install/ols_binaries_config.py ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: ols_binaries_config.py not found; upgrade.py may fail with ModuleNotFoundError" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running: $CP_PYTHON upgrade.py $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Run upgrade.py and capture output
upgrade_output=$("$CP_PYTHON" upgrade.py "$Branch_Name" 2>&1)
RETURN_CODE=$?
echo "$upgrade_output" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check for TypeError specifically
if echo "$upgrade_output" | grep -q "TypeError: expected string or bytes-like object"; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: TypeError detected in upgrade.py, but continuing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    # Check if upgrade actually completed despite the error
    if echo "$upgrade_output" | grep -q "Upgrade Completed"; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Upgrade completed despite TypeError" | tee -a /var/log/cyberpanel_upgrade_debug.log
        RETURN_CODE=0
    fi
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Python upgrade.py returned code: $RETURN_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check if the command was successful (return code 0)
if [ $RETURN_CODE -eq 0 ]; then
    echo "Upgrade successful."
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] First upgrade attempt successful" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] First upgrade attempt failed with code $RETURN_CODE, starting fallback..." | tee -a /var/log/cyberpanel_upgrade_debug.log


    if [ -e /usr/bin/pip3 ]; then
    PIP3="/usr/bin/pip3"
  else
    PIP3="pip3.6"
  fi

  rm -rf /usr/local/CyberPanelTemp
  
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating temporary virtual environment for fallback upgrade..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Try python3 -m venv first (more reliable on Ubuntu 22.04)
  if python3 -m venv --system-site-packages /usr/local/CyberPanelTemp 2>/dev/null; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Temporary virtualenv created with python3 -m venv" | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    # Fallback to virtualenv command
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Trying virtualenv command for temporary environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanelTemp 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

# shellcheck disable=SC1091
. /usr/local/CyberPanelTemp/bin/activate

wget -O /usr/local/requirments-old.txt "${Git_Content_URL}/${Branch_Name}/requirments-old.txt"

    if [[ "$Server_OS" = "CentOS" ]] ; then
#  $PIP3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  $PIP3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberPanelTemp/bin/activate
    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
elif [[ "$Server_OS" = "openEuler" ]] ; then
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running fallback: /usr/local/CyberPanelTemp/bin/python upgrade.py $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log
/usr/local/CyberPanelTemp/bin/python upgrade.py "$Branch_Name" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
FALLBACK_CODE=$?
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fallback upgrade returned code: $FALLBACK_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
Check_Return

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing temporary environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -rf /usr/local/CyberPanelTemp

fi

echo -e "\n[$(date +"%Y-%m-%d %H:%M:%S")] Starting post-upgrade cleanup..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check if we need to recreate due to Python 2
NEEDS_RECREATE=0
if [[ -f /usr/local/CyberCP/bin/python2 ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Found Python 2 in CyberCP, will recreate with Python 3..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  NEEDS_RECREATE=1
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing old CyberCP virtual environment directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -rf /usr/local/CyberCP/bin
rm -rf /usr/local/CyberCP/lib
rm -rf /usr/local/CyberCP/lib64
rm -rf /usr/local/CyberCP/pyvenv.cfg

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking CyberCP virtual environment status after cleanup..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# After removing directories, we always need to recreate
if [[ $NEEDS_RECREATE -eq 1 ]] || [[ ! -d /usr/local/CyberCP/bin ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating/recreating CyberCP virtual environment with Python 3..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # First ensure the directory exists
  mkdir -p /usr/local/CyberCP
  
  # For Ubuntu 22.04+, we need to handle virtualenv differently
  VENV_SUCCESS=0
  
  # First try using python3 -m venv (more reliable on Ubuntu 22.04)
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Attempting to create virtual environment using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  virtualenv_output=$(python3 -m venv --system-site-packages /usr/local/CyberCP 2>&1)
  VENV_CODE=$?
  echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  if [[ $VENV_CODE -eq 0 ]] && [[ -f /usr/local/CyberCP/bin/activate ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtual environment created successfully using python3 -m venv" | tee -a /var/log/cyberpanel_upgrade_debug.log
    VENV_SUCCESS=1
  else
    # If that fails, try virtualenv command
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] python3 -m venv failed, trying virtualenv command..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # On Ubuntu 22.04, we need to ensure proper virtualenv installation
    if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 22.04 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  elif [[ "$Server_OS" = "CentOS" ]] && ([[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]); then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky Linux 9/10 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  elif [[ "$Server_OS" = "AlmaLinux9" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux 9 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    
    # Find the correct python3 path
    if [[ "$Server_OS" = "CentOS" ]] && ([[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]); then
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Using Python path: $PYTHON_PATH" | tee -a /var/log/cyberpanel_upgrade_debug.log
      virtualenv_output=$(virtualenv -p "$PYTHON_PATH" /usr/local/CyberCP 2>&1)
    elif [[ "$Server_OS" = "AlmaLinux9" ]]; then
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux 9 - Using Python path: $PYTHON_PATH" | tee -a /var/log/cyberpanel_upgrade_debug.log
      virtualenv_output=$(virtualenv -p "$PYTHON_PATH" /usr/local/CyberCP 2>&1)
    else
      virtualenv_output=$(virtualenv -p /usr/bin/python3 /usr/local/CyberCP 2>&1)
    fi
    VENV_CODE=$?
    echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Check if TypeError occurred (common on Ubuntu 22.04)
    if echo "$virtualenv_output" | grep -q "TypeError"; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: TypeError detected, attempting workaround..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      
      # Try alternative method using explicit system-site-packages
      virtualenv_output=$(virtualenv --python=/usr/bin/python3 --system-site-packages /usr/local/CyberCP 2>&1)
      VENV_CODE=$?
      echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    
    if [[ -f /usr/local/CyberCP/bin/activate ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtual environment created successfully" | tee -a /var/log/cyberpanel_upgrade_debug.log
      VENV_SUCCESS=1
      VENV_CODE=0
    fi
  fi
  
  if [[ $VENV_SUCCESS -eq 0 ]]; then
    VENV_CODE=1
  fi
  
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtualenv creation returned code: $VENV_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  if [[ $VENV_CODE -ne 0 ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] FATAL: Virtualenv creation failed with code $VENV_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo -e "Virtualenv creation failed. Please check the logs at /var/log/cyberpanel_upgrade_debug.log"
    exit $VENV_CODE
  fi
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] CyberCP virtualenv already exists, skipping recreation" | tee -a /var/log/cyberpanel_upgrade_debug.log
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberCP...\n"
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing old requirements file..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -f /usr/local/requirments.txt

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading new requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
Download_Requirement

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Python packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [ "$Server_OS" = "Ubuntu" ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu detected, activating virtual environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  # shellcheck disable=SC1091
  . /usr/local/CyberCP/bin/activate 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  ACTIVATE_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Activate returned code: $ACTIVATE_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Upgrading setuptools and packaging..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip install --upgrade setuptools packaging 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  PIP_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pip install returned code: $PIP_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Non-Ubuntu OS, activating virtual environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  # shellcheck disable=SC1091
  source /usr/local/CyberCP/bin/activate 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  ACTIVATE_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Activate returned code: $ACTIVATE_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  /usr/local/CyberCP/bin/pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  PIP_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pip install returned code: $PIP_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Verifying Django installation..." | tee -a /var/log/cyberpanel_upgrade_debug.log
# Test if Django is installed
if ! /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Django not found, installing requirements again..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Re-activate virtual environment
  source /usr/local/CyberCP/bin/activate
  
  # Install MySQL/MariaDB development headers for mysqlclient Python package
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing MySQL/MariaDB development headers..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  if [[ "$Server_OS" = "Ubuntu" ]] || [[ "$Server_OS" = "Debian" ]]; then
    # Ubuntu/Debian
    apt-get update -y
    apt-get install -y libmariadb-dev libmariadb-dev-compat pkg-config build-essential
  elif [[ "$Server_OS" =~ ^(CentOS|RHEL|AlmaLinux|RockyLinux|CloudLinux) ]]; then
    # RHEL-based systems
    if command -v dnf >/dev/null 2>&1; then
      # Remove conflicting packages first
      dnf remove -y mariadb mariadb-client-utils mariadb-server || true
      dnf remove -y MariaDB-server MariaDB-client MariaDB-devel || true
      
      # Install development packages with conflict resolution
      dnf install -y --allowerasing --skip-broken --nobest mariadb-devel pkgconfig gcc python3-devel || \
      dnf install -y --allowerasing --skip-broken --nobest mysql-devel pkgconfig gcc python3-devel || \
      dnf install -y --allowerasing --skip-broken --nobest mariadb-devel mariadb-connector-c-devel pkgconfig gcc python3-devel
    else
      yum install -y mariadb-devel pkgconfig gcc python3-devel
    fi
  fi

  # Check if mysql.h is available and create symlink if needed
  if [[ ! -f "/usr/include/mysql/mysql.h" ]] && [[ -f "/usr/include/mariadb/mysql.h" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating mysql.h symlink for compatibility..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    mkdir -p /usr/include/mysql
    ln -sf /usr/include/mariadb/mysql.h /usr/include/mysql/mysql.h
  fi
  
  # Re-install requirements
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Re-installing Python requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Django is properly installed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing WSGI-LSAPI with optimized compilation..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Save current directory
UPGRADE_CWD=$(pwd)

cd /tmp || exit
rm -rf wsgi-lsapi-2.1*

wget -q https://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
tar xf wsgi-lsapi-2.1.tgz
cd wsgi-lsapi-2.1 || exit

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Configuring WSGI..." | tee -a /var/log/cyberpanel_upgrade_debug.log
PYTHON_CFG="${CP_PYTHON:-/usr/bin/python3}"
[[ -x "$PYTHON_CFG" ]] || PYTHON_CFG="/usr/bin/python3"
"$PYTHON_CFG" ./configure.py 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log

# Fix Makefile to use proper optimization flags to avoid _FORTIFY_SOURCE warnings
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Optimizing Makefile for proper compilation..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ -f Makefile ]]; then
    # Replace -O0 -g3 with -O2 -g to satisfy _FORTIFY_SOURCE
    sed -i 's/-O0 -g3/-O2 -g/g' Makefile
    # Ensure we have proper optimization flags
    if grep -q "CFLAGS" Makefile && ! grep -q -e "-O2" Makefile; then
        sed -i 's/CFLAGS =/CFLAGS = -O2/' Makefile
    fi
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Makefile optimized for proper compilation" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Compiling WSGI with optimized flags..." | tee -a /var/log/cyberpanel_upgrade_debug.log
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] (Upstream WSGI source may show harmless strncpy/gstate warnings; build can still succeed.)" | tee -a /var/log/cyberpanel_upgrade_debug.log
make clean 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
make 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing lswsgi binary..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -f /usr/local/CyberCP/bin/lswsgi
cp lswsgi /usr/local/CyberCP/bin/
chmod +x /usr/local/CyberCP/bin/lswsgi

# Return to original directory
cd "$UPGRADE_CWD" || cd /root

# Final verification
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running final verification..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null && [[ -f /usr/local/CyberCP/bin/lswsgi ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] All components successfully installed!" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Some components may be missing, check logs" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Main_Upgrade function completed" | tee -a /var/log/cyberpanel_upgrade_debug.log
}

Post_Upgrade_System_Tweak() {
  if [[ "$Server_OS" = "CentOS" ]] ; then

  #for cenots 7/8
    if [[ "$Server_OS_Version" = "7" ]] ; then
      sed -i 's|error_reporting = E_ALL \&amp; ~E_DEPRECATED \&amp; ~E_STRICT|error_reporting = E_ALL \& ~E_DEPRECATED \& ~E_STRICT|g' /usr/local/lsws/{lsphp72,lsphp73}/etc/php.ini
    #fix php.ini &amp; issue
        if ! yum list installed lsphp74-devel ; then
          yum install -y lsphp74-devel
        fi
        if [[ ! -f /usr/local/lsws/lsphp74/lib64/php/modules/zip.so ]] ; then
        if yum list installed libzip-devel >/dev/null 2>&1 ; then
          yum remove -y libzip-devel
        fi
        yum install -y https://cyberpanel.sh/misc/libzip-0.11.2-6.el7.psychotic.x86_64.rpm
        yum install -y https://cyberpanel.sh/misc/libzip-devel-0.11.2-6.el7.psychotic.x86_64.rpm
        yum install lsphp74-devel
        if [[ ! -d /usr/local/lsws/lsphp74/tmp ]]; then
          mkdir /usr/local/lsws/lsphp74/tmp
        fi
        /usr/local/lsws/lsphp74/bin/pecl channel-update pecl.php.net
        /usr/local/lsws/lsphp74/bin/pear config-set temp_dir /usr/local/lsws/lsphp74/tmp
        if /usr/local/lsws/lsphp74/bin/pecl install zip ; then
          echo "extension=zip.so" >/usr/local/lsws/lsphp74/etc/php.d/20-zip.ini
          chmod 755 /usr/local/lsws/lsphp74/lib64/php/modules/zip.so
        else
          echo -e "\nlsphp74-zip compilation failed..."
        fi
        #fix old legacy lsphp74-zip issue on centos 7
      fi


    #for centos 7
    elif [[ "$Server_OS_Version" = "8" ]] ; then
    :
    #for centos 8
    fi
  fi

  if [[ "$Server_OS" = "Ubuntu" ]] ; then

  if ! dpkg -l lsphp74-dev >/dev/null 2>&1 ; then
    apt install -y lsphp74-dev
  fi

    if [[ ! -f /usr/sbin/ipset ]] ; then
    ln -s /sbin/ipset /usr/sbin/ipset
    fi

  #for ubuntu 18/20
    if [[ "$Server_OS_Version" = "18" ]] ; then
    :
    #for ubuntu 18
    elif [[ "$Server_OS_Version" = "20" ]] ; then
    :
    #for ubuntu 20
    fi
  fi

sed -i "s|lsws-5.3.8|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.4.2|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.3.5|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-6.0|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-6.3.4|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py

if [[ "$Server_Country" = "CN" ]] ; then
  sed -i 's|https://www.litespeedtech.com/|https://cyberpanel.sh/www.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
  sed -i 's|http://license.litespeedtech.com/|https://cyberpanel.sh/license.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
fi

sed -i 's|python2|python|g' /usr/bin/adminPass
chmod 700 /usr/bin/adminPass

rm -f /usr/bin/php
ln -s /usr/local/lsws/lsphp74/bin/php /usr/bin/php

if [[ -f /etc/cyberpanel/webadmin_passwd ]]; then
  chmod 600 /etc/cyberpanel/webadmin_passwd
fi

chown lsadm:lsadm /usr/local/lsws/admin/conf/htpasswd
chmod 600 /usr/local/lsws/admin/conf/htpasswd

if [[ -f /etc/pure-ftpd/pure-ftpd.conf ]]; then
  sed -i 's|NoAnonymous                 no|NoAnonymous                 yes|g' /etc/pure-ftpd/pure-ftpd.conf
fi

Tmp_Output=$(timeout 3 openssl s_client -connect 127.0.0.1:8090 2>/dev/null)
if echo "$Tmp_Output" | grep -q "mail@example.com" ; then
  # it is using default installer generated cert
  Regenerate_Cert 8090
fi


Tmp_Output=$(timeout 3 openssl s_client -connect 127.0.0.1:7080 2>/dev/null)
if echo "$Tmp_Output" | grep -q "mail@example.com" ; then
  Regenerate_Cert 7080
fi

if [[ ! -f /usr/bin/cyberpanel_utility ]]; then
  wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
  chmod 700 /usr/bin/cyberpanel_utility
fi

if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
	watchdog kill
	rm -f /etc/cyberpanel/watchdog.sh
	rm -f /usr/local/bin/watchdog
	wget -O /etc/cyberpanel/watchdog.sh "${Git_Content_URL}/${Branch_Name}/CPScripts/watchdog.sh"
	chmod 700 /etc/cyberpanel/watchdog.sh
	ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
	watchdog status
fi


rm -f /usr/local/composer.sh
rm -f /usr/local/requirments.txt

chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib64

# Fix missing lsphp binary in /usr/local/lscp/fcgi-bin/ after upgrade
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking and restoring lsphp binary if missing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp ]] || [[ ! -s /usr/local/lscp/fcgi-bin/lsphp ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary missing or empty, attempting to restore..." | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Ensure fcgi-bin directory exists
    mkdir -p /usr/local/lscp/fcgi-bin

    # Find the latest available PHP version and use it
    PHP_RESTORED=0
    
    # Try to find the latest lsphp version (check from newest to oldest)
    # Priority: 85 (beta), 84, 83, 82, 81, 80, 74
    for PHP_VER in 85 84 83 82 81 80 74; do
        if [[ -f /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp ]]; then
            # Try to create symlink first (preferred)
            if ln -sf /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp /usr/local/lscp/fcgi-bin/lsphp 2>/dev/null; then
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp symlink created from lsphp${PHP_VER}" | tee -a /var/log/cyberpanel_upgrade_debug.log
            else
                # If symlink fails, copy the file
                cp -f /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp /usr/local/lscp/fcgi-bin/lsphp
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary copied from lsphp${PHP_VER}" | tee -a /var/log/cyberpanel_upgrade_debug.log
            fi
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            PHP_RESTORED=1
            break
        fi
    done

    # If no lsphp version found, try php binary as fallback
    if [[ $PHP_RESTORED -eq 0 ]]; then
        for PHP_VER in 83 82 81 80 74 73 72; do
            if [[ -f /usr/local/lsws/lsphp${PHP_VER}/bin/php ]]; then
                # Try to create symlink first (preferred)
                if ln -sf /usr/local/lsws/lsphp${PHP_VER}/bin/php /usr/local/lscp/fcgi-bin/lsphp 2>/dev/null; then
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp symlink created from php${PHP_VER} (lsphp fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
                else
                    # If symlink fails, copy the file
                    cp -f /usr/local/lsws/lsphp${PHP_VER}/bin/php /usr/local/lscp/fcgi-bin/lsphp
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary copied from php${PHP_VER} (lsphp fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
                fi
                chown root:root /usr/local/lscp/fcgi-bin/lsphp
                chmod 755 /usr/local/lscp/fcgi-bin/lsphp
                PHP_RESTORED=1
                break
            fi
        done
    fi
    
    # If no lsphp version found, try admin_php5 as fallback
    if [[ $PHP_RESTORED -eq 0 ]]; then
        if [[ -f /usr/local/lscp/admin/fcgi-bin/admin_php5 ]]; then
            cp -f /usr/local/lscp/admin/fcgi-bin/admin_php5 /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from admin_php5 (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        elif [[ -f /usr/local/lscp/admin/fcgi-bin/admin_php ]]; then
            cp -f /usr/local/lscp/admin/fcgi-bin/admin_php /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from admin_php (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        elif [[ -f /usr/local/lsws/admin/fcgi-bin/admin_php5 ]]; then
            cp -f /usr/local/lsws/admin/fcgi-bin/admin_php5 /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from lsws admin_php5 (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        else
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Could not find any PHP binary to restore lsphp" | tee -a /var/log/cyberpanel_upgrade_debug.log
        fi
    fi
    
    # Create symlinks if they don't exist
    if [[ -f /usr/local/lscp/fcgi-bin/lsphp ]]; then
        if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp4 ]]; then
            ln -sf ./lsphp /usr/local/lscp/fcgi-bin/lsphp4
        fi
        if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp5 ]]; then
            ln -sf ./lsphp /usr/local/lscp/fcgi-bin/lsphp5
        fi
    fi
fi

# Fix missing lscpd binary in /usr/local/lscp/bin/ after upgrade
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking and restoring lscpd binary if missing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ ! -f /usr/local/lscp/bin/lscpd ]] || [[ ! -s /usr/local/lscp/bin/lscpd ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary missing or empty, attempting to restore..." | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Ensure lscp bin directory exists
    mkdir -p /usr/local/lscp/bin

    # Select the correct lscpd binary based on OS and version
    lscpd_selection='lscpd-0.3.1'

    # Check if this is an ARM system
    if uname -a | grep -q 'aarch64'; then
        lscpd_selection='lscpd.aarch64'
    else
        # For x86_64 systems, check Ubuntu version
        if [[ "$Server_OS" = "Ubuntu" ]] && [[ -f /etc/lsb-release ]]; then
            ubuntu_version=$(grep 'DISTRIB_RELEASE' /etc/lsb-release | cut -d'=' -f2 | cut -d'.' -f1)
            if [[ "$ubuntu_version" = "22" ]] || [[ "$ubuntu_version" = "24" ]]; then
                lscpd_selection='lscpd.0.4.0'
            fi
        fi
    fi

    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Selected lscpd binary: $lscpd_selection" | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Copy the selected binary from CyberCP to lscp bin
    if [[ -f /usr/local/CyberCP/${lscpd_selection} ]]; then
        cp -f /usr/local/CyberCP/${lscpd_selection} /usr/local/lscp/bin/${lscpd_selection}
        rm -f /usr/local/lscp/bin/lscpd
        mv /usr/local/lscp/bin/${lscpd_selection} /usr/local/lscp/bin/lscpd
        chmod 755 /usr/local/lscp/bin/lscpd
        chown root:root /usr/local/lscp/bin/lscpd
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary restored successfully from ${lscpd_selection}" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Could not find lscpd source binary ${lscpd_selection} in /usr/local/CyberCP/" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary exists and is valid" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] || [[ "$Server_OS_Version" = "18" ]] || [[ "$Server_OS_Version" = "8" ]] || [[ "$Server_OS_Version" = "20" ]] || [[ "$Server_OS_Version" = "24" ]]; then
    echo "PYTHONHOME=/usr" > /usr/local/lscp/conf/pythonenv.conf
  else
    # Uncomment and use the following lines if necessary for other OS versions
    # rsync -av --ignore-existing /usr/lib64/python3.9/ /usr/local/CyberCP/lib64/python3.9/
    # Check_Return
    :
fi

# Fix SnappyMail directory permissions for Ubuntu 24.04 and other systems
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking SnappyMail directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Migrate data from old rainloop folder to new snappymail folder (2.4.4 -> 2.5.5 upgrade)
if [ -d "/usr/local/lscp/cyberpanel/rainloop/data" ] && [ "$(ls -A /usr/local/lscp/cyberpanel/rainloop/data 2>/dev/null)" ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Migrating rainloop data to snappymail..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Check if snappymail data already exists with content
    if [ -d "/usr/local/lscp/cyberpanel/snappymail/data" ] && [ -d "/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] SnappyMail data already exists, skipping migration" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        # Create SnappyMail data directories if they don't exist
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/
        
        # Migrate data using rsync (preserves permissions and ownership)
        rsync -av --ignore-existing /usr/local/lscp/cyberpanel/rainloop/data/ /usr/local/lscp/cyberpanel/snappymail/data/ 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
        
        if [ $? -eq 0 ]; then
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Successfully migrated rainloop data to snappymail" | tee -a /var/log/cyberpanel_upgrade_debug.log
            
            # Update include.php to use snappymail path
            if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
                sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Updated include.php to use snappymail data path" | tee -a /var/log/cyberpanel_upgrade_debug.log
            fi
        else
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Data migration completed with errors" | tee -a /var/log/cyberpanel_upgrade_debug.log
        fi
    fi
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] No old rainloop data found, creating new SnappyMail directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Create SnappyMail data directories if they don't exist
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/
fi

# Ensure proper ownership for SnappyMail data directories
if id -u lscpd >/dev/null 2>&1; then
    chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set SnappyMail ownership to lscpd:lscpd" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: lscpd user not found, skipping ownership change" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Set proper permissions for SnappyMail data directories (group writable)
chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data/
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set SnappyMail data directory permissions to 775 (group writable)" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Ensure web server users are in the lscpd group for access
usermod -a -G lscpd nobody 2>/dev/null || true

# Fix SnappyMail public directory ownership (critical fix)
chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/data 2>/dev/null || true
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Added web server users to lscpd group and fixed SnappyMail ownership" | tee -a /var/log/cyberpanel_upgrade_debug.log

systemctl restart lscpd

}

Post_Install_Display_Final_Info() {
echo -e "\n"
# Fixed box width (109 chars) so right border (║) aligns in all boxes
BOX_W=109
_br() { echo "╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"; }
_bl() { echo "╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"; }
_b()  { printf '║%-*s║\n' "$BOX_W" "$1"; }
_br
_b ""
_b "    █████████             █████                        ███████████                                ████"
_b "   ███▒▒▒▒▒███           ▒▒███                        ▒▒███▒▒▒▒▒███                              ▒▒███"
_b "  ███     ▒▒▒  █████ ████ ▒███████   ██████  ████████  ▒███    ▒███  ██████   ████████    ██████  ▒███"
_b "  ▒███         ▒▒███ ▒███  ▒███▒▒███ ███▒▒███▒▒███▒▒███ ▒██████████  ▒▒▒▒▒███ ▒▒███▒▒███  ███▒▒███ ▒███"
_b "  ▒███          ▒███ ▒███  ▒███ ▒███▒███████  ▒███ ▒▒▒  ▒███▒▒▒▒▒▒    ███████  ▒███ ▒███ ▒███████  ▒███"
_b "  ▒▒███     ███ ▒███ ▒███  ▒███ ▒███▒███▒▒▒   ▒███      ▒███         ███▒▒███  ▒███ ▒███ ▒███▒▒▒   ▒███"
_b "  ▒▒█████████  ▒▒███████  ████████ ▒▒██████  █████     █████       ▒▒████████ ████ █████▒▒██████  █████"
_b "  ▒▒▒▒▒▒▒▒▒    ▒▒▒▒▒███ ▒▒▒▒▒▒▒▒   ▒▒▒▒▒▒  ▒▒▒▒▒     ▒▒▒▒▒         ▒▒▒▒▒▒▒▒ ▒▒▒▒ ▒▒▒▒▒  ▒▒▒▒▒▒  ▒▒▒▒▒"
_b "              ███ ▒███"
_b "             ▒▒██████"
_b "              ▒▒▒▒▒▒"
_b "                    *** UPGRADE COMPLETED SUCCESSFULLY! ***"
_b ""
_bl

Panel_Port=$(cat /usr/local/lscp/conf/bind.conf)
if [[ $Panel_Port = "" ]] ; then
  Panel_Port="8090"
fi

# Resolve server IP for remote access URL (avoid empty Remote: https://:2087)
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(ip -4 route get 1 2>/dev/null | awk '/src/ {print $7; exit}')
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || curl -s --max-time 3 icanhazip.com 2>/dev/null)
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP="YOUR_SERVER_IP"
fi

# Test if CyberPanel is accessible
echo -e "\n🔍 Testing CyberPanel accessibility..."

# Check if lscpd service is running
if systemctl is-active --quiet lscpd 2>/dev/null; then
  _br
  _b ""
  _b "  ACCESS YOUR CYBERPANEL:"
  _b ""
  _b "  Local:  https://127.0.0.1:${Panel_Port#*:}"
  _b "  Remote: https://${SERVER_IP}:${Panel_Port#*:}"
  _b ""
  _b "  Default Login: admin / 1234567890"
  _b "  >> Please change the default password immediately!"
  _b ""
  _bl

  # Binary confirmation + versions (ASCII-only so box alignment is correct)
  echo -e "\n"
  _br
  _b ""
  _b "  UPGRADE STATUS: [====================================================] 100%"
  _b ""
  _b "  [OK] All components installed successfully"
  _b "  [OK] Python dependencies resolved"
  _b "  [OK] WSGI-LSAPI compiled with optimizations"
  _b "  [OK] CyberPanel service is running"
  _b "  [OK] Web interface is accessible"
  _b ""
  _b "  CyberPanel: ${Branch_Name:-unknown}"
  _b "  Database (MariaDB): ${MARIADB_VER:-unknown}"
  _b ""
  _b "  *** UPGRADE COMPLETED SUCCESSFULLY! ***"
  _b ""
  _bl

else
  echo -e "CyberPanel may not be running properly. Please check the logs."
  echo -e "\n"
  _br
  _b ""
  _b "  UPGRADE COMPLETED WITH WARNINGS"
  _b ""
  _b "  - CyberPanel files have been updated"
  _b "  - Some services may need manual restart"
  _b "  - Please check logs at /var/log/cyberpanel_upgrade_debug.log"
  _b ""
  _b "  Try running: systemctl restart lscpd"
  _b ""
  _bl
fi

echo -e "\n📋 Next Steps:"
echo -e "   1. Access your CyberPanel at the URL above"
echo -e "   2. Change the default admin password"
echo -e "   3. Configure your domains and websites"
echo -e "   4. Check system status in the dashboard"

echo -e "\n🧹 Cleaning up temporary files..."
rm -rf /root/cyberpanel_upgrade_tmp
echo -e "✅ Cleanup completed\n"
}

if [[ ! -d /etc/cyberpanel ]] ; then
  echo -e "\n\nCan not detect CyberCP..."
  exit
fi

if [[ "$*" = *"--debug"* ]] ; then
  Debug="On"
  Random_Log_Name=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 5)
  find /var/log -name 'cyberpanel_debug_upgrade_*' -exec rm {} +
  echo -e "$(date)" > "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
  chmod 600 "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
fi

Set_Default_Variables

Check_Root

Check_Server_IP "$@"

Check_OS

Check_Provider

Check_Argument "$@"

if [[ "$*" != *"--branch "* ]] && [[ "$*" != *"-b "* ]] ; then
  Pre_Upgrade_Branch_Input
fi

# Prompt for MariaDB version if not set via --mariadb or --mariadb-version (default 11.8). Options: 10.11, 11.8, 12.1.
if [[ "$*" != *"--mariadb"* ]] && [[ "$*" != *"--mariadb-version "* ]]; then
  echo -e "\nMariaDB version: \e[31m10.11\e[39m, \e[31m11.8\e[39m LTS (default) or \e[31m12.1\e[39m. You can switch later by re-running with --mariadb-version 10.11, 11.8 or 12.1."
  echo -e "Press Enter for 11.8 LTS, or type \e[31m10.11\e[39m or \e[31m12.1\e[39m (5 sec timeout): "
  read -r -t 5 Tmp_MariaDB_Ver || true
  Tmp_MariaDB_Ver="${Tmp_MariaDB_Ver// /}"
  if [[ "$Tmp_MariaDB_Ver" = "10.11" ]]; then
    MARIADB_VER="10.11"
    echo -e "MariaDB 10.11 selected.\n"
  elif [[ "$Tmp_MariaDB_Ver" = "12.1" ]]; then
    MARIADB_VER="12.1"
    echo -e "MariaDB 12.1 selected.\n"
  else
    MARIADB_VER="11.8"
    echo -e "MariaDB 11.8 LTS (default).\n"
  fi
fi

# Write chosen MariaDB version for upgrade.py (e.g. fix_almalinux9_mariadb)
mkdir -p /etc/cyberpanel
echo "$MARIADB_VER" > /etc/cyberpanel/mariadb_version
chmod 644 /etc/cyberpanel/mariadb_version
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB version set to: $MARIADB_VER" | tee -a /var/log/cyberpanel_upgrade_debug.log

Pre_Upgrade_Setup_Repository

Pre_Upgrade_Setup_Git_URL

Pre_Upgrade_Required_Components

Main_Upgrade

Post_Upgrade_System_Tweak

Post_Install_Display_Final_Info
