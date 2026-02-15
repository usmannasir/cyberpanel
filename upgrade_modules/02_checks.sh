#!/usr/bin/env bash
# CyberPanel upgrade – root, server IP, OS, provider, and argument checks. Sourced by cyberpanel_upgrade.sh.

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


Skip_System_Update=""
# Migrate MariaDB from latin1 to utf8mb4 after upgrade (only when --migrate-to-utf8 and upgrading to 11.x/12.x)
Migrate_MariaDB_To_UTF8_Requested=""
# MariaDB version: any X.Y or X.Y.Z supported; highlighted: 10.11.16, 11.8 LTS, 12.x (default 11.8)
MARIADB_VER="11.8"
MARIADB_VER_REPO="11.8"

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
# Parse --backup-db / --no-backup-db: pre-upgrade MariaDB backup. Default when neither set: ask user (may take a while).
# --backup-db = always backup; --no-backup-db = never backup; omit both = prompt [y/N]
Backup_DB_Before_Upgrade=""
if [[ "$*" = *"--backup-db"* ]]; then
  Backup_DB_Before_Upgrade="yes"
  echo -e "\nUsing --backup-db: will create a full MariaDB backup before upgrade.\n"
elif [[ "$*" = *"--no-backup-db"* ]]; then
  Backup_DB_Before_Upgrade="no"
  echo -e "\nUsing --no-backup-db: skipping MariaDB pre-upgrade backup.\n"
fi
# Parse --migrate-to-utf8: after upgrading to MariaDB 11.x/12.x, convert DBs/tables from latin1 to utf8mb4 (only if your apps support UTF-8)
if [[ "$*" = *"--migrate-to-utf8"* ]]; then
  Migrate_MariaDB_To_UTF8_Requested="yes"
  echo -e "\nUsing --migrate-to-utf8: will convert databases to UTF-8 (utf8mb4) after MariaDB upgrade.\n"
fi
# Parse --mariadb-version (any version: 10.6, 10.11, 10.11.16, 11.8, 12.1, 12.2, 12.3, etc.). Default 11.8.
# --mariadb is shorthand for --mariadb-version 10.11
if [[ "$*" = *"--mariadb"* ]] && [[ "$*" != *"--mariadb-version "* ]]; then
  MARIADB_VER="10.11"
  echo -e "\nUsing --mariadb: MariaDB 10.11 selected (non-interactive).\n"
elif [[ "$*" = *"--mariadb-version "* ]]; then
  MARIADB_VER=$(echo "$*" | sed -n 's/.*--mariadb-version \([^ ]*\).*/\1/p' | head -1)
  MARIADB_VER="${MARIADB_VER:-11.8}"
fi
# Allow any version; repo paths use major.minor (normalized later)
}

