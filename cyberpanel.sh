#!/bin/bash

#set -e -o pipefail
#set -x
#set -u


#CyberPanel installer script for CentOS 7, CentOS 8, CloudLinux 7, AlmaLinux 8, RockyLinux 8, Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, openEuler 20.03 and openEuler 22.03
#For whoever may edit this script, please follow:
#Please use Pre_Install_xxx() and Post_Install_xxx() if you want to something respectively before or after the panel installation
#and update below accordingly
#Please use variable/functions name as MySomething or My_Something, and please try not to use too-short abbreviation :)
#Please use On/Off,  True/False, Yes/No.

#workflow:
#Set_Default_Variables() --->  set some default variable for later use
#Check_Root()  ---> check for root
#Check_Server_IP()  ---> check for server IP and geolocation at country level
#Check_OS() ---> check system , support on CentOS 7/8, RockyLinux 8, AlmaLinux 8, Ubuntu 18/20, openEuler 20.03/22.03 and CloudLinux 7, 8 is untested.
#Check_Virtualization()  ---> check for virtualizaon , #LXC not supported# , some edit needed on OVZ
#Check_Panel() --->  check to make sure no other panel is installed
#Check_Process() ---> check no other process like Apache is running
#Check_Provider() ---> check the provider, certain provider like Alibaba or Tencent Cloud may need some special change
#Check_Argument() ---> parse argument and go to Argument_Mode() or Interactive_Mode() respectively
#Pre_Install_Setup_Repository() ---> setup/install repositories for CentOS and openEuler system.
#go to Pre_Install_Setup_CN_Repository() if server is within China.
#Pre_Install_Setup_Git_URL() --->  form up github URL , use Gitee for servers within China.
#Pre_Install_Required_Components() --->  install required softwares and git clone it
#Pre_Install_System_Tweak() ---> set up SWAP and apply some system tweak depends on providers
#Main_Installation() --->  change some code within python files for CN servers and start to install
#Post_Install_Addon_Memcached() ---> Install Memcached extension and process
#Post_Install_Addon_Redis() ---> Install Redis extension and process
#Post_Install_Required_Components() --->  install some required softwares.
#Post_Install_PHP_Session_Setup() --->  set up PHP session
#Post_Install_PHP_TimezoneDB() ---> set up PHP timezoneDB
#Post_Install_Regenerate_Cert() ---> regenerate cert for :7080 and :8090 to avoid Chrome on macOS blocking.
#Post_Install_Regenerate_Webadmin_Console_Passwd() ---> regenerate the webadmin console password
#Post_Install_Setup_Watchdog() ---> set up watchdog script for webserver and MariaDB.
#Post_Install_Setup_Utility() --->  set up utility script for some handy features
#Post_Install_Tweak() --->  some patches/fixes on certain systems
#Post_Install_Display_Final_Info() ---> display installation successful information.


Sudo_Test=$(set)
#for SUDO check

Set_Default_Variables() {

echo -e "Fetching latest data from CyberPanel server...\n"
echo -e "This may take few seconds..."

Silent="Off"
Server_Edition="OLS"
Admin_Pass="1234567"

Memcached="Off"
Redis="Off"

Postfix_Switch="On"
PowerDNS_Switch="On"
PureFTPd_Switch="On"

Server_IP=""
Server_Country="Unknow"
Server_OS=""
Server_OS_Version=""
Server_Provider='Undefined'

Watchdog="On"
Redis_Hosting="No"
Temp_Value=$(curl --silent --max-time 30 -4 https://cyberpanel.net/version.txt)
Panel_Version=${Temp_Value:12:3}
Panel_Build=${Temp_Value:25:1}

Branch_Name="v${Panel_Version}.${Panel_Build}"

if [[ $Branch_Name = v*.*.* ]] ; then
  echo -e  "\nBranch name fetched...$Branch_Name"
else
  echo -e "\nUnable to fetch Branch name..."
  echo -e "\nPlease try again in few moments, if this error still happens, please contact support"
  exit
fi

Base_Number="1.9.3"

Total_RAM=$(free -m | awk '/Mem:/ { print $2 }')

Remote_MySQL="Off"

Final_Flags=()

Git_User=""
Git_Content_URL=""
Git_Clone_URL=""

LSWS_Latest_URL="https://cyberpanel.sh/update.litespeedtech.com/ws/latest.php"
LSWS_Tmp=$(curl --silent --max-time 30 -4 "$LSWS_Latest_URL")
LSWS_Stable_Line=$(echo "$LSWS_Tmp" | grep "LSWS_STABLE")
LSWS_Stable_Version=$(expr "$LSWS_Stable_Line" : '.*LSWS_STABLE=\(.*\) BUILD .*')
#grab the LSWS latest stable version.

Enterprise_Flag=""
License_Key=""
Debug_Log2 "Starting installation..,1"

}

Debug_Log() {
echo -e "\n${1}=${2}\n" >> "/var/log/cyberpanel_debug_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
}

Debug_Log2() {
Check_Server_IP "$@" >/dev/null 2>&1
echo -e "\n${1}" >> /var/log/installLogs.txt
curl --max-time 20 -d '{"ipAddress": "'"$Server_IP"'", "InstallCyberPanelStatus": "'"$1"'"}' -H "Content-Type: application/json" -X POST https://cloud.cyberpanel.net/servers/RecvData  >/dev/null 2>&1
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
    echo -e "\nYou must use version number higher than 1.9.4"
    exit
  else
    Branch_Name="v${1//[[:space:]]/}"
    echo -e "\nSet branch name to $Branch_Name..."
  fi
else
  echo -e "\nPlease input a valid format version number."
  exit
fi
}

License_Check() {
License_Key="$1"
echo -e "\nChecking LiteSpeed Enterprise license key..."
if echo "$License_Key" | grep -q "^....-....-....-....$" && [[ ${#License_Key} = "19" ]]; then
  echo -e "\nLicense key set...\n"
elif [[ ${License_Key,,} = "trial" ]] ; then
  echo -e "\nTrial license set..."
  License_Key="Trial"
else
  echo -e "\nLicense key seems incorrect, please verify"
  echo -e "\nIf you are copying/pasting, please make sure you didn't paste blank space...\n"
  exit
fi
}

Check_Return() {
  #check previous command result , 0 = ok ,  non-0 = something wrong.
# shellcheck disable=SC2181
if [[ $? != "0" ]]; then
  if [[ -n "$1" ]] ; then
    echo -e "\n\n\n$1"
  fi
  echo -e  "above command failed..."
  Debug_Log2 "command failed, exiting. For more information read /var/log/installLogs.txt [404]"
  if [[ "$2" = "no_exit" ]] ; then
    echo -e"\nRetrying..."
  else
    exit
  fi
fi
}
# check command success or not

Retry_Command() {
# shellcheck disable=SC2034
for i in {1..50};
do
  if [[ "$i" = "50" ]] ; then
    echo "command $1 failed for 50 times, exit..."
    exit 2
  else
    $1  && break || echo -e "\n$1 has failed for $i times\nWait for 3 seconds and try again...\n"; sleep 3;
  fi
done
}

Check_Root() {
echo -e "\nChecking root privileges..."
  if echo "$Sudo_Test" | grep SUDO >/dev/null; then
    echo -e "\nYou are using SUDO , please run as root user...\n"
    echo -e "\nIf you don't have direct access to root user, please run \e[31msudo su -\e[39m command (do NOT miss the \e[31m-\e[39m at end or it will fail) and then run installation command again."
    exit
  fi

  if [[ $(id -u) != 0 ]] >/dev/null; then
    echo -e "\nYou must run on root user to install CyberPanel...\n"
    echo -e "or run following command: (do NOT miss the quotes)"
    echo -e "\e[31msudo su -c \"sh <(curl https://cyberpanel.sh || wget -O - https://cyberpanel.sh)\"\e[39m"
    exit 1
  else
    echo -e "\nYou are runing as root...\n"
  fi
}

Check_Server_IP() {
Server_IP=$(curl --silent --max-time 30 -4 https://cyberpanel.sh/?ip)
  if [[ $Server_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "Valid IP detected..."
  else
    echo -e "Can not detect IP, exit..."
    Debug_Log2 "Can not detect IP. [404]"
    exit
  fi

echo -e "\nChecking server location...\n"

if [[ "$Server_Country" != "CN" ]] ; then
  Server_Country=$(curl --silent --max-time 10 -4 https://cyberpanel.sh/?country)
  if [[ ${#Server_Country} != "2" ]] ; then
   Server_Country="Unknow"
  fi
fi
#to avoid repeated check_ip called by debug_log2 to break force mirror for CN servers.

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_IP" "$Server_IP"
  Debug_Log "Server_Country" "$Server_Country"
fi

if [[ "$*" = *"--mirror"* ]] ; then
  Server_Country="CN"
  echo -e "Force to use mirror server due to --mirror argument...\n"
fi

if [[ "$Server_Country" = *"CN"* ]] ; then
  Server_Country="CN"
  echo -e "Setting up to use mirror server...\n"
fi
}

Check_OS() {
if [[ ! -f /etc/os-release ]] ; then
  echo -e "Unable to detect the operating system...\n"
  exit
fi

# Reference: https://unix.stackexchange.com/questions/116539/how-to-detect-the-desktop-environment-in-a-bash-script
if [ -z "$XDG_CURRENT_DESKTOP" ]; then
    echo -e "Desktop OS not detected. Proceeding\n"
else
    echo "$XDG_CURRENT_DESKTOP defined appears to be a desktop OS. Bailing as CyberPanel is incompatible."
    echo -e "\nCyberPanel is supported on server OS types only. Such as Ubuntu 18.04 x86_64, Ubuntu 20.04 x86_64, Ubuntu 20.10 x86_64, CentOS 7.x, CentOS 8.x, AlmaLinux 8.x and CloudLinux 7.x...\n"
    exit
fi

if ! uname -m | grep -q x86_64 ; then
  echo -e "x86_64 system is required...\n"
  exit
fi

if grep -q -E "CentOS Linux 7|CentOS Linux 8" /etc/os-release ; then
  Server_OS="CentOS"
elif grep -q "AlmaLinux-8" /etc/os-release ; then
  Server_OS="AlmaLinux"
elif grep -q -E "CloudLinux 7|CloudLinux 8" /etc/os-release ; then
  Server_OS="CloudLinux"
elif grep -q -E "Rocky Linux" /etc/os-release ; then
  Server_OS="RockyLinux"
elif grep -q -E "Ubuntu 18.04|Ubuntu 20.04|Ubuntu 20.10|Ubuntu 22.04" /etc/os-release ; then
  Server_OS="Ubuntu"
elif grep -q -E "openEuler 20.03|openEuler 22.03" /etc/os-release ; then
  Server_OS="openEuler"
else
  echo -e "Unable to detect your system..."
  echo -e "\nCyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03...\n"
  Debug_Log2 "CyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03... [404]"
  exit
fi

Server_OS_Version=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )
#to make 20.04 display as 20, etc.

echo -e "System: $Server_OS $Server_OS_Version detected...\n"

if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]] ; then
  Server_OS="CentOS"
  #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
  #treat CloudLinux, Rocky and Alma as CentOS
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_OS" "$Server_OS $Server_OS_Version"
fi

}

Check_Virtualization() {
echo -e "Checking virtualization type..."
#if hostnamectl | grep -q "Virtualization: lxc"; then
#  echo -e "\nLXC detected..."
#  echo -e "CyberPanel does not support LXC"
#  echo -e "Exiting..."
#  Debug_Log2 "CyberPanel does not support LXC.. [404]"
#  exit
#fi
#remove per https://github.com/usmannasir/cyberpanel/issues/589

if hostnamectl | grep -q "Virtualization: openvz"; then
  echo -e "OpenVZ detected...\n"

  if [[ ! -d /etc/systemd/system/pure-ftpd.service.d ]]; then
    mkdir /etc/systemd/system/pure-ftpd.service.d
    echo "[Service]
PIDFile=/run/pure-ftpd.pid" >/etc/systemd/system/pure-ftpd.service.d/override.conf
    echo -e "PureFTPd service file modified for OpenVZ..."
  fi

  if [[ ! -d /etc/systemd/system/lshttpd.service.d ]]; then
    mkdir /etc/systemd/system/lshttpd.service.d
    echo "[Service]
PIDFile=/tmp/lshttpd/lshttpd.pid" >/etc/systemd/system/lshttpd.service.d/override.conf
    echo -e "LiteSPeed service file modified for OpenVZ..."
  fi

  if [[ ! -d /etc/systemd/system/spamassassin.service.d ]]; then
    mkdir /etc/systemd/system/spamassassin.service.d
    echo "[Service]
PIDFile=/run/spamassassin.pid" >/etc/systemd/system/spamassassin.service.d/override.conf
    echo -e "SpamAssassin service file modified for OpenVZ..."
  fi
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Server_Virtualization" "$(hostnamectl | grep "Virtualization")"
fi
}

Check_Panel() {
if [[ -d /usr/local/cpanel ]]; then
  echo -e "\ncPanel detected...\n"
  Debug_Log2 "cPanel detected...exit... [404]"
  exit
elif [[ -d /usr/local/directadmin ]]; then
  echo -e "\nDirectAdmin detected...\n"
  Debug_Log2 "DirectAdmin detected...exit... [404]"
  exit
elif [[ -d /etc/httpd/conf/plesk.conf.d/ ]] || [[ -d /etc/apache2/plesk.conf.d/ ]]; then
  echo -e "\nPlesk detected...\n"
  Debug_Log2 "Plesk detected...exit... [404]"
  exit
fi
}

Check_Process() {
if systemctl is-active --quiet httpd; then
    systemctl disable httpd
    systemctl stop httpd
    systemctl mask httpd
    echo -e "\nhttpd process detected, disabling...\n"
fi
if systemctl is-active --quiet apache2; then
    systemctl disable apache2
    systemctl stop apache2
    systemctl mask apache2
    echo -e "\napache2 process detected, disabling...\n"
fi
if systemctl is-active --quiet named; then
    systemctl stop named
    systemctl disable named
    systemctl mask named
    echo -e "\nnamed process detected, disabling...\n"
fi
if systemctl is-active --quiet exim; then
    systemctl stop exim
    systemctl disable exim
    systemctl mask exim
    echo -e "\nexim process detected, disabling...\n"
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

Show_Help() {
echo -e "\nCyberPanel Installer Script Help\n"
echo -e "\nUsage: sh <(curl cyberpanel.sh) --argument"
echo -e "\n\e[31m-v\e[39m or \e[31m--version\e[39m : choose to install CyberPanel OpenLiteSpeed or CyberPanel Enterprise, available options are \e[31mols\e[39m , \e[31mTRIAL\e[39m and \e[31mSERIAL_NUMBER\e[39m, default ols"
echo -e "Please be aware, this serial number must be obtained from LiteSpeed Store."
echo -e "And if this serial number has been used before, it must be released/migrated in Store first, otherwise it will fail to start."
echo -e "\n\e[31m-a\e[39m or \e[31m--addons\e[39m : install addons: memcached, redis, PHP extension for memcached and redis"
echo -e "\n\e[31m-p\e[39m or \e[31m--password\e[39m : set password of new installation, empty for default 1234567, [r] or [random] for randomly generated 16 digital password, any other value besides [d] and [r(andom)] will be accept as password, default use 1234567."
echo -e "e.g. \e[31m-p r\e[39m will generate a random password"
echo -e "     \e[31m-p 123456789\e[39m will set password to 123456789"
echo -e "\n\e[31m-m\e[39m or \e[31m--minimal\e[39m : set to minimal mode which will not install PowerDNS, Pure-FTPd and Postfix"
echo -e "\n\e[31m-m postfix/pureftpd/powerdns\e[39m will do minimal install also with compoenent given"
echo -e "e.g.  \e[31m-m postfix\e[39m will do minimal install also with Postfix"
echo -e "      \e[31m-m powerdns\e[39m will do minimal install also with PowerDNS"
echo -e "      \e[31m-m postfix\e[39m powerdns will do minimal install also with Postfix and PowerDNS"
echo -e "\n\e[31m-b\e[39m or \e[31m--branch\e[39m : install with given branch/version , must be higher than 1.9.4"
echo -e "e.g.  \e[31m-b 2.0.2\e[39m will install 2.0.2 version"
echo -e "\n\e[31m--mirror\e[39m : this argument force to use mirror server for majority of repositories, only suggest to use for servers within China"
echo -e "\nExample:"
echo -e "\nsh <(curl cyberpanel.sh) -v ols -p r or ./cyberpanel.sh --version ols --password random"
echo -e "\nThis will install CyberPanel OpenLiteSpeed and randomly generate the password."
echo -e "\nsh <(curl cyberpanel.sh) -v LICENSE_KEY -a -p my_pass_word"
echo -e "\nThis will install LiteSpeed Enterise , replace LICENSE_KEY to actual license key and set password to my_pass_word\n"
}

Check_Argument() {
if  [[ "$#" = "0" ]] || [[ "$#" = "1" && "$1" = "--debug" ]] || [[ "$#" = "1" && "$1" = "--mirror" ]]; then
  echo -e "\nInitialized...\n"
else
  if [[ $1 = "help" ]]; then
    Show_Help
    exit
  elif [[ $1 = "default" ]]; then
    echo -e "\nThis will start default installation...\n"
    Silent="On"
    Postfix_Switch="On"
    PowerDNS_Switch="On"
    PureFTPd_Switch="On"
    Server_Edition="OLS"
    Admin_Pass="1234567"
    Memcached="On"
    Redis="On"
  else
    while [[ -n "${1}" ]]; do
      case $1 in
      -v | --version)
      shift
      if [[ "${1}" = "" ]]; then
        Show_Help
        exit
      elif [[ "${1^^}" = "OLS" ]] ; then
        Server_Edition="OLS"
        Silent="On"
        echo -e "\nSet to use OpenLiteSpeed..."
      else
        Server_Edition="Enterprise"
        License_Key="${1}"
        Silent="On"
        echo -e "\nSet to use LiteSpeed Enterprise..."
        echo -e "\nSet to use license key ${1}..."
      fi
      ;;
      -p | --password)
      shift
      if [[ ${1} = "" ]]; then
        Admin_Pass="1234567"
      elif [[ ${1} = "r" ]] || [[ $1 = "random" ]]; then
        Admin_Pass=$(
        head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16
        echo ''
        )
      elif [[ ${1} = "d" ]]; then
        Admin_Pass="1234567"
      else
        if [[ ${#1} -lt 8 ]]; then
          echo -e "\nPassword length less than 8 digital, please choose a more complicated password.\n"
          exit
        fi
        Admin_Pass="${1}"
      fi
      echo -e "\nSet to use password ${1}..."
      ;;
      -b | --branch)
      shift
        Branch_Check "${1}"
      ;;
      -m | --minimal)
      if ! echo "$@" | grep -q -i "postfix\|pureftpd\|powerdns" ; then
        Postfix_Switch="Off"
        PowerDNS_Switch="Off"
        PureFTPd_Switch="Off"
        echo -e "\nSet to use minimal installation..."
      else
          if [[ "${*^^}" = *"POSTFIX"* ]] ; then
            Postfix_Switch="On"
            echo -e "\nEnable Postfix..."
          fi
          if [[ "${*^^}" = *"PUREFTPD"* ]] ; then
            PureFTPd_Switch="On"
            echo -e "\nEnable PureFTPd..."
          fi
          if [[ "${*^^}" = *"POWERDNS"* ]] ; then
            PowerDNS_Switch="On"
            echo -e "\nEnable PowerDNS..."
          fi
      fi
      ;;
      -a | --addons)
        Memcached="On"
        Redis="On"
        echo -e "\nEnable Addons..."
      ;;
      -h | --help)
        Show_Help
        exit
      ;;
      --debug)
        echo -e "\nEnable Debug log...\n"
      ;;
      --mirror)
        echo -e "\nForce to use mirror server...\n"
      ;;
      *)
        if [[ "${1^^}" = *"POSTFIX"* ]] || [[ "${1^^}" = *"PUREFTPD"* ]] || [[ "${1^^}" = *"POWERDNS"* ]] ; then
          :
        #this is ugly workaround , leave it for now , to-do for further improvement.
        else
          echo -e "\nUnknown argument...\n"
          Show_Help
          exit
        fi
      ;;
    esac
    shift
    done
  fi
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Arguments" "${@}"
fi

Debug_Log2 "Initialization completed..,2"
}

Argument_Mode() {
if [[ "${Server_Edition^^}" = "OLS" ]] ; then
  Server_Edition="OLS"
  echo -e "\nSet to OpenLiteSpeed..."
else
  License_Check "$License_Key"
fi

if [[ $Admin_Pass = "d" ]]; then
  Admin_Pass="1234567"
  echo -e "\nSet to default password..."
  echo -e "\nAdmin password will be set to \e[31m$Admin_Pass\e[39m\n"
elif [[ $Admin_Pass = "r" ]]; then
  Admin_Pass=$(
  head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16
  echo ''
  )
  echo -e "\nSet to random-generated password..."
  echo -e "\nAdmin password will be set to \e[31m$Admin_Pass\e[39m"
else
  echo -e "\nAdmin password will be set to \e[31m$Admin_Pass\e[39m"
fi
}

Interactive_Mode() {
echo -e "		CyberPanel Installer v$Panel_Version.$Panel_Build

1. Install CyberPanel.

2. Exit.

"
read -r -p "  Please enter the number[1-2]: " Input_Number
echo ""
case "$Input_Number" in
  1)
  Interactive_Mode_Set_Parameter
  ;;
  2)
  exit
  ;;
  *)
  echo -e "  Please enter the right number [1-2]\n"
  exit
  ;;
esac
}


Interactive_Mode_Set_Parameter() {
echo -e "		CyberPanel Installer v$Panel_Version.$Panel_Build

RAM check : $(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')

Disk check : $(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}') (Minimal \e[31m10GB\e[39m free space)

1. Install CyberPanel with \e[31mOpenLiteSpeed\e[39m.

2. Install Cyberpanel with \e[31mLiteSpeed Enterprise\e[39m.

3. Exit.

"
read -r -p "  Please enter the number[1-3]: " Input_Number
echo ""
case "$Input_Number" in
  1)
  Server_Edition="OLS"
  ;;
  2)
  Interactive_Mode_License_Input
  ;;
  3)
  exit
  ;;
  *)
  echo -e "  Please enter the right number [1-3]\n"
  exit
  ;;
esac

echo -e "\nInstall Full service for CyberPanel? This will include PowerDNS, Postfix and Pure-FTPd."
echo -e ""
printf "%s" "Full installation [Y/n]: "
read -r Tmp_Input
if [[ $(expr "x$Tmp_Input" : 'x[Yy]') -gt 1 ]] || [[ $Tmp_Input = "" ]]; then
  echo -e "\nFull installation selected..."
  Postfix_Switch="On"
  PowerDNS_Switch="On"
  PureFTPd_Switch="On"
else
  echo -e ""
  printf "%s" "Install Postfix? [Y/n]: "
  read -r Tmp_Input
    if [[ $Tmp_Input =~ ^(no|n|N) ]]; then
      Postfix_Switch="Off"
    else
      Postfix_Switch="On"
    fi
  echo -e ""
  printf "%s" "Install PowerDNS? [Y/n]: "
  read -r Tmp_Input
    if [[ $Tmp_Input =~ ^(no|n|N) ]]; then
      PowerDNS_Switch="Off"
    else
      PowerDNS_Switch="On"
    fi
  echo -e ""
  printf "%s" "Install PureFTPd? [Y/n]: "
  read -r Tmp_Input
    if [[ $Tmp_Input =~ ^(no|n|N) ]]; then
      PureFTPd_Switch="Off"
    else
      PureFTPd_Switch="On"
    fi
fi

  ### Ask if you want to set up this CyberPanel with remote MySQL

echo -e "\nDo you want to setup Remote MySQL? (This will skip installation of local MySQL)"
echo -e ""
printf "%s" "(Default = No) Remote MySQL [y/N]: "
read -r Tmp_Input
if [[ $(expr "x$Tmp_Input" : 'x[Yy]') -gt 1 ]]; then
  echo -e "\nRemote MySQL selected..."
  Remote_MySQL="On"

  echo -e ""
  printf "%s" "Remote MySQL Hostname: "
  read -r MySQL_Host

  echo -e ""
  printf "%s" "Remote MySQL Database that contains meta information regarding MYSQL. (usually mysql): "
  read -r MySQL_DB

  echo -e ""
  printf "%s" "Remote MySQL Username:  "
  read -r MySQL_User

  echo -e ""
  printf "%s" "Remote MySQL Password:  "
  read -r -s -p "Password: " MySQL_Password

  echo -e ""
  printf "%s" "Remote MySQL Port:  "
  read -r MySQL_Port
else
  echo -e "\nLocal MySQL selected..."
fi

echo -e "\nPress \e[31mEnter\e[39m key to continue with latest version or Enter specific version such as: \e[31m1.9.4\e[39m , \e[31m2.0.1\e[39m , \e[31m2.0.2\e[39m ...etc"
printf "%s" ""
read -r Tmp_Input

if [[ $Tmp_Input = "" ]]; then
  echo -e "Branch name set to $Branch_Name"
else
  Branch_Check "$Tmp_Input"
fi

echo -e "\nPlease choose to use default admin password \e[31m1234567\e[39m, randomly generate one \e[31m(recommended)\e[39m or specify the admin password?"
printf "%s" "Choose [d]fault, [r]andom or [s]et password: [d/r/s] "
read -r Tmp_Input

if [[ $Tmp_Input =~ ^(d|D| ) ]] || [[ -z $Tmp_Input ]]; then
  Admin_Pass="1234567"
  echo -e "\nAdmin password will be set to $Admin_Pass\n"
elif [[ $Tmp_Input =~ ^(r|R) ]]; then
  Admin_Pass=$(
    head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16
    echo ''
    )
  echo -e "\nAdmin password will be provided once installation is completed...\n"
elif [[ $Tmp_Input =~ ^(s|S) ]]; then
  Custom_Pass="True"
  echo -e "\nPlease enter your password:"
  printf "%s" ""
  read -r -s -p "Password: " Tmp_Input
  if [[ -z "$Tmp_Input" ]]; then
    echo -e "\nPlease do not use empty string...\n"
    exit
  fi
  if [[ ${#Tmp_Input} -lt 8 ]]; then
    echo -e "\nPassword length less than 8 digital, please choose a more complicated password.\n"
    exit
  fi
  Tmp_Input1=$Tmp_Input
  read -r -s -p "Confirm Password:" Tmp_Input
  if [[ -z "$Tmp_Input" ]]; then
    echo -e "\nPlease do not use empty string...\n"
    exit
  fi
  if [[ "$Tmp_Input" = "$Tmp_Input1" ]]; then
    Admin_Pass=$Tmp_Input
  else
    echo -e "\nRepeated password didn't match , please check...\n"
    exit
  fi
else
  Admin_Pass="1234567"
  echo -e "\nAdmin password will be set to $Admin_Pass\n"
fi

echo -e "\nDo you wish to install Memcached process and its PHP extension?"
printf "%s" "Please select [Y/n]: "
read -r Tmp_Input
if [[ $Tmp_Input =~ ^(no|n|N) ]]; then
  Memcached="Off"
else
  Memcached="On"
  echo -e "\nInstall Memcached process and its PHP extension set to Yes...\n"
fi

echo -e "\nDo you wish to install Redis process and its PHP extension?"
printf "%s" "Please select [Y/n]: "
read -r Tmp_Input
if [[ $Tmp_Input =~ ^(no|n|N) ]]; then
  Redis="Off"
else
  Redis="On"
  echo -e "\nInstall Redis process and its PHP extension set to Yes...\n"
fi

echo -e "\nWould you like to set up a WatchDog \e[31m(beta)\e[39m for Web service and Database service ?"
echo -e "The watchdog script will be automatically started up after installation and server reboot"
echo -e "If you want to kill the watchdog , run \e[31mwatchdog kill\e[39m"
echo -e "Please type Yes or no (with capital \e[31mY\e[39m, default Yes): "
read -r Tmp_Input
if [[ $Tmp_Input = "Yes" ]] || [[ $Tmp_Input = "" ]]; then
  Watchdog="On"
  echo -e "\nInstall Watchdog set to Yes...\n"
else
  Watchdog="Off"
fi
}

Interactive_Mode_License_Input() {
Server_Edition="Enterprise"
echo -e "\nPlease note that your server has \e[31m$Total_RAM MB\e[39m RAM"
echo -e "REMINDER: The \e[31mFree Start\e[39m license requires \e[31m2GB or less\e[39m of RAM and the \e[31mSite Owner\e[39m and \e[31mWeb Host Lite\e[39m licenses require \e[31m8GB or less\e[39m.\n"
echo -e "If you do not have any license, you can also use trial license (if server has not used trial license before), type \e[31mTRIAL\e[39m\n"

printf "%s" "Please input your serial number for LiteSpeed WebServer Enterprise: "
read -r License_Key
if [[ -z "$License_Key" ]]; then
  echo -e "\nPlease provide license key\n"
  exit
fi

echo -e "The serial number you input is: \e[31m$License_Key\e[39m\n"
printf "%s" "Please verify it is correct. [y/N]: "
read -r Tmp_Input
if [[ -z "$Tmp_Input" ]]; then
  echo -e "\nPlease type \e[31my\e[39m\n"
  exit
fi

License_Check "$License_Key"

#echo -e "\nWould you like use Redis Mass Hosting?"
#echo -e "Please type Yes or No (with capital \e[31mY\e[39m, default No):"
#read -r Redis_Hosting

#if [[ "$Redis_Hosting" = "Yes" ]]; then
#  echo -e "\nRedis Mass Hosting is set to Yes...\n"
#fi
#  hide it for now
}

Pre_Install_Setup_Repository() {
if [[ $Server_OS = "CentOS" ]] ; then
  rpm --import https://cyberpanel.sh/rpms.litespeedtech.com/centos/RPM-GPG-KEY-litespeed
  #import the LiteSpeed GPG key

  yum clean all
  yum autoremove -y epel-release
  rm -f /etc/yum.repos.d/epel.repo
  rm -f /etc/yum.repos.d/epel.repo.rpmsave

  if [[ "$Server_OS_Version" = "8" ]]; then
    rpm --import https://cyberpanel.sh/www.centos.org/keys/RPM-GPG-KEY-CentOS-Official
    rpm --import https://cyberpanel.sh/dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-8
    yum install -y https://cyberpanel.sh/dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
      Check_Return "yum repo" "no_exit"

    sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-* > /dev/null 2>&1
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-* > /dev/null 2>&1
    # ref: https://stackoverflow.com/questions/70926799/centos-through-vm-no-urls-in-mirrorlist

    dnf config-manager --set-enabled PowerTools > /dev/null 2>&1
    dnf config-manager --set-enabled powertools > /dev/null 2>&1
  
#    cat <<EOF >/etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo
#[powertools-for-cyberpanel]
#name=CentOS Linux \$releasever - PowerTools
#mirrorlist=http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=PowerTools&infra=\$infra
#baseurl=http://mirror.centos.org/\$contentdir/\$releasever/PowerTools/\$basearch/os/
#gpgcheck=1
#enabled=1
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
#EOF
  fi

  if [[ "$Server_OS_Version" = "7" ]]; then
    rpm --import https://cyberpanel.sh/dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7
    yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
      Check_Return "yum repo" "no_exit"

    yum install -y yum-plugin-copr
      Check_Return "yum repo" "no_exit"
    yum copr enable -y copart/restic
      Check_Return "yum repo" "no_exit"
    yum install -y yum-plugin-priorities
      Check_Return "yum repo" "no_exit"
    curl -o /etc/yum.repos.d/powerdns-auth-43.repo https://cyberpanel.sh/repo.powerdns.com/repo-files/centos-auth-43.repo
      Check_Return "yum repo" "no_exit"

    cat <<EOF >/etc/yum.repos.d/MariaDB.repo
# MariaDB 10.4 CentOS repository list - created 2021-08-06 02:01 UTC
# http://downloads.mariadb.org/mariadb/repositories/
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.4/centos7-amd64
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF

    yum install --nogpg -y https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el7.noarch.rpm
      Check_Return "yum repo" "no_exit"

    rpm -ivh https://cyberpanel.sh/repo.iotti.biz/CentOS/7/noarch/lux-release-7-1.noarch.rpm
      Check_Return "yum repo" "no_exit"

    rpm -ivh https://cyberpanel.sh/repo.ius.io/ius-release-el7.rpm
      Check_Return "yum repo" "no_exit"
  fi
fi

if [[ $Server_OS = "openEuler" ]]; then
  rpm --import https://cyberpanel.sh/rpms.litespeedtech.com/centos/RPM-GPG-KEY-litespeed
  #import the LiteSpeed GPG key
  yum clean all
  sed -i "s|gpgcheck=1|gpgcheck=0|g" /etc/yum.repos.d/openEuler.repo
  sed -i "s|repo.openeuler.org|mirror.efaith.com.hk/openeuler|g" /etc/yum.repos.d/openEuler.repo

  if [[ "$Server_OS_Version" = "20" ]]; then
    dnf install --nogpg -y https://repo.yaro.ee/yaro-release-20.03LTS-latest.oe1.noarch.rpm
      Check_Return "yum repo" "no_exit"
  fi

  if [[ "$Server_OS_Version" = "22" ]]; then
    dnf install --nogpg -y https://repo.yaro.ee/yaro-release-22.03LTS-latest.oe2203.noarch.rpm
      Check_Return "yum repo" "no_exit"
  fi
fi

Debug_Log2 "Setting up repositories...,1"

if [[ "$Server_Country" = "CN" ]] ; then
  Pre_Install_Setup_CN_Repository
  Debug_Log2 "Setting up repositories for CN server...,1"
fi

if [[ "$Server_Country" = "CN" ]] || [[ "$Server_Provider" = "Alibaba Cloud" ]] || [[ "$Server_Provider" = "Tencent Cloud" ]]; then
  Setup_Pip
fi

}

Setup_Pip() {

rm -rf /root/.pip
mkdir -p /root/.pip
cat <<EOF >/root/.pip/pip.conf
[global]
index-url=https://cyberpanel.sh/pip-repo/pypi/simple/
EOF
#default to self-host pip for CN

if [[ "$Server_Provider" = "Alibaba Cloud" ]] ; then
sed -i 's|https://cyberpanel.sh/pip-repo/pypi/simple/|http://mirrors.cloud.aliyuncs.com/pypi/simple/|g' /root/.pip/pip.conf
echo "trusted-host = mirrors.cloud.aliyuncs.com" >> /root/.pip/pip.conf
fi

if [[ "$Server_Provider" = "Tencent Cloud" ]] ; then
sed -i 's|https://cyberpanel.sh/pip-repo/pypi/simple/|https://mirrors.cloud.tencent.com/pypi/simple/|g' /root/.pip/pip.conf
fi
#set Alibaba and Tencent to their private mirror


Debug_Log2 "Setting up PIP repo...,3"
#set up pip for Alibaba, Tencent worldwide and Chinese server

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Pip Source" "$(grep "index-url" /root/.pip/pip.conf)"
fi
}

Pre_Install_Setup_CN_Repository() {
if [[ "$Server_OS" = "CentOS" ]] && [[ "$Server_OS_Version" = "7" ]]; then

  sed -i 's|http://yum.mariadb.org|https://cyberpanel.sh/yum.mariadb.org|g' /etc/yum.repos.d/MariaDB.repo
  sed -i 's|https://yum.mariadb.org/RPM-GPG-KEY-MariaDB|https://cyberpanel.sh/yum.mariadb.org/RPM-GPG-KEY-MariaDB|g' /etc/yum.repos.d/MariaDB.repo
  # use MariaDB Mirror

  sed -i 's|https://download.copr.fedorainfracloud.org|https://cyberpanel.sh/download.copr.fedorainfracloud.org|g' /etc/yum.repos.d/_copr_copart-restic.repo

  sed -i 's|http://repo.iotti.biz|https://cyberpanel.sh/repo.iotti.biz|g' /etc/yum.repos.d/frank.repo

  sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/7/gf/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/7/gf/x86_64/|g" /etc/yum.repos.d/gf.repo
  sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/7/plus/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64/|g" /etc/yum.repos.d/gf.repo

  sed -i 's|https://repo.ius.io|https://cyberpanel.sh/repo.ius.io|g' /etc/yum.repos.d/ius.repo

  sed -i 's|http://repo.iotti.biz|https://cyberpanel.sh/repo.iotti.biz|g' /etc/yum.repos.d/lux.repo

  sed -i 's|http://repo.powerdns.com|https://cyberpanel.sh/repo.powerdns.com|g' /etc/yum.repos.d/powerdns-auth-43.repo
  sed -i 's|https://repo.powerdns.com|https://cyberpanel.sh/repo.powerdns.com|g' /etc/yum.repos.d/powerdns-auth-43.repo
fi
#  sed -i 's|http://mirrors.tencentyun.com/ubuntu/|https://cyberpanel.sh/us.archive.ubuntu.com/ubuntu/|g' /etc/apt/sources.list

Debug_Log2 "Setting up repositories for CN server...,1"
}

Download_Requirement() {
for i in {1..50} ;
  do
  wget -O /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments.txt"
  if grep -q "Django==" /usr/local/requirments.txt ; then
    break
  else
    echo -e "\n Requirement list has failed to download for $i times..."
    echo -e "Wait for 30 seconds and try again...\n"
    sleep 30
  fi
done
#special made function for Gitee.com , for whatever reason , sometimes it fails to download this file
}

Pre_Install_Required_Components() {

Debug_Log2 "Installing necessary components..,3"

if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "openEuler" ]] ; then
  yum update -y
  if [[ "$Server_OS_Version" = "7" ]] ; then
    yum install -y wget strace net-tools curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel gpgme-devel curl-devel git socat openssl-devel MariaDB-shared mariadb-devel yum-utils python36u python36u-pip python36u-devel zip unzip bind-utils
      Check_Return
    yum -y groupinstall development
      Check_Return
  elif [[ "$Server_OS_Version" = "8" ]] ; then
    dnf install -y libnsl zip wget strace net-tools curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git platform-python-devel tar socat python3 zip unzip bind-utils
      Check_Return
    dnf install -y gpgme-devel
      Check_Return
  elif [[ "$Server_OS_Version" = "20" ]] || [[ "$Server_OS_Version" = "22" ]] ; then
    dnf install -y libnsl zip wget strace net-tools curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git python3-devel tar socat python3 zip unzip bind-utils
      Check_Return
    dnf install -y gpgme-devel
      Check_Return
  fi
  ln -s /usr/bin/pip3 /usr/bin/pip
else
  apt update -y
  DEBIAN_FRONTEND=noninteractive apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
	if [[ "$Server_Provider" = "Alibaba Cloud" ]] ; then
    apt install -y --allow-downgrades libgnutls30=3.6.13-2ubuntu1.3
  fi

  if [[ "$Server_OS_Version" = "22" ]] ; then
    DEBIAN_FRONTEND=noninteractive apt install -y dnsutils net-tools htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git socat vim unzip zip libmariadb-dev-compat libmariadb-dev
     Check_Return
  else
    DEBIAN_FRONTEND=noninteractive apt install -y dnsutils net-tools htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadbclient-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git socat vim unzip zip
     Check_Return
  fi

  DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
    Check_Return

  ln -s /usr/bin/pip3 /usr/bin/pip3.6
  ln -s /usr/bin/pip3.6 /usr/bin/pip

  DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
    Check_Return
  DEBIAN_FRONTEND=noninteractive apt install -y python3-venv
    Check_Return

  DEBIAN_FRONTEND=noninteractive apt install -y locales
  locale-gen "en_US.UTF-8"
  update-locale LC_ALL="en_US.UTF-8"
fi

Debug_Log2 "Installing required virtual environment,3"

export LC_CTYPE=en_US.UTF-8
export LC_ALL=en_US.UTF-8
#need to set lang to address some pip module installation issue.

Retry_Command "pip install --default-timeout=3600 virtualenv==16.7.9"

Download_Requirement

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]] ; then
python3 -m venv /usr/local/CyberPanel
Check_Return
else
virtualenv -p /usr/bin/python3 /usr/local/CyberPanel
  Check_Return
fi

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" != "20" ]] ; then
  # shellcheck disable=SC1091
  source /usr/local/CyberPanel/bin/activate
else
  # shellcheck disable=SC1091
  . /usr/local/CyberPanel/bin/activate
fi

Debug_Log2 "Installing requirments..,3"

Retry_Command "pip install --default-timeout=3600 -r /usr/local/requirments.txt"
  Check_Return "requirments" "no_exit"

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]] ; then
  cp /usr/bin/python3.10 /usr/local/CyberCP/bin/python3
fi

rm -rf cyberpanel
echo -e "\nFetching files from ${Git_Clone_URL}...\n"

Debug_Log2 "Getting CyberPanel code..,4"

Retry_Command "git clone ${Git_Clone_URL}"
  Check_Return "git clone ${Git_Clone_URL}"

echo -e "\nCyberPanel source code downloaded...\n"

cd cyberpanel || exit
git checkout "$Branch_Name"
  Check_Return "git checkout"
cd - || exit
cp -r cyberpanel /usr/local/cyberpanel
cd cyberpanel/install || exit

Debug_Log2 "Necessary components installed..,5"
}

Pre_Install_System_Tweak() {
Debug_Log2 "Setting up system tweak...,20"
Line_Number=$(grep -n "127.0.0.1" /etc/hosts | cut -d: -f 1)
My_Hostname=$(hostname)

if [[ -n $Line_Number ]]; then
  for Line_Number2 in $Line_Number ; do
    String=$(sed "${Line_Number2}q;d" /etc/hosts)
    if [[ $String != *"$My_Hostname"* ]]; then
      New_String="$String $My_Hostname"
      sed -i "${Line_Number2}s/.*/${New_String}/" /etc/hosts
    fi
  done
else
  echo "127.0.0.1 $My_Hostname " >>/etc/hosts
fi
  #this should address on "sudo: unable to resolve host ..." on Ubuntu , it's not issue but annoying.

if [[ "$Server_OS" = "CentOS" ]] ; then
  setenforce 0 || true
  sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
  #disable SELinux

    if [[ "$Server_OS_Version" = "7" ]] ; then
    :
    fi
    #CentOS 7 specific change
    if [[ "$Server_OS_Version" = "8" ]] ; then
	      if grep -q -E "Rocky Linux" /etc/os-release ; then
        if [[ "$Server_Country" = "CN" ]] ; then
          sed -i 's|rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo|g' install.py
        else
          sed -i 's|rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed.repo|g' install.py
        fi
      fi
    fi
    #CentOS 8 specific change

elif  [[ "$Server_OS" = "Ubuntu" ]] ; then
    if [[ "$Server_OS_Version" = "20" ]] ; then
    sed -i 's|ce-2.3-latest/ubuntu/bionic bionic main|ce-2.3-latest/ubuntu/focal focal main|g' install.py
    fi
    #Ubuntu 20 specific change.

    if [[ "$Server_OS_Version" = "18" ]] ; then
    :
    fi
    #Ubuntu 18 specific change.
fi

if ! grep -q "pid_max" /etc/rc.local 2>/dev/null ; then
  if [[ $Server_OS = "CentOS" ]] || [[ $Server_OS = "openEuler" ]] ; then
    echo "echo 1000000 > /proc/sys/kernel/pid_max
    echo 1 > /sys/kernel/mm/ksm/run" >>/etc/rc.d/rc.local
    chmod +x /etc/rc.d/rc.local
  else
    if [[ -f /etc/rc.local ]] ; then 
      echo -e "#!/bin/bash\n$(cat /etc/rc.local)" > /etc/rc.local
    else 
      echo "#!/bin/bash" > /etc/rc.local
    fi 
    echo "echo 1000000 > /proc/sys/kernel/pid_max
    echo 1 > /sys/kernel/mm/ksm/run" >>/etc/rc.local
    chmod +x /etc/rc.local
    systemctl enable rc-local  >/dev/null 2>&1
    systemctl start rc-local  >/dev/null 2>&1
  fi
	if grep -q "nf_conntrack_max" /etc/sysctl.conf ; then
    sysctl -w net.netfilter.nf_conntrack_max=2097152 > /dev/null
    sysctl -w net.nf_conntrack_max=2097152 > /dev/null
    echo "net.netfilter.nf_conntrack_max=2097152" >> /etc/sysctl.conf
    echo "net.nf_conntrack_max=2097152" >> /etc/sysctl.conf
  fi
    echo "fs.file-max = 65535" >>/etc/sysctl.conf
    sysctl -p >/dev/null
    echo "*                soft    nofile          65535
  *                hard    nofile          65535
  root             soft    nofile          65535
  root             hard    nofile          65535
  *                soft    nproc           65535
  *                hard    nproc           65535
  root             soft    nproc           65535
  root             hard    nproc           65535" >>/etc/security/limits.conf
  fi
  #sed -i 's|#DefaultLimitNOFILE=|DefaultLimitNOFILE=65535|g' /etc/systemd/system.conf
  #raise the file limit for systemd process

  Total_SWAP=$(free -m | awk '/^Swap:/ { print $2 }')
  Set_SWAP=$((Total_RAM - Total_SWAP))
  SWAP_File=/cyberpanel.swap

  if [ ! -f $SWAP_File ]; then
    if [[ $Total_SWAP -gt $Total_RAM ]] || [[ $Total_SWAP -eq $Total_RAM ]]; then
      echo -e "Check SWAP...\n"
    else
      if [[ $Set_SWAP -gt "2049" ]]; then
        #limit it to 2GB as max size
        Set_SWAP="2048"
      fi
      fallocate --length ${Set_SWAP}MiB $SWAP_File
      chmod 600 $SWAP_File
      mkswap $SWAP_File
      swapon $SWAP_File
      echo -e "${SWAP_File} swap swap sw 0 0" | sudo tee -a /etc/fstab
      sysctl vm.swappiness=10
      echo -e "vm.swappiness = 10" >> /etc/sysctl.conf
      echo -e "\nSWAP set...\n"
    fi
  fi

  if [[ "$Server_Provider" = "Tencent Cloud" ]] ; then
    echo "$(host mirrors.tencentyun.com | awk '{print $4}') mirrors.tencentyun.com " >> /etc/hosts
  fi
  if [[ "$Server_Provider" = "Alibaba Cloud" ]] ; then
    echo "$(host mirrors.cloud.aliyuncs.com | awk '{print $4}') mirrors.cloud.aliyuncs.com " >> /etc/hosts
  fi
  #add internal repo server to host file before systemd-resolved is disabled

  if grep -i -q "systemd-resolve" /etc/resolv.conf ; then
    systemctl stop systemd-resolved  >/dev/null 2>&1
    systemctl disable systemd-resolved  >/dev/null 2>&1
    systemctl mask systemd-resolved  >/dev/null 2>&1
  fi

  # Backup previous resolv.conf file
  cp /etc/resolv.conf /etc/resolv.conf_bak

  # Delete resolv.conf file
  rm -f /etc/resolv.conf

  if [[ "$Server_Provider" = "Tencent Cloud" ]] ; then
    echo -e "nameserver 183.60.83.19" > /etc/resolv.conf
    echo -e "nameserver 183.60.82.98" >> /etc/resolv.conf
  elif [[ "$Server_Provider" = "Alibaba Cloud" ]] ; then
    echo -e "nameserver 100.100.2.136" > /etc/resolv.conf
    echo -e "nameserver 100.100.2.138" >> /etc/resolv.conf
  else
    echo -e "nameserver 1.1.1.1" > /etc/resolv.conf
    echo -e "nameserver 8.8.8.8" >> /etc/resolv.conf
  fi

  systemctl restart systemd-networkd >/dev/null 2>&1
  sleep 3
  #take a break ,or installer will break

  # Check Connectivity
  if ping -q -c 1 -W 1 cyberpanel.sh >/dev/null; then
    echo -e "\nSuccessfully set up nameservers..\n"
    echo -e "\nThe network is up.. :)\n"
    echo -e "\nContinue installation..\n"
  else
    echo -e "\nThe network is down.. :(\n"
    rm -f /etc/resolv.conf
    mv /etc/resolv.conf_bak /etc/resolv.conf
    systemctl restart systemd-networkd >/dev/null 2>&1
    echo -e "\nReturns the nameservers settings to default..\n"
    echo -e "\nContinue installation..\n"
    sleep 3
  fi

cp /etc/resolv.conf /etc/resolv.conf-tmp

Line1="$(grep -n "f.write('nameserver 8.8.8.8')" installCyberPanel.py | head -n 1 | cut -d: -f1)"
sed -i "${Line1}i\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ subprocess.call\(command, shell=True)" installCyberPanel.py
sed -i "${Line1}i\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ command = 'cat /etc/resolv.conf-tmp > /etc/resolv.conf'" installCyberPanel.py
}

License_Validation() {
Debug_Log2 "Validating LiteSpeed license...,40"
Current_Dir=$(pwd)

if [ -f /root/cyberpanel-tmp ]; then
  rm -rf /root/cyberpanel-tmp
fi

mkdir /root/cyberpanel-tmp
cd /root/cyberpanel-tmp || exit

Retry_Command "wget https://cyberpanel.sh/www.litespeedtech.com/packages/${LSWS_Stable_Version:0:1}.0/lsws-$LSWS_Stable_Version-ent-x86_64-linux.tar.gz"
tar xzvf "lsws-$LSWS_Stable_Version-ent-x86_64-linux.tar.gz" >/dev/null
cd "/root/cyberpanel-tmp/lsws-$LSWS_Stable_Version/conf"  || exit
if [[ "$License_Key" = "Trial" ]]; then
  Retry_Command "wget -q https://cyberpanel.sh/license.litespeedtech.com/reseller/trial.key"
  sed -i "s|writeSerial = open('lsws-6.0/serial.no', 'w')|command = 'wget -q --output-document=./lsws-$LSWS_Stable_Version/trial.key https://cyberpanel.sh/license.litespeedtech.com/reseller/trial.key'|g" "$Current_Dir/installCyberPanel.py"
  sed -i 's|writeSerial.writelines(self.serial)|subprocess.call(command, shell=True)|g' "$Current_Dir/installCyberPanel.py"
  sed -i 's|writeSerial.close()||g' "$Current_Dir/installCyberPanel.py"
else
  echo "$License_Key" > serial.no
fi

cd "/root/cyberpanel-tmp/lsws-$LSWS_Stable_Version/bin"  || exit

if [[ "$License_Key" = "Trial" ]]; then
  License_Key="1111-2222-3333-4444"
else
  ./lshttpd -r
fi

if ./lshttpd -V |& grep "ERROR" || ./lshttpd -V |& grep "expire in 0 days" ; then
  echo -e "\n\nThere appears to be an issue with license , please check above result..."
  Debug_Log2 "There appears to be an issue with LiteSpeed License, make sure you are using correct serial key. [404]"
  exit
fi

echo -e "\nLicense seems valid..."
cd "$Current_Dir" || exit
rm -rf /root/cyberpanel-tmp
  #clean up the temp files
}

Pre_Install_CN_Replacement() {
if [[ "$Server_OS" = "Ubuntu" ]] ; then
  sed -i 's|wget http://rpms.litespeedtech.com/debian/|wget https://cyberpanel.sh/litespeed/|g' install.py
  sed -i 's|https://repo.dovecot.org/|https://cyberpanel.sh/repo.dovecot.org/|g' install.py
fi
  #replace litespeed repo on ubuntu 18/20

if [[ "$Server_OS" = "CentOS" ]] ; then
  sed -i 's|rpm -ivh http://rpms.litespeedtech.com/centos/litespeed-repo-1.2-1.el7.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo|g' install.py
  sed -i 's|rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo|g' install.py
  sed -i 's|https://mirror.ghettoforge.org/distributions|https://cyberpanel.sh/mirror.ghettoforge.org/distributions|g' install.py

  if [[ "$Server_OS_Version" = "8" ]] ; then
  sed -i 's|dnf --nogpg install -y https://mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el8.noarch.rpm|echo gf8|g' install.py
  sed -i 's|dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el8.noarch.rpm|echo gf8|g' install.py

  Retry_Command "dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el8.noarch.rpm"
  sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/8/gf/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/8/gf/x86_64/|g" /etc/yum.repos.d/gf.repo
  sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/8/plus/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/8/plus/x86_64/|g" /etc/yum.repos.d/gf.repo
  #get this set up beforehand.
  fi

fi

sed -i "s|https://www.litespeedtech.com/|https://cyberpanel.sh/www.litespeedtech.com/|g" installCyberPanel.py
sed -i 's|composer.sh|composer_cn.sh|g' install.py
sed -i 's|./composer_cn.sh|COMPOSER_ALLOW_SUPERUSER=1 ./composer_cn.sh|g' install.py
sed -i 's|http://www.litespeedtech.com|https://cyberpanel.sh/www.litespeedtech.com|g' install.py
sed -i 's|https://snappymail.eu/repository/latest.tar.gz|https://cyberpanel.sh/www.snappymail.eu/repository/latest.tar.gz|g' install.py

sed -i "s|rep.cyberpanel.net|cyberpanel.sh/rep.cyberpanel.net|g" installCyberPanel.py
sed -i "s|rep.cyberpanel.net|cyberpanel.sh/rep.cyberpanel.net|g" install.py


Debug_Log2 "Setting up URLs for CN server...,1"


sed -i 's|wget -O -  https://get.acme.sh \| sh|echo acme|g' install.py
sed -i 's|/root/.acme.sh/acme.sh --upgrade --auto-upgrade|echo acme2|g' install.py

Current_Dir=$(pwd)
Retry_Command "git clone https://gitee.com/neilpang/acme.sh.git"
cd acme.sh || exit
./acme.sh --install
cd "$Current_Dir" || exit
rm -rf acme.sh

# shellcheck disable=SC2016
sed -i 's|$PROJECT/archive/$BRANCH.tar.gz|https://cyberpanel.sh/codeload.github.com/acmesh-official/acme.sh/tar.gz/master|g' /root/.acme.sh/acme.sh

Retry_Command "/root/.acme.sh/acme.sh --upgrade --auto-upgrade"
#install acme and upgrade it beforehand, to prevent gitee fail
}

Main_Installation() {
Debug_Log2 "Starting main installation..,30"
if [[ -d /usr/local/CyberCP ]] ; then
  echo -e "\n CyberPanel already installed, exiting..."
  Debug_Log2 "CyberPanel already installed, exiting... [404]"
  exit
fi

if [[ $Server_Edition = "Enterprise" ]] ; then
  echo -e "\nValidating the license..."
  echo -e "\nThis may take a minute..."
  echo -e "\nPlease be patient...\n"

  License_Validation

  sed -i "s|lsws-5.4.2|lsws-$LSWS_Stable_Version|g" installCyberPanel.py
  sed -i "s|lsws-5.3.5|lsws-$LSWS_Stable_Version|g" installCyberPanel.py
  sed -i "s|lsws-6.0|lsws-$LSWS_Stable_Version|g" installCyberPanel.py
  #this sed must be done after license validation

  Enterprise_Flag="--ent ent --serial "
fi

sed -i 's|git clone https://github.com/usmannasir/cyberpanel|echo downloaded|g' install.py
sed -i 's|mirror.cyberpanel.net|cyberpanel.sh|g' install.py


if [[ $Server_Country = "CN" ]] ; then
  Pre_Install_CN_Replacement
else
  sed -i 's|wget -O -  https://get.acme.sh \| sh|echo acme|g' install.py
  sed -i 's|/root/.acme.sh/acme.sh --upgrade --auto-upgrade|echo acme2|g' install.py

  Current_Dir=$(pwd)
  Retry_Command "git clone https://github.com/acmesh-official/acme.sh.git"
  cd acme.sh || exit
  ./acme.sh --install
  cd "$Current_Dir" || exit
  rm -rf acme.sh

  Retry_Command "/root/.acme.sh/acme.sh --upgrade --auto-upgrade"
  #install acme and upgrade it beforehand, to prevent gitee fail
fi
  #install acme.sh before main installation for issues #705 #707 #708 #709

echo -e "Preparing...\n"

Final_Flags=()
Final_Flags+=("$Server_IP")
Final_Flags+=(${Enterprise_Flag:+$Enterprise_Flag})
Final_Flags+=(${License_Key:+$License_Key})
Final_Flags+=(--postfix "${Postfix_Switch^^}")
Final_Flags+=(--powerdns "${PowerDNS_Switch^^}")
Final_Flags+=(--ftp "${PureFTPd_Switch^^}")

if [[ "$Redis_Hosting" = "Yes" ]] ; then
  Final_Flags+=(--redis enable)
fi

if [[ "$Remote_MySQL" = "On" ]] ; then
  Final_Flags+=(--remotemysql "${Remote_MySQL^^}")
  Final_Flags+=(--mysqlhost "$MySQL_Host")
  Final_Flags+=(--mysqldb "$MySQL_DB")
  Final_Flags+=(--mysqluser "$MySQL_User")
  Final_Flags+=(--mysqlpassword "$MySQL_Password")
  Final_Flags+=(--mysqlport "$MySQL_Port")
else
  Final_Flags+=(--remotemysql "${Remote_MySQL^^}")
fi
  #form up the final agurment for install.py
if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Final_Flags" "${Final_Flags[@]}"
fi

/usr/local/CyberPanel/bin/python install.py "${Final_Flags[@]}"


if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt >/dev/null; then
  echo -e "\nCyberPanel installation sucessfully completed...\n"
  Debug_Log2 "Main installation completed...,70"
else
  echo -e "Oops, something went wrong..."
  Debug_Log2 "Oops, something went wrong... [404]"
  exit
fi
}

Post_Install_Addon_Mecached_LSMCD() {
if [[ $Server_OS = "CentOS" ]] || [[ $Server_OS = "openEuler" ]]; then
  yum groupinstall "Development Tools" -y
  yum install autoconf automake zlib-devel openssl-devel expat-devel pcre-devel libmemcached-devel cyrus-sasl* -y
  wget -O lsmcd-master.zip https://cyberpanel.sh/codeload.github.com/litespeedtech/lsmcd/zip/master
  unzip lsmcd-master.zip
  Current_Dir=$(pwd)
  cd "$Current_Dir/lsmcd-master"  || exit
  ./fixtimestamp.sh
  ./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
  make
  make install
  systemctl enable lsmcd
  systemctl start lsmcd
  cd "$Current_Dir"  || exit
else
  DEBIAN_FRONTEND=noninteractive apt install build-essential zlib1g-dev libexpat1-dev openssl libssl-dev libsasl2-dev libpcre3-dev git -y
  wget -O lsmcd-master.zip https://cyberpanel.sh/codeload.github.com/litespeedtech/lsmcd/zip/master
  unzip lsmcd-master.zip
  Current_Dir=$(pwd)
  cd "$Current_Dir/lsmcd-master"  || exit
  ./fixtimestamp.sh
  ./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
  make
  make install
  cd "$Current_Dir"  || exit
  systemctl enable lsmcd
  systemctl start lsmcd
fi
}

Post_Install_Addon_Memcached() {
if [[ $Server_OS = "CentOS" ]]; then
  yum install -y lsphp??-memcached lsphp??-pecl-memcached
  if [[ $Total_RAM -eq "2048" ]] || [[ $Total_RAM -gt "2048" ]]; then
    Post_Install_Addon_Mecached_LSMCD
  else
    yum install -y memcached
    sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
    #turn off UDP and bind to 127.0.0.1 only
    systemctl enable memcached
    systemctl start memcached
  fi
fi
if [[ $Server_OS = "Ubuntu" ]]; then
  DEBIAN_FRONTEND=noninteractive apt install -y "lsphp*-memcached"

  if [[ "$Total_RAM" -eq "2048" ]] || [[ "$Total_RAM" -gt "2048" ]]; then
    Post_Install_Addon_Mecached_LSMCD
  else
    DEBIAN_FRONTEND=noninteractive apt install -y memcached
    systemctl enable memcached
    systemctl start memcached
  fi
fi
if [[ $Server_OS = "openEuler" ]]; then
  yum install -y lsphp??-memcached lsphp??-pecl-memcached
  if [[ $Total_RAM -eq "2048" ]] || [[ $Total_RAM -gt "2048" ]]; then
    Post_Install_Addon_Mecached_LSMCD
  else
    yum install -y memcached
    sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
    #turn off UDP and bind to 127.0.0.1 only
    systemctl enable memcached
    systemctl start memcached
  fi
fi

if pgrep "lsmcd" ; then
  echo -e "\n\nLiteSpeed Memcached installed and running..."
fi

if pgrep "memcached" ; then
  echo -e "\n\nMemcached installed and running..."
fi
}

Post_Install_Addon_Redis() {
if [[ "$Server_OS" = "CentOS" ]]; then
  if [[ "$Server_OS_Version" = "8" ]]; then
    yum install -y lsphp??-redis redis
  else
    yum -y install http://rpms.remirepo.net/enterprise/remi-release-7.rpm
    yum-config-manager --disable remi
    yum-config-manager --disable remi-safe
    yum -y --enablerepo=remi install redis
  fi
fi

if [[ $Server_OS = "Ubuntu" ]]; then
  DEBIAN_FRONTEND=noninteractive apt install -y "lsphp*-redis" redis
fi

if ifconfig -a | grep inet6; then
  echo -e "\nIPv6 detected...\n"
else
  sed -i 's|bind 127.0.0.1 ::1|bind 127.0.0.1|g' /etc/redis/redis.conf
  echo -e "\n no IPv6 detected..."
fi

if [[ $Server_OS = "Ubuntu" ]]; then
  systemctl stop redis-server
  rm -f /var/run/redis/redis-server.pid
  systemctl enable redis-server
  systemctl start redis-server
else
  systemctl enable redis
  systemctl start redis
fi

if [[ "$Server_OS" = "openEuler" ]]; then
  yum install -y lsphp??-redis redis6
fi

if pgrep "redis" ; then
  echo -e "\n\nRedis installed and running..."
  touch /home/cyberpanel/redis
fi
}

Post_Install_PHP_Session_Setup() {
echo -e "\nSetting up PHP session storage path...\n"
#wget -O /root/php_session_script.sh "${Git_Content_URL}/stable/CPScripts/setup_php_sessions.sh"
chmod +x /usr/local/CyberCP/CPScripts/setup_php_sessions.sh
bash /usr/local/CyberCP/CPScripts/setup_php_sessions.sh
#rm -f /root/php_session_script.sh
Debug_Log2 "Setting up PHP session conf...,90"
}

Post_Install_PHP_TimezoneDB() {
Current_Dir="$(pwd)"
rm -f /usr/local/lsws/cyberpanel-tmp
mkdir /usr/local/lsws/cyberpanel-tmp
cd /usr/local/lsws/cyberpanel-tmp || exit
wget -O timezonedb.tgz https://cyberpanel.sh/pecl.php.net/get/timezonedb
tar xzvf timezonedb.tgz
cd timezonedb-*  || exit

if [[ "$Server_OS" = "Ubuntu" ]] ; then
  DEBIAN_FRONTEND=noninteractive apt install libmagickwand-dev pkg-config build-essential -y
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp*-dev
else
  yum remove -y lsphp??-mysql
  yum install -y lsphp??-mysqlnd
  yum install -y lsphp??-devel make gcc glibc-devel libmemcached-devel zlib-devel
fi

for PHP_Version in /usr/local/lsws/lsphp?? ;
  do
    PHP_INI_Path=$(find "$PHP_Version" -name php.ini)

    if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "openEuler" ]]; then
      if [[ ! -d "${PHP_Version}/tmp" ]]; then
        mkdir "${PHP_Version}/tmp"
      fi
      "${PHP_Version}"/bin/pecl channel-update pecl.php.net
      "${PHP_Version}"/bin/pear config-set temp_dir "${PHP_Version}/tmp"
      "${PHP_Version}"/bin/phpize
      ./configure --with-php-config="${PHP_Version}"/bin/php-config
      make
      make install
      echo "extension=timezonedb.so" > "${PHP_Version}/etc/php.d/20-timezone.ini"
      make clean
      sed -i 's|expose_php = On|expose_php = Off|g' "$PHP_INI_Path"
      sed -i 's|mail.add_x_header = On|mail.add_x_header = Off|g' "$PHP_INI_Path"
    else
      "${PHP_Version}"/bin/phpize
      ./configure --with-php-config="${PHP_Version}"/bin/php-config
      make
      make install
      echo "extension=timezonedb.so" > "/usr/local/lsws/${PHP_Version: 16:7}/etc/php/${PHP_Version: 21:1}.${PHP_Version: 22:1}/mods-available/20-timezone.ini"
      make clean
      sed -i 's|expose_php = On|expose_php = Off|g' "$PHP_INI_Path"
      sed -i 's|mail.add_x_header = On|mail.add_x_header = Off|g' "$PHP_INI_Path"
    fi
  done
rm -rf /usr/local/lsws/cyberpanel-tmp
cd "$Current_Dir" || exit
Debug_Log2 "Installing timezoneDB...,95"
}

Post_Install_Regenerate_Webadmin_Console_Passwd() {
if [[ "$Server_Edition" = "OLS" ]]; then
  PHP_Command="admin_php"
else
  PHP_Command="admin_php5"
fi

Webadmin_Pass=$(
  head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16
  echo ''
  )

Encrypt_string=$(/usr/local/lsws/admin/fcgi-bin/${PHP_Command} /usr/local/lsws/admin/misc/htpasswd.php "${Webadmin_Pass}")
echo "" >/usr/local/lsws/admin/conf/htpasswd
echo "admin:$Encrypt_string" > /usr/local/lsws/admin/conf/htpasswd
chown lsadm:lsadm /usr/local/lsws/admin/conf/htpasswd
chmod 600 /usr/local/lsws/admin/conf/htpasswd
echo "${Webadmin_Pass}" >/etc/cyberpanel/webadmin_passwd
chmod 600 /etc/cyberpanel/webadmin_passwd
}

Post_Install_Setup_Watchdog() {
if [[ "$Watchdog" = "On" ]]; then
  wget -O /etc/cyberpanel/watchdog.sh "${Git_Content_URL}/stable/CPScripts/watchdog.sh"
  chmod 700 /etc/cyberpanel/watchdog.sh
  ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
  #shellcheck disable=SC2009
  pid=$(ps aux | grep "watchdog lsws" | grep -v grep | awk '{print $2}')
  if [[ $pid = "" ]]; then
    nohup watchdog lsws >/dev/null 2>&1 &
  fi
  echo -e "Checking MariaDB ..."
  #shellcheck disable=SC2009
  pid=$(ps aux | grep "watchdog mariadb" | grep -v grep | awk '{print $2}')
  if [[ $pid = "" ]]; then
    nohup watchdog mariadb >/dev/null 2>&1 &
  fi

  if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "openEuler" ]]; then
    echo "nohup watchdog lsws > /dev/null 2>&1 &
nohup watchdog mariadb > /dev/null 2>&1 &" >>/etc/rc.d/rc.local
  else
    echo "nohup watchdog lsws > /dev/null 2>&1 &
nohup watchdog mariadb > /dev/null 2>&1 &" >>/etc/rc.local
  fi
  echo -e "\nSetting up WatchDog..."
fi
}

Post_Install_Setup_Utility() {
if [[ ! -f /usr/bin/cyberpanel_utility ]]; then
  wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
  chmod 700 /usr/bin/cyberpanel_utility
fi
}

Post_Install_Display_Final_Info() {
snappymailAdminPass=$(grep SetPassword /usr/local/CyberCP/public/snappymail.php| sed -e 's|$oConfig->SetPassword(||g' -e "s|');||g" -e "s|'||g")
Elapsed_Time="$((Time_Count / 3600)) hrs $(((SECONDS / 60) % 60)) min $((Time_Count % 60)) sec"
echo "###################################################################"
echo "                CyberPanel Successfully Installed                  "
echo "                                                                   "
echo "                Current Disk usage : $(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')                        "
echo "                                                                   "
echo "                Current RAM  usage : $(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')                         "
echo "                                                                   "
echo "                Installation time  : $Elapsed_Time                 "
echo "                                                                   "
echo "                Visit: https://$Server_IP:8090                     "
echo "                Panel username: admin                              "
if [[ "$Custom_Pass" = "True" ]]; then
echo "                Panel password: *****                              "
else
echo "                Panel password: $Admin_Pass                        "
fi
#echo "                Visit: https://$Server_IP:7080                     "
#echo "                WebAdmin console username: admin                   "
#echo "                WebAdmin console password: $Webadmin_Pass          "
#echo "                                                                   "
#echo "                Visit: https://$Server_IP:8090/snappymail/?admin     "
#echo "                snappymail Admin username: admin                     "
#echo "                snappymail Admin password: $snappymailAdminPass        "
echo "                                                                   "
echo -e "             Run \e[31mcyberpanel help\e[39m to get FAQ info"
echo -e "             Run \e[31mcyberpanel upgrade\e[39m to upgrade it to latest version."
echo -e "             Run \e[31mcyberpanel utility\e[39m to access some handy tools ."
echo "                                                                   "
echo "              Website : https://www.cyberpanel.net                 "
echo "              Forums  : https://forums.cyberpanel.net              "
echo "              Wikipage: https://docs.cyberpanel.net                "
echo "              Docs    : https://cyberpanel.net/docs/               "
echo "                                                                   "
echo -e "            Enjoy your accelerated Internet by                  "
echo -e "                CyberPanel & $Word 				                     "
echo "###################################################################"

if [[ "$Server_Provider" != "Undefined" ]]; then
  echo -e "\033[0;32m$Server_Provider\033[39m detected..."
  echo -e "This provider has a \e[31mnetwork-level firewall\033[39m"
else
  echo -e "If your provider has a \e[31mnetwork-level firewall\033[39m"
fi
echo -e "Please make sure you have opened following port for both in/out:"
echo -e "\033[0;32mTCP: 8090\033[39m for CyberPanel"
echo -e "\033[0;32mTCP: 80\033[39m, \033[0;32mTCP: 443\033[39m and \033[0;32mUDP: 443\033[39m for webserver"
echo -e "\033[0;32mTCP: 21\033[39m and \033[0;32mTCP: 40110-40210\033[39m for FTP"
echo -e "\033[0;32mTCP: 25\033[39m, \033[0;32mTCP: 587\033[39m, \033[0;32mTCP: 465\033[39m, \033[0;32mTCP: 110\033[39m, \033[0;32mTCP: 143\033[39m and \033[0;32mTCP: 993\033[39m for mail service"
echo -e "\033[0;32mTCP: 53\033[39m and \033[0;32mUDP: 53\033[39m for DNS service"

if ! timeout 3 telnet mx.zoho.com 25 | grep "Escape" >/dev/null 2>&1; then
  echo -e "Your provider seems \e[31mblocked\033[39m port 25 , E-mail sending may \e[31mnot\033[39m work properly."
fi

Debug_Log2 "Completed [200]"

if [[ "$Silent" != "On" ]]; then
  printf "%s" "Would you like to restart your server now? [y/N]: "
  read -r Tmp_Input

  if [[ "${Tmp_Input^^}" = *Y* ]] ; then
    reboot
  fi
fi

}


Post_Install_Regenerate_Cert() {
cat <<EOF >/root/cyberpanel/cert_conf
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
openssl req -x509 -config /root/cyberpanel/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout /usr/local/lscp/conf/key.pem -out /usr/local/lscp/conf/cert.pem

if [[ "$Server_Edition" = "OLS" ]]; then
  Key_Path="/usr/local/lsws/admin/conf/webadmin.key"
  Cert_Path="/usr/local/lsws/admin/conf/webadmin.crt"
else
  Key_Path="/usr/local/lsws/admin/conf/cert/admin.key"
  Cert_Path="/usr/local/lsws/admin/conf/cert/admin.crt"
fi
openssl req -x509 -config /root/cyberpanel/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout "$Key_Path" -out "$Cert_Path"
rm -f /root/cyberpanel/cert_conf
}

Post_Install_Required_Components() {
Debug_Log2 "Finalization..,80"

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]] ; then
python3 -m venv /usr/local/CyberCP
Check_Return
else
virtualenv -p /usr/bin/python3 /usr/local/CyberCP
  Check_Return
fi

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "20" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberCP/bin/activate
   Check_Return
else
  # shellcheck disable=SC1091
  source /usr/local/CyberCP/bin/activate
   Check_Return

fi

Retry_Command "pip install --default-timeout=3600 -r /usr/local/requirments.txt"
 Check_Return "requirments.txt" "no_exit"

if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]] ; then
  cp /usr/bin/python3.10 /usr/local/CyberCP/bin/python3
fi

chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib64 || true
}

Pre_Install_Setup_Git_URL() {
if [[ $Server_Country != "CN" ]] ; then
  Git_User="usmannasir"
  Git_Content_URL="https://raw.githubusercontent.com/${Git_User}/cyberpanel"
  Git_Clone_URL="https://github.com/${Git_User}/cyberpanel.git"
else
  Git_User="qtwrk"
  Git_Content_URL="https://gitee.com/${Git_User}/cyberpanel/raw"
  Git_Clone_URL="https://gitee.com/${Git_User}/cyberpanel.git"
fi

if [[ "$Debug" = "On" ]] ; then
  Debug_Log "Git_URL" "$Git_Content_URL"
fi
}

Post_Install_Tweak() {
if [[ -d /etc/pure-ftpd/conf ]]; then
  echo "yes" >/etc/pure-ftpd/conf/ChrootEveryone
  systemctl restart pure-ftpd-mysql
fi

if [[ -f /etc/pure-ftpd/pure-ftpd.conf ]]; then
  sed -i 's|NoAnonymous                 no|NoAnonymous                 yes|g' /etc/pure-ftpd/pure-ftpd.conf
fi

sed -i "s|lsws-5.3.8|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.4.2|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.3.5|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py


if [[ ! -f /usr/bin/cyberpanel_utility ]]; then
  wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
  chmod 700 /usr/bin/cyberpanel_utility
fi

rm -rf /etc/profile.d/cyberpanel*
curl --silent -o /etc/profile.d/cyberpanel.sh https://cyberpanel.sh/?banner 2>/dev/null
chmod 700 /etc/profile.d/cyberpanel.sh
echo "$Admin_Pass" > /etc/cyberpanel/adminPass
chmod 600 /etc/cyberpanel/adminPass
/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py --password "$Admin_Pass"
mkdir -p /etc/opendkim

echo '/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py --password $@' > /usr/bin/adminPass
echo "systemctl restart lscpd" >> /usr/bin/adminPass
echo "echo \$@ > /etc/cyberpanel/adminPass" >> /usr/bin/adminPass
chmod 700 /usr/bin/adminPass

rm -f /usr/bin/php
ln -s /usr/local/lsws/lsphp74/bin/php /usr/bin/php

if [[ "$Server_OS" = "CentOS" ]] ; then
#all centos 7/8 post change goes here

  sed -i 's|error_reporting = E_ALL \&amp; ~E_DEPRECATED \&amp; ~E_STRICT|error_reporting = E_ALL \& ~E_DEPRECATED \& ~E_STRICT|g' /usr/local/lsws/{lsphp72,lsphp73}/etc/php.ini
#fix php.ini &amp; issue
  sed -i 's|/usr/local/lsws/bin/lswsctrl restart|systemctl restart lsws|g' /var/spool/cron/root

  if [[ "$Server_OS_Version" = "7" ]] ; then
  #all centos 7 specific post change goes here
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
    #fix compile lsphp74-zip on centos 7
    fi
  fi

  if [[ "$Server_OS_Version" = "8" ]] ; then
  #all centos 8 specific post change goes here
  :
  fi

elif [[ "$Server_OS" = "Ubuntu" ]] ; then
#all ubuntu 18/20 post change goes here
  sed -i 's|/usr/local/lsws/bin/lswsctrl restart|systemctl restart lsws|g' /var/spool/cron/crontabs/root
  if [[ ! -f /usr/sbin/ipset ]] ; then
    ln -s /sbin/ipset /usr/sbin/ipset
  fi

  if [[ "$Server_OS_Version" = "18" ]] ; then
    #all ubuntu 18 specific post change goes here
    :
  fi

  if [[ "$Server_OS_Version" = "20" ]] ; then
    #all ubuntu 20 specific post change goes here
    :
  fi

elif [[ "$Server_OS" = "openEuler" ]] ; then
  sed -i 's|error_reporting = E_ALL \&amp; ~E_DEPRECATED \&amp; ~E_STRICT|error_reporting = E_ALL \& ~E_DEPRECATED \& ~E_STRICT|g' /usr/local/lsws/{lsphp72,lsphp73}/etc/php.ini
  #fix php.ini &amp; issue
  sed -i 's|/usr/local/lsws/bin/lswsctrl restart|systemctl restart lsws|g' /var/spool/cron/root
fi

if [[ "$Server_Edition" = "OLS" ]]; then
  Word="OpenLiteSpeed"
else
  Word="LiteSpeed Enterprise"
  sed -i 's|Include /usr/local/lsws/conf/rules.conf||g' /usr/local/lsws/conf/modsec.conf
fi

systemctl restart lscpd >/dev/null 2>&1
/usr/local/lsws/bin/lswsctrl stop >/dev/null 2>&1
systemctl stop lsws >/dev/null 2>&1
systemctl start lsws >/dev/null 2>&1
echo -e "\nFinalizing...\n"
echo -e "Cleaning up...\n"
rm -rf /root/cyberpanel

if [[ "$Server_Country" = "CN" ]] ; then
Post_Install_CN_Replacement
fi

# If valid hostname is set that resolves externally we can issue an ssl. This will create the hostname as a website so we can issue the SSL and do our first login without SSL warnings or exceptions needed.
HostName=$(hostname --fqdn); [ -n "$(dig @1.1.1.1 +short "$HostName")" ]  &&  echo "$HostName resolves to valid IP. Setting up hostname SSL" && cyberpanel createWebsite --package Default --owner admin --domainName $(hostname --fqdn) --email root@localhost --php 7.4 && cyberpanel hostNameSSL --domainName $(hostname --fqdn)


}

Post_Install_CN_Replacement() {
sed -i 's|wp core download|wp core download https://cyberpanel.sh/wordpress.org/latest.tar.gz|g' /usr/local/CyberCP/plogical/applicationInstaller.py
sed -i 's|https://raw.githubusercontent.com/|https://cyberpanel.sh/raw.githubusercontent.com/|g' /usr/local/CyberCP/plogical/applicationInstaller.py
sed -i 's|wp plugin install litespeed-cache|wp plugin install  https://cyberpanel.sh/downloads.wordpress.org/plugin/litespeed-cache.zip|g' /usr/local/CyberCP/plogical/applicationInstaller.py

sed -i 's|https://www.litespeedtech.com/|https://cyberpanel.sh/www.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|http://license.litespeedtech.com/|https://cyberpanel.sh/license.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
}

echo -e "\nInitializing...\n"

if [[ "$*" = *"--debug"* ]] ; then
  Debug="On"
  find /var/log -name 'cyberpanel_debug_*' -exec rm {} +
  Random_Log_Name=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 5)
  echo -e "$(date)" > "/var/log/cyberpanel_debug_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
  chmod 600 "/var/log/cyberpanel_debug_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
fi

Set_Default_Variables

Check_Root

Check_Server_IP "$@"

Check_OS

Check_Virtualization

Check_Panel

Check_Process

Check_Provider

Check_Argument "$@"

if [[ $Silent = "On" ]]; then
  Argument_Mode
else
  Interactive_Mode
fi

Time_Count="0"

Pre_Install_Setup_Repository

Pre_Install_Setup_Git_URL

Pre_Install_Required_Components

Pre_Install_System_Tweak

Main_Installation
#Python install in here

if [[ "$Memcached" = "On" ]] ; then
  Post_Install_Addon_Memcached
fi

if [[ "$Redis" = "On" ]] ; then
  Post_Install_Addon_Redis
fi

Post_Install_Required_Components

Post_Install_PHP_Session_Setup

Post_Install_PHP_TimezoneDB

Post_Install_Regenerate_Cert

Post_Install_Regenerate_Webadmin_Console_Passwd

Post_Install_Setup_Watchdog

Post_Install_Setup_Utility

Post_Install_Tweak

Post_Install_Display_Final_Info
