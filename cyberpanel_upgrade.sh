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

Sudo_Test=$(set)
#for SUDO check

Set_Default_Variables() {

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
  if echo "$Sudo_Test" | grep SUDO >/dev/null; then
    echo -e "\nYou are using SUDO, please run as root user...\n"
    echo -e "\nIf you don't have direct access to root user, please run \e[31msudo su -\e[39m command (do NOT miss the \e[31m-\e[39m at end or it will fail) and then run installation command again."
    exit
  fi

  if [[ $(id -u) != 0 ]] >/dev/null; then
    echo -e "\nYou must run as root user to install CyberPanel...\n"
    echo -e "or run the following command: (do NOT miss the quotes)"
    echo -e "\e[31msudo su -c \"sh <(curl https://cyberpanel.sh || wget -O - https://cyberpanel.sh)\"\e[39m"
    exit 1
  else
    echo -e "\nYou are running as root...\n"
  fi
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

if ! uname -m | grep -q x86_64 ; then
  echo -e "x86_64 system is required...\n"
  exit
fi

if grep -q -E "CentOS Linux 7|CentOS Linux 8" /etc/os-release ; then
  Server_OS="CentOS"
elif grep -q -E "CloudLinux 7|CloudLinux 8" /etc/os-release ; then
  Server_OS="CloudLinux"
elif grep -q "AlmaLinux-8" /etc/os-release ; then
  Server_OS="AlmaLinux"
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

if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] ; then
  Server_OS="CentOS"
  #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
  #treat CloudLinux, Rocky and Alma as CentOS
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
    echo -e "\nYou must use version number higher than 1.9.4"
    exit
  else
    Branch_Name="v${1//[[:space:]]/}"
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
  $1  && break || echo -e "\n$1 has failed for $i times\nWait for 3 seconds and try again...\n"; sleep 3;
done
}

Check_Argument() {
if [[ "$*" = *"--branch "* ]] || [[ "$*" = *"-b "* ]]; then
  Branch_Name=$(echo "$*" | sed -e "s/--branch //" -e "s/--mirror//" -e "s/-b //")
  Branch_Check "$Branch_Name"
fi
}

Pre_Upgrade_Setup_Git_URL() {
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
if [[ "$Server_OS" = "CentOS" ]] ; then
  rm -f /etc/yum.repos.d/CyberPanel.repo
  rm -f /etc/yum.repos.d/litespeed.repo
  if [[ "$Server_Country" = "CN" ]] ; then
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo
  else
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed.repo
  fi
  yum clean all
  yum update -y
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

    cat << EOF > /etc/yum.repos.d/MariaDB.repo
# MariaDB 10.4 CentOS repository list - created 2021-08-06 02:01 UTC
# http://downloads.mariadb.org/mariadb/repositories/
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.4/centos7-amd64
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
      sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/7/gf/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/7/gf/x86_64/|g" /etc/yum.repos.d/gf.repo
      sed -i "s|mirrorlist=http://mirrorlist.ghettoforge.org/el/7/plus/\$basearch/mirrorlist|baseurl=https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64/|g" /etc/yum.repos.d/gf.repo
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
    dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  else
    dnf --nogpg install -y https://mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  fi

  dnf install epel-release -y

  dnf install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git platform-python-devel tar socat bind-utils
  dnf install gpgme-devel -y
  dnf install python3 -y
  fi
  #all pre-upgrade operation for CentOS 8
elif [[ "$Server_OS" = "Ubuntu" ]] ; then

  apt update -y
  DEBIAN_FRONTEND=noninteractive apt upgrade -y

  if [[ "$Server_OS_Version" = "22" ]] ; then
    DEBIAN_FRONTEND=noninteracitve apt install -y dnsutils net-tools htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git socat vim unzip zip libmariadb-dev-compat libmariadb-dev

  else
    DEBIAN_FRONTEND=noninteracitve apt install -y htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadbclient-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git dnsutils
  fi
  DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
  DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
  DEBIAN_FRONTEND=noninteractive apt install -y python3-venv

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
for i in {1..50};
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
#special made function for Gitee.com, for whatever reason sometimes it fails to download this file
}



Pre_Upgrade_Required_Components() {

if [ "$Server_OS" = "Ubuntu" ]; then
  pip3 install --default-timeout=3600 virtualenv==16.7.9
    Check_Return
else
  pip3.6 install --default-timeout=3600 virtualenv==16.7.9
    Check_Return
fi

if [[ -f /usr/local/CyberPanel/bin/python2 ]]; then
  echo -e "\nPython 2 dectected, doing re-setup...\n"
  rm -rf /usr/local/CyberPanel/bin
  virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
  Check_Return
elif [[ -d /usr/local/CyberPanel/bin/ ]]; then
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberPanel...\n"
else
  echo -e "\nNothing found, need fresh setup...\n"
  virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
  Check_Return
fi

# shellcheck disable=SC1091
. /usr/local/CyberPanel/bin/activate

Download_Requirement

if [[ "$Server_OS" = "CentOS" ]] ; then
  pip3.6 install --default-timeout=3600 virtualenv==16.7.9
    Check_Return
  pip3.6 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberPanel/bin/activate
    Check_Return
  pip3 install --default-timeout=3600 virtualenv==16.7.9
    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "openEuler" ]] ; then
  pip3 install --default-timeout=3600 virtualenv==16.7.9
    Check_Return
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

Pre_Upgrade_Setup_Git_URL() {
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

Pre_Upgrade_Branch_Input() {
  echo -e "\nPress the Enter key to continue with latest version, or enter specific version such as: \e[31m1.9.4\e[39m , \e[31m1.9.5\e[39m ...etc"
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
/usr/local/CyberPanel/bin/python upgrade.py "$Branch_Name"
  Check_Return

if [[ -f /usr/local/CyberCP/bin/python2 ]]; then
  rm -rf /usr/local/CyberCP/bin
  virtualenv -p /usr/bin/python3 /usr/local/CyberCP
    Check_Return
elif [[ -d /usr/local/CyberCP/bin/ ]]; then
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberCP...\n"
else
  virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberCP
    Check_Return
fi

rm -f /usr/local/requirments.txt

Download_Requirement

if [ "$Server_OS" = "Ubuntu" ]; then
  # shellcheck disable=SC1091
  . /usr/local/CyberCP/bin/activate
    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
else
  # shellcheck disable=SC1091
  source /usr/local/CyberCP/bin/activate
    Check_Return
  pip3.6 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
fi

wget https://cyberpanel.sh/www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz
tar xf wsgi-lsapi-2.1.tgz
cd wsgi-lsapi-2.1 || exit
/usr/local/CyberPanel/bin/python ./configure.py
make

rm -f /usr/local/CyberCP/bin/lswsgi
cp lswsgi /usr/local/CyberCP/bin/

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
systemctl restart lscpd

}

Post_Install_Display_Final_Info() {
Panel_Port=$(cat /usr/local/lscp/conf/bind.conf)
if [[ $Panel_Port = "" ]] ; then
  Panel_Port="8090"
fi

if curl -I -XGET -k "https://127.0.0.1:${Panel_Port#*:}" | grep -q "200 OK" ; then
  echo "###################################################################"
  echo "                CyberPanel Upgraded                                "
  echo "###################################################################"
else
  echo -e "\nSeems something wrong with upgrade, please check...\n"
fi
rm -rf /root/cyberpanel_upgrade_tmp
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

Pre_Upgrade_Setup_Repository

Pre_Upgrade_Setup_Git_URL

Pre_Upgrade_Required_Components

Main_Upgrade

Post_Upgrade_System_Tweak

Post_Install_Display_Final_Info
