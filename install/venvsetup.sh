#!/bin/bash

#CyberPanel installer script for Ubuntu 18.04 and CentOS 7.X

# Constants
readonly DEFAULT_ADMIN_PASS="1234567"
readonly MIN_PASSWORD_LENGTH=8
readonly DEFAULT_TIMEOUT=10
readonly CYBERPANEL_PORT=8090
readonly DEFAULT_SWAP_SIZE_MB=2048
readonly RANDOM_PASSWORD_LENGTH=16
readonly PID_MAX=1000000
readonly KSM_RUN=1
readonly VM_SWAPPINESS=10
readonly INSTALLATION_DELAY_SECONDS=10
readonly MIN_DISK_SPACE_GB=10
readonly FILE_MAX=65535
readonly NOFILE_LIMIT=65535
readonly NPROC_LIMIT=65535

# URLs and endpoints
readonly CYBERPANEL_VERSION_URL="https://cyberpanel.net/version.txt"
readonly LITESPEED_UPDATE_URL="https://update.litespeedtech.com/ws/latest.php"
readonly CYBERPANEL_SH_URL="https://cyberpanel.sh"
readonly CYBERPANEL_CDN_URL="https://cdn.cyberpanel.sh"
readonly GITHUB_REPO_URL="https://github.com/usmannasir/cyberpanel"
readonly GITHUB_RAW_URL="https://raw.githubusercontent.com/usmannasir/cyberpanel"

# Default values
DEV="OFF"

PROVIDER="undefined"
SERIAL_NO=""
DIR=$(pwd)
TOTAL_RAM=$(free -m | awk '/Mem\:/ { print $2 }')

# Version information
TEMP=$(curl --silent --max-time "$DEFAULT_TIMEOUT" "$CYBERPANEL_VERSION_URL")
CP_VER1=${TEMP:12:3}
CP_VER2=${TEMP:25:1}
SERVER_OS="CentOS"
VERSION="OLS"
LICENSE_KEY=""
ADMIN_PASS="$DEFAULT_ADMIN_PASS"
MEMCACHED="ON"
REDIS="ON"

# Function to perform common sed replacements
perform_sed_replacements() {
	local file="$1"
	
	# Replace cyberpanel.sh with DOWNLOAD_SERVER
	sed -i 's|cyberpanel.sh|'"$DOWNLOAD_SERVER"'|g' "$file"
	
	# Replace mirror.cyberpanel.net with DOWNLOAD_SERVER
	sed -i 's|mirror.cyberpanel.net|'"$DOWNLOAD_SERVER"'|g' "$file"
	
	# Replace git clone with echo downloaded
	sed -i 's|git clone https://github.com/usmannasir/cyberpanel|echo downloaded|g' "$file"
	
	# Replace http with https
	sed -i 's|http://|https://|g' "$file"
	
	# Replace wget rpms.litespeedtech.com with --no-check-certificate
	sed -i 's|wget https://rpms.litespeedtech.com/debian/|wget --no-check-certificate https://rpms.litespeedtech.com/debian/|g' "$file"
	
	# Replace powerdns repo URL
	sed -i 's|https://repo.powerdns.com/repo-files/centos-auth-42.repo|https://'"$DOWNLOAD_SERVER"'/powerdns/powerdns.repo|g' "$file"
	
	# Replace snappymail URL
	sed -i 's|https://snappymail.eu/repository/latest.tar.gz|https://'"$DOWNLOAD_SERVER"'/repository/latest.tar.gz|g' "$file"
	
	# Replace litespeed repo RPM
	sed -i 's|rpm -ivh https://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://'"$DOWNLOAD_SERVER"'/litespeed/litespeed.repo|g' "$file"
	
	# Replace restic repo URL
	sed -i 's|https://copr.fedorainfracloud.org/coprs/copart/restic/repo/epel-7/copart-restic-epel-7.repo|https://'"$DOWNLOAD_SERVER"'/restic/restic.repo|g' "$file"
	
	# Replace gf-release RPM
	sed -i 's|yum -y install https://cyberpanel.sh/gf-release-latest.gf.el7.noarch.rpm|wget -O /etc/yum.repos.d/gf.repo https://'"${DOWNLOAD_SERVER}"'/gf-plus/gf.repo|g' "$file"
	
	# Replace dovecot repo
	sed -i 's|dovecot-2.3-latest|dovecot-2.3-latest-mirror|g' "$file"
	
	# Replace git clone with wget for CN
	sed -i 's|git clone https://github.com/usmannasir/cyberpanel|wget https://cyberpanel.sh/cyberpanel-git.tar.gz \&\& tar xzvf cyberpanel-git.tar.gz|g' "$file"
	
	# Replace dovecot repo URL
	sed -i "s|https://repo.dovecot.org/ce-2.3-latest/centos/\$releasever/RPMS/\$basearch|https://${DOWNLOAD_SERVER}/dovecot/|g" "$file"
	
	# Replace DOWNLOAD_SERVER back to cyberpanel.sh for specific cases
	sed -i 's|'"${DOWNLOAD_SERVER}"'|cyberpanel.sh|g' "$file"
}

license_validation() {
CURRENT_DIR=$(pwd)

if [ -f /root/cyberpanel-tmp ] ; then
rm -rf /root/cyberpanel-tmp
fi

mkdir /root/cyberpanel-tmp
cd /root/cyberpanel-tmp || exit
wget -q "https://$DOWNLOAD_SERVER/litespeed/lsws-$LSWS_STABLE_VER-ent-x86_64-linux.tar.gz"
tar xzvf "lsws-$LSWS_STABLE_VER-ent-x86_64-linux.tar.gz" > /dev/null
cd "/root/cyberpanel-tmp/lsws-$LSWS_STABLE_VER/conf" || exit || exit
if [[ $LICENSE_KEY == "TRIAL" ]] ; then
wget -q http://license.litespeedtech.com/reseller/trial.key
sed -i 's|writeSerial = open('\''lsws-5.4.2/serial.no'\'', '\''w'\'')|command = '\''wget -q --output-document=./lsws-'"$LSWS_STABLE_VER"'/trial.key http://license.litespeedtech.com/reseller/trial.key'\''|g' "$CURRENT_DIR/installCyberPanel.py"
sed -i 's|writeSerial.writelines(self.serial)|subprocess.call(command, shell=True)|g' "$CURRENT_DIR/installCyberPanel.py"
sed -i 's|writeSerial.close()||g' "$CURRENT_DIR/installCyberPanel.py"
else
echo "$LICENSE_KEY" > serial.no
fi

cd "/root/cyberpanel-tmp/lsws-$LSWS_STABLE_VER/bin" || exit

if [[ $LICENSE_KEY == "TRIAL" ]] ; then
	if ./lshttpd -V 2>&1 | grep  "ERROR" ; then
	echo -e "\n\nIt appears to have some issue with license , please check above result..."
	exit
	fi
	LICENSE_KEY="1111-2222-3333-4444"
else
	if ./lshttpd -r 2>&1 | grep "ERROR" ; then
	./lshttpd -r
	echo -e "\n\nIt appears to have some issue with license , please check above result..."
	exit
	fi
fi
echo -e "License seems valid..."
cd /root/cyberpanel-tmp || exit
rm -rf "lsws-$LSWS_STABLE_VER*"
cd "$CURRENT_DIR" || exit
rm -rf /root/cyberpanel-tmp
}

special_change(){
# Use consolidated function for common sed replacements
perform_sed_replacements "install.py"
perform_sed_replacements "installCyberPanel.py"

LATEST_URL="$LITESPEED_UPDATE_URL"
#LATEST_URL="https://cyberpanel.sh/latest.php"
curl --silent -o /tmp/lsws_latest "$LATEST_URL" 2>/dev/null
LSWS_STABLE_LINE=$(grep LSWS_STABLE /tmp/lsws_latest)
LSWS_STABLE_VER=$(expr "$LSWS_STABLE_LINE" : '.*LSWS_STABLE=\(.*\) BUILD .*')

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	# Additional CN-specific replacements
	sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.4.2-ent-x86_64-linux.tar.gz|https://'"${DOWNLOAD_SERVER}"'/litespeed/lsws-'"${LSWS_STABLE_VER}"'-ent-x86_64-linux.tar.gz|g' installCyberPanel.py
	
	if [[ $SERVER_OS == "CentOS" ]] ; then
		DIR=$(pwd)
		cd "$DIR/mysql" || exit
		echo "[mariadb-tsinghua]
name = MariaDB
baseurl = https://mirrors.tuna.tsinghua.edu.cn/mariadb/yum/10.1/centos7-amd64
gpgkey = https://mirrors.tuna.tsinghua.edu.cn/mariadb/yum//RPM-GPG-KEY-MariaDB
gpgcheck = 1" > MariaDB.repo
#above to set mariadb db to Tsinghua repo
		cd "$DIR" || exit
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|g' installCyberPanel.py
		mkdir /root/.pip
		cat << EOF > /root/.pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/ 
EOF
		echo -e "\nSet to Aliyun pip repo..."
		cat << EOF > composer.sh
#!/usr/bin/env bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php
php -r "unlink('composer-setup.php');"
mv composer.phar /usr/bin/composer

if [ ! -d /root/.config ]; then
mkdir /root/.config
fi

if [ ! -d /root/.config/composer ]; then
mkdir /root/.config/composer
fi

echo '{
    "bitbucket-oauth": {},
    "github-oauth": {},
    "gitlab-oauth": {},
    "gitlab-token": {},
    "http-basic": {}
}
' > /root/.config/composer/auth.json

echo '{
    "config": {},
    "repositories": {
        "packagist": {
            "type": "composer",
            "url": "https://mirrors.aliyun.com/composer/"
        }
    }
}
' > /root/.config/composer/config.json
composer clear-cache
EOF
	fi


	if [[ $SERVER_OS == "Ubuntu" ]] ; then
		echo $'\n89.208.248.38 rpms.litespeedtech.com\n' >> /etc/hosts
		echo -e "Mirror server set..."
		pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
		cat << EOF > /root/.pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/ 
EOF
	echo -e "\nSet to Aliyun pip repo..."
		if [[ $PROVIDER == "Tencent Cloud" ]] ; then
		#tencent cloud and ubuntu system
		echo -e "\n Tencent Cloud detected ... bypass default repository"
		cp /etc/apt/sources.list /etc/apt/sources.list-backup
		#backup original sources list
		cat << 'EOF' > /etc/apt/sources.list
deb http://mirrors.aliyun.com/ubuntu/ bionic main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ bionic-security main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ bionic-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ bionic-proposed main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ bionic-backports main restricted universe multiverse
deb-src http://mirrors.aliyun.com/ubuntu/ bionic main restricted universe multiverse
deb-src http://mirrors.aliyun.com/ubuntu/ bionic-security main restricted universe multiverse
deb-src http://mirrors.aliyun.com/ubuntu/ bionic-updates main restricted universe multiverse
deb-src http://mirrors.aliyun.com/ubuntu/ bionic-proposed main restricted universe multiverse
deb-src http://mirrors.aliyun.com/ubuntu/ bionic-backports main restricted universe multiverse
EOF
		DEBIAN_FRONTEND=noninteractive apt update -y
		pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
		cat << EOF > composer.sh
#!/usr/bin/env bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php
php -r "unlink('composer-setup.php');"
mv composer.phar /usr/bin/composer

if [ ! -d /root/.config ]; then
mkdir /root/.config
fi

if [ ! -d /root/.config/composer ]; then
mkdir /root/.config/composer
fi

echo '{
    "bitbucket-oauth": {},
    "github-oauth": {},
    "gitlab-oauth": {},
    "gitlab-token": {},
    "http-basic": {}
}
' > /root/.config/composer/auth.json

echo '{
    "config": {},
    "repositories": {
        "packagist": {
            "type": "composer",
            "url": "https://mirrors.cloud.tencent.com/composer/"
        }
    }
}
' > /root/.config/composer/config.json
composer clear-cache
EOF
		else
	cat << EOF > composer.sh
#!/usr/bin/env bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php
php -r "unlink('composer-setup.php');"
mv composer.phar /usr/bin/composer

if [ ! -d /root/.config ]; then
mkdir /root/.config
fi

if [ ! -d /root/.config/composer ]; then
mkdir /root/.config/composer
fi

echo '{
    "bitbucket-oauth": {},
    "github-oauth": {},
    "gitlab-oauth": {},
    "gitlab-token": {},
    "http-basic": {}
}
' > /root/.config/composer/auth.json

echo '{
    "config": {},
    "repositories": {
        "packagist": {
            "type": "composer",
            "url": "https://packagist.phpcomposer.com"
        }
    }
}
' > /root/.config/composer/config.json
composer clear-cache
EOF
		fi
	fi
fi
}


system_tweak() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	setenforce 0
	sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
fi

if ! grep -q "pid_max" /etc/rc.local; then
		if [[ $SERVER_OS == "CentOS" ]] ; then
		echo "echo $PID_MAX > /proc/sys/kernel/pid_max
echo $KSM_RUN > /sys/kernel/mm/ksm/run" >> /etc/rc.d/rc.local
		chmod +x /etc/rc.d/rc.local
		else
		echo "echo $PID_MAX > /proc/sys/kernel/pid_max
echo $KSM_RUN > /sys/kernel/mm/ksm/run" >> /etc/rc.local
		chmod +x /etc/rc.local
		fi
	echo "fs.file-max = $FILE_MAX" >> /etc/sysctl.conf
	sysctl -p > /dev/null
	echo "*                soft    nofile          $NOFILE_LIMIT
*                hard    nofile          $NOFILE_LIMIT
root             soft    nofile          $NOFILE_LIMIT
root             hard    nofile          $NOFILE_LIMIT
*                soft    nproc           $NPROC_LIMIT
*                hard    nproc           $NPROC_LIMIT
root             soft    nproc           $NPROC_LIMIT
root             hard    nproc           $NPROC_LIMIT" >> /etc/security/limits.conf
fi

#sed -i 's|#DefaultLimitNOFILE=|DefaultLimitNOFILE=65535|g' /etc/systemd/system.conf


TOTAL_SWAP=$(free -m | awk '/^Swap:/ { print $2 }')
SET_SWAP=$((TOTAL_RAM - TOTAL_SWAP))
SWAP_FILE=/cyberpanel.swap

if [ ! -f $SWAP_FILE ] ; then
	if [[ $TOTAL_SWAP -gt $TOTAL_RAM ]] || [[ $TOTAL_SWAP -eq $TOTAL_RAM ]] ; then
		echo "SWAP check..."
	else
		if [[ $SET_SWAP -gt "$DEFAULT_SWAP_SIZE_MB" ]] ; then
			SET_SWAP="$DEFAULT_SWAP_SIZE_MB"
		else
			echo "Checking SWAP..."
		fi
	fallocate --length ${SET_SWAP}MiB $SWAP_FILE
	chmod 600 $SWAP_FILE
	mkswap $SWAP_FILE
	swapon $SWAP_FILE
	echo "${SWAP_FILE} swap swap sw 0 0" | sudo tee -a /etc/fstab
	sysctl vm.swappiness=$VM_SWAPPINESS
	echo "vm.swappiness = $VM_SWAPPINESS" >> /etc/sysctl.conf
	echo "SWAP set..."
	fi
fi
}


install_required() {
echo -e "\nInstalling necessary components..."
if [[ $SERVER_OS == "CentOS" ]] ; then
	rpm --import "https://$DOWNLOAD_SERVER/mariadb/RPM-GPG-KEY-MariaDB"
	rpm --import "https://$DOWNLOAD_SERVER/litespeed/RPM-GPG-KEY-litespeed"
	rpm --import "https://$DOWNLOAD_SERVER/powerdns/FD380FBB-pub.asc"
	rpm --import http://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7
	rpm --import "https://$DOWNLOAD_SERVER/gf-plus/RPM-GPG-KEY-gf.el7"
	rpm --import "https://repo.dovecot.org/DOVECOT-REPO-GPG"
	rpm --import "https://copr-be.cloud.fedoraproject.org/results/copart/restic/pubkey.gpg"
	yum autoremove epel-release -y
	rm -f /etc/yum.repos.d/epel.repo
	rm -f /etc/yum.repos.d/epel.repo.rpmsave
	yum clean all
	yum update -y
	yum install epel-release -y
	yum install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc python-devel libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel python-pip git
	if [[ $DEV == "ON" ]] ; then
		yum -y install yum-utils
		yum -y groupinstall development
		yum -y install https://centos7.iuscommunity.org/ius-release.rpm
		yum -y install python36u python36u-pip python36u-devel
	fi
fi

if [[ $SERVER_OS == "Ubuntu" ]] ; then
	apt update -y
	DEBIAN_FRONTEND=noninteractive apt upgrade -y
	DEBIAN_FRONTEND=noninteractive apt install -y htop telnet python-mysqldb python-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadbclient-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev python-gpg python python-minimal python-setuptools virtualenv python-dev python-pip git
	if [[ $DEV == "ON" ]] ; then
		DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
		DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
		DEBIAN_FRONTEND=noninteractive apt install -y python3-venv
	fi
fi
}

memcached_installation() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached lsphp56-pecl-memcached lsphp55-pecl-memcached lsphp54-pecl-memcached 
		if [[ $TOTAL_RAM -eq "$DEFAULT_SWAP_SIZE_MB" ]] || [[ $TOTAL_RAM -gt "$DEFAULT_SWAP_SIZE_MB" ]] ; then
			yum groupinstall "Development Tools" -y
			yum install autoconf automake zlib-devel openssl-devel expat-devel pcre-devel libmemcached-devel cyrus-sasl* -y
			wget "https://$DOWNLOAD_SERVER/litespeed/lsmcd.tar.gz"
			tar xzvf lsmcd.tar.gz
			DIR=$(pwd)
			cd "$DIR/lsmcd" || exit
			./fixtimestamp.sh
			./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
			make
			make install
			systemctl enable lsmcd
			systemctl start lsmcd
			cd "$DIR" || exit
		else
			yum install -y memcached
			sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
			systemctl enable memcached
			systemctl start memcached
		fi
fi
if [[ $SERVER_OS == "Ubuntu" ]] ; then
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached
		if [[ $TOTAL_RAM -eq "$DEFAULT_SWAP_SIZE_MB" ]] || [[ $TOTAL_RAM -gt "$DEFAULT_SWAP_SIZE_MB" ]] ; then
			DEBIAN_FRONTEND=noninteractive apt install build-essential zlib1g-dev libexpat1-dev openssl libssl-dev libsasl2-dev libpcre3-dev git -y
			wget "https://$DOWNLOAD_SERVER/litespeed/lsmcd.tar.gz"
			tar xzvf lsmcd.tar.gz
			DIR=$(pwd)
			cd "$DIR/lsmcd" || exit
			./fixtimestamp.sh
			./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
			make
			make install
			cd "$DIR" || exit
			systemctl enable lsmcd
			systemctl start lsmcd
		else
			DEBIAN_FRONTEND=noninteractive apt install -y memcached
			systemctl enable memcached
			systemctl start memcached
		fi
fi

if pgrep -f "lsmcd" > /dev/null; then
	echo -e "\n\nLiteSpeed Memcached installed and running..."
fi

if pgrep -f "memcached" > /dev/null; then
	echo -e "\n\nMemcached installed and running..."
fi

}

redis_installation() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis lsphp56-redis lsphp55-redis lsphp54-redis redis
fi
if [[ $SERVER_OS == "Ubuntu" ]] ; then
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis redis
fi

if ifconfig -a | grep inet6 ; then
	echo -e "\n IPv6 detected..."
else
	sed -i 's|bind 127.0.0.1 ::1|bind 127.0.0.1|g' /etc/redis/redis.conf
	echo -e "\n no IPv6 detected..."
fi

if [[ $SERVER_OS == "CentOS" ]] ; then
	systemctl enable redis
	systemctl start redis
fi

if [[ $SERVER_OS == "Ubuntu" ]] ; then
	systemctl enable redis-server
	systemctl start redis-server
fi

if pgrep -f "redis" > /dev/null; then
	echo -e "\n\nRedis installed and running..."
fi
}

check_provider() {
	
if hash dmidecode > /dev/null 2>&1 ; then
		if [ "$(dmidecode -s bios-vendor)" = 'Google' ] ; then
			PROVIDER='Google Cloud Platform'      
		elif [ "$(dmidecode -s bios-vendor)" = 'DigitalOcean' ] ; then
			PROVIDER='Digital Ocean'
		elif [ "$(dmidecode -s system-product-name | cut -c 1-7)" = 'Alibaba' ] ; then
			PROVIDER='Alibaba Cloud'
		elif [ "$(dmidecode -s system-manufacturer)" = 'Microsoft Corporation' ] ; then    
			PROVIDER='Microsoft Azure'
		elif [ -d /usr/local/qcloud ] ; then
			PROVIDER='Tencent Cloud'
		else
		PROVIDER='undefined' 
		fi 
else
	PROVIDER='undefined'
fi

if [ "$(cut -c 1-3 /sys/devices/virtual/dmi/id/product_uuid)" = 'EC2' ] && [ -d /home/ubuntu ]; then 
	PROVIDER='Amazon Web Service'
fi

}


check_OS() {
echo -e "\nChecking OS..."
OUTPUT=$(</etc/*release)
if  echo "$OUTPUT" | grep -q "CentOS Linux 7" ; then
	echo -e "\nDetecting CentOS 7.X...\n"
	SERVER_OS="CentOS"
elif echo "$OUTPUT" | grep -q "CloudLinux 7" ; then
	echo -e "\nDetecting CloudLinux 7.X...\n"
	SERVER_OS="CentOS"
elif echo "$OUTPUT" | grep -q "Ubuntu 18.04" ; then
	echo -e "\nDetecting Ubuntu 18.04...\n"
	SERVER_OS="Ubuntu"
else
	cat /etc/*release
	echo -e "\nUnable to detect your OS...\n"
	echo -e "\nCyberPanel is supported on Ubuntu 18.04, CentOS 7.x and CloudLinux 7.x...\n"
	exit 1
fi
}

check_root() {
echo -e "Checking root privileges...\n"
if [[ $(id -u) != 0 ]]; then
	echo -e "You must use a root account to do this"
	echo -e "or run following command: (do NOT miss the quotes)"
	echo -e "\e[31msudo su -c \"sh <(curl $CYBERPANEL_SH_URL || wget -O - $CYBERPANEL_SH_URL)\"\e[39m"
	exit 1
else
	echo -e "You are running as root...\n"
fi
}

check_panel() {
if [ -d /usr/local/cpanel ]; then
	echo -e "\ncPanel detected...exit...\n"
	exit 1
fi
if [ -d /opt/plesk ]; then
	echo -e "\nPlesk detected...exit...\n"
	exit 1
fi
}

check_process() {
if systemctl is-active --quiet httpd; then
	systemctl disable httpd
	systemctl stop httpd
	echo -e "\nhttpd process detected, disabling...\n"
fi
if systemctl is-active --quiet apache2; then
	systemctl disable apache2
	systemctl stop apache2
	echo -e "\napache2 process detected, disabling...\n"
fi
if systemctl is-active --quiet named; then
  systemctl stop named
  systemctl disable named
	echo -e "\nnamed process detected, disabling...\n"
fi
if systemctl is-active --quiet exim; then
	systemctl stop exim
	systemctl disable exim
	echo -e "\nexim process detected, disabling...\n"
fi
}

show_help() {
echo -e "\nCyberPanel Installer Script Help\n"
echo -e "\nUsage: wget $CYBERPANEL_SH_URL/cyberpanel.sh"
echo -e "\nchmod +x cyberpanel.sh"
echo -e "\n./cyberpanel.sh -v ols/SERIAL_NUMBER -c 1 -a 1"
echo -e "\n -v or --version: choose to install CyberPanel OpenLiteSpeed or CyberPanel Enterprise, available options are \e[31mols\e[39m and \e[31mSERIAL_NUMBER\e[39m, default ols"
echo -e "\n Please be aware, this serial number must be obtained from LiteSpeed Store."
echo -e "\n And if this serial number has been used before, it must be released/migrated in Store first, otherwise it will fail to start."
echo -e "\n -a or --addons: install addons: memcached, redis, PHP extension for memcached and redis, 1 for install addons, 0 for not to install, default 0, only applicable for CentOS system."
echo -e "\n -p or --password: set password of new installation, empty for default 1234567, [r] or [random] for randomly generated 16 digital password, any other value besdies [d] and [r(andom)] will be accept as password, default use 1234567."
#echo -e "\n -m: set to minimal mode which will not install PowerDNS, Pure-FTPd and Postfix"
echo -e "\n Example:"
echo -e "\n ./cyberpanel.sh -v ols -p r or ./cyberpanel.sh --version ols --password random"
echo -e "\n This will install CyberPanel OpenLiteSpeed and randomly generate the password."
echo -e "\n ./cyberpanel.sh default"
echo -e "\n This will install everything default , which is OpenLiteSpeed and nothing more.\n"

}

license_input() {
VERSION="ENT"
echo -e "\nPlease note that your server has \e[31m$TOTAL_RAM\e[39m RAM"
echo -e "If you are using \e[31mFree Start\e[39m license, It will not start due to \e[31m2GB RAM limit\e[39m.\n"
echo -e "If you do not have any license, you can also use trial license (if server has not used trial license before), type \e[31mTRIAL\e[39m\n"

printf "%s" "Please input your serial number for LiteSpeed WebServer Enterprise:"
read -r LICENSE_KEY
if [ -z "$LICENSE_KEY" ] ; then
	echo -e "\nPlease provide license key\n"
	exit
fi

echo -e "The serial number you input is: \e[31m$LICENSE_KEY\e[39m"
printf "%s"  "Please verify it is correct. [y/N]"
read -r TMP_YN
if [ -z "$TMP_YN" ] ; then
	echo -e "\nPlease type \e[31my\e[39m\n"
	exit
fi

KEY_SIZE=${#LICENSE_KEY}
TMP=$(echo "$LICENSE_KEY" | cut -c5)
TMP2=$(echo "$LICENSE_KEY" | cut -c10)
TMP3=$(echo "$LICENSE_KEY" | cut -c15)

if [[ $TMP == "-" ]] && [[ $TMP2 == "-" ]] && [[ $TMP3 == "-" ]] && [[ $KEY_SIZE == "19" ]] ; then
	echo -e "\nLicense key set..."
elif [[ $LICENSE_KEY == "trial" ]] || [[ $LICENSE_KEY == "TRIAL" ]] || [[ $LICENSE_KEY == "Trial" ]] ; then
	echo -e "\nTrial license set..."
	LICENSE_KEY="TRIAL"
else
	echo -e "\nLicense key seems incorrect, please verify\n"
	echo -e "\nIf you are copying/pasting, please make sure you didn't paste blank space...\n"
	exit
fi	
}

interactive_mode() {
echo -e "		CyberPanel Installer v$CP_VER1$CP_VER2

  1. Install CyberPanel.
  
  2. Addons and Miscellaneous
  
  3. Exit.
  
  "
read -r -p "  Please enter the number[1-3]: " num
echo ""
case "$num" in
	1)
	interactive_install
	;;
	2)
	interactive_others
	;;
	3)
	exit
	;;
	*)
	echo -e "  Please enter the right number [1-3]\n"
	exit
	;;
esac
}

interactive_others() {
if [ ! -e "/etc/cyberpanel/machineIP" ]; then
echo -e "\nYou don't have CyberPanel installed...\n"
exit
fi

echo -e "		CyberPanel Addons v$CP_VER1$CP_VER2

  1. Install Memcached extension and backend
	
  2. Install Redis extension and backend
	
  3. Return to main page.
	
  4. Exit
  "
 
echo && read -r -p "Please enter the number[1-4]: " num
case "$num" in
	1)
	memcached_installation
	exit
	;;
	2)
	redis_installation
	exit
	;;
	3)
	interactive_mode
	;;
	4)
	exit
	;;
	*)
	echo -e "please enter the right number [1-4]"
	;;
esac
}

interactive_install() {
RAM=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
DISK=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
#clear
echo -e "		CyberPanel Installer v$CP_VER1$CP_VER2

  RAM check : $RAM 
  
  Disk check : $DISK (Minimal \e[31m${MIN_DISK_SPACE_GB}GB\e[39m free space)

  1. Install CyberPanel with \e[31mOpenLiteSpeed\e[39m.
  
  2. Install Cyberpanel with \e[31mLiteSpeed Enterprise\e[39m.
  
  3. Exit.
  
  "
read -r -p "  Please enter the number[1-3]: " num
echo ""
case "$num" in
	1)
	VERSION="OLS"
	;;
	2)
	license_input
	;;
	3)
	exit
	;;
	*)
	echo -e "  Please enter the right number [1-3]\n"
	exit
	;;
esac

#above comment for future use

if [[ $DEV_ARG == "ON" ]] ; then
echo -e "\nDo you want to specify which branch you want to install?"
echo -e "\nNOTE: this feature is only for developers "
echo -e "\nonly use this feature if you are a \e[31mdeveloper\e[39m"
#echo -e "\nPlease press Enter key or n to proceed as normal user"
#echo -e "\nPlease enter \e[31mdeveloper\e[39m to confirm you want to use this feature"
#printf "%s" ""
#read TMP_YN

#if [[ $TMP_YN == "developer" ]] ; then
	DEV="ON"
	echo -e "\nPlease specify branch name"
	printf "%s" ""
	read -r TMP_YN
	BRANCH_NAME=$TMP_YN
	echo -e "Branch name set to $BRANCH_NAME"
#else
#	DEV="OFF"
#fi
fi

echo -e "\nPlease choose to use default admin password \e[31m1234567\e[39m, randomly generate one \e[31m(recommended)\e[39m or specify the admin password?"
printf "%s" "Choose [d]fault, [r]andom or [s]et password: [d/r/s] "
read -r TMP_YN

if [[ $TMP_YN =~ ^(d|D| ) ]] || [[ -z $TMP_YN ]]; then
	ADMIN_PASS="$DEFAULT_ADMIN_PASS"
	echo -e "\nAdmin password will be set to $ADMIN_PASS\n"
elif [[ $TMP_YN =~ ^(r|R) ]] ; then
	ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c $RANDOM_PASSWORD_LENGTH ; echo '')
	echo -e "\nAdmin password will be provided once installation is completed...\n"
elif [[ $TMP_YN =~ ^(s|S) ]] ; then
	echo -e "\nPlease enter your password:"
	printf "%s" ""
	read -r TMP_YN
		if [ -z "$TMP_YN" ] ; then
  		echo -e "\nPlease do not use empty string...\n"
			exit 1
		fi
		if [ ${#TMP_YN} -lt $MIN_PASSWORD_LENGTH ] ; then
			echo -e "\nPassword length less than $MIN_PASSWORD_LENGTH characters, please choose a more complicated password.\n"
			exit 1
		fi
	TMP_YN1=$TMP_YN
	echo -e "\nPlease confirm  your password:\n"
	printf "%s" ""
	read -r TMP_YN
	if [ -z "$TMP_YN" ] ; then
  	echo -e "\nPlease do not use empty string...\n"
		exit 1
	fi
	TMP_YN2=$TMP_YN
	if [ "$TMP_YN1" = "$TMP_YN2" ] ; then
		ADMIN_PASS=$TMP_YN1
	else
		echo -e "\nRepeated password didn't match , please check...\n"
		exit 1
	fi
else
	ADMIN_PASS="$DEFAULT_ADMIN_PASS"
	echo -e "\nAdmin password will be set to $ADMIN_PASS\n"
fi

echo -e "\nDo you wish to install Memcached extension and backend?"
printf "%s" "Please select [Y/n]: "
read -r TMP_YN
if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
	MEMCACHED="OFF"
else
	MEMCACHED="ON"
fi

echo -e "\nDo you wish to install Redis extension and backend?"
printf "%s" "Please select [Y/n]: "
read -r TMP_YN
if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
	REDIS="OFF"
else
	REDIS="ON"
fi
}

main_install() {

if [[ -e /usr/local/CyberCP ]] ; then
	echo -e "\n CyberPanel already installed, exiting..."
#exit
fi
	
special_change

if [[ $VERSION == "ENT" ]] ; then
	echo -e "\nValidating the license..."
	echo -e "\nThis may take a minute..."
	echo -e "\nplease be patient...\n\n"
	license_validation
	SERIAL_NO="--ent ent --serial "
fi

sed -i 's|lsws-5.4.2|lsws-'"$LSWS_STABLE_VER"'|g' installCyberPanel.py
sed -i 's|lsws-5.3.5|lsws-'"$LSWS_STABLE_VER"'|g' installCyberPanel.py
#this sed must be done after license validation
	
echo -e "Preparing..."
echo -e "Installation will start in $INSTALLATION_DELAY_SECONDS seconds, if you wish to stop please press CTRL + C"
sleep $INSTALLATION_DELAY_SECONDS
debug="1"
if [[ $debug == "0" ]] ; then
	echo "/usr/local/CyberPanel/bin/python2 install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY"
	exit
fi

if [[ $debug == "1" ]] ; then
	if [[ $DEV == "ON" ]] ; then
	/usr/local/CyberPanel/bin/python install.py "$SERVER_IP" "$SERIAL_NO" "$LICENSE_KEY"
	else
	/usr/local/CyberPanel/bin/python2 install.py "$SERVER_IP" "$SERIAL_NO" "$LICENSE_KEY"
	fi
	
	if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt > /dev/null; then 
		echo -e "\nCyberPanel installation sucessfully completed..."
else
	echo -e "Oops, something went wrong..."
	exit
fi

if [[ $MEMCACHED == "ON" ]] ; then
	memcached_installation
fi
if [[ $REDIS == "ON" ]] ; then
	redis_installation
fi
	after_install
fi
}

pip_virtualenv() {
if [[ $DEV == "OFF" ]] ; then
if [[ $SERVER_COUNTRY == "CN" ]] ; then
	mkdir /root/.pip
cat << EOF > /root/.pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/ 
EOF
fi

if [[ $PROVIDER == "Alibaba Cloud" ]] ; then
	pip install --upgrade pip
	pip install setuptools==40.8.0
fi

pip install virtualenv

# Create virtual environment with fallback for Ubuntu 22.04 compatibility
echo "Creating CyberPanel virtual environment..."
if python3 -m venv --system-site-packages /usr/local/CyberPanel 2>&1 | grep -q "unrecognized option"; then
    # Fallback to virtualenv if python3 -m venv doesn't support --system-site-packages
    virtualenv --system-site-packages /usr/local/CyberPanel
elif python3 -m venv --system-site-packages /usr/local/CyberPanel 2>/dev/null; then
    echo "Virtual environment created successfully using python3 -m venv"
else
    # Final fallback to virtualenv
    virtualenv --system-site-packages /usr/local/CyberPanel
fi

# shellcheck disable=SC1091
source /usr/local/CyberPanel/bin/activate
rm -rf requirements.txt
wget -O requirements.txt "$GITHUB_RAW_URL/1.8.0/requirements.txt"
pip install --ignore-installed -r requirements.txt
fi

if [[ $DEV == "ON" ]] ; then
	#install dev branch 
	#wget https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirements.txt
	cd /usr/local/ || exit
	python3.6 -m venv CyberPanel
	# shellcheck disable=SC1091
	source /usr/local/CyberPanel/bin/activate
	wget -O requirements.txt "$GITHUB_RAW_URL/$BRANCH_NAME/requirements.txt"
	pip3.6 install --ignore-installed -r requirements.txt
fi

if [ -f requirements.txt ] && [ -d cyberpanel ] ; then
	rm -rf cyberpanel
	rm -f requirements.txt
fi

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	wget $CYBERPANEL_SH_URL/cyberpanel-git.tar.gz
	tar xzvf cyberpanel-git.tar.gz > /dev/null
	cp -r cyberpanel /usr/local/cyberpanel
	cd cyberpanel/install || exit
else
	if [[ $DEV == "ON" ]] ; then
	git clone "$GITHUB_REPO_URL"
	cd cyberpanel || exit
	git checkout "$BRANCH_NAME"
	cd - || exit
	cd cyberpanel/install || exit
	else
	git clone "$GITHUB_REPO_URL"
	cd cyberpanel/install || exit
	fi
fi
curl $CYBERPANEL_SH_URL/?version
}

after_install() {
if [ ! -d "/var/lib/php" ]; then
	mkdir /var/lib/php
fi

if [ ! -d "/var/lib/php/session" ]; then
	mkdir /var/lib/php/session
fi

chmod 1733 /var/lib/php/session

if grep "\[ERROR\] We are not able to run ./install.sh return code: 1.  Fatal error, see /var/log/installLogs.txt for full details" /var/log/installLogs.txt > /dev/null; then 
	cd "${DIR}/cyberpanel/install/lsws-*" || exit
	./install.sh
	echo -e "\n\n\nIt seems LiteSpeed Enterprise has failed to install, please check your license key is valid"
	echo -e "\nIf this license key has been used before, you may need to go to store to release it first."
	exit
fi


if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt > /dev/null; then

if [[ $DEV == "ON" ]] ; then
python3.6 -m venv /usr/local/CyberCP
# shellcheck disable=SC1091
source /usr/local/CyberCP/bin/activate
	wget -O requirements.txt "$GITHUB_RAW_URL/$BRANCH_NAME/requirements.txt"
pip3.6 install --ignore-installed -r requirements.txt
systemctl restart lscpd
fi

for version in /usr/local/lsws/lsphp*;
	do
		php_ini=$(find "/usr/local/lsws/$version/" -name php.ini)
		version2=${version:5:2}
		version2=$(awk "BEGIN { print \"${version2}/10\" }")
				if [[ $version2 = "7" ]] ; then
					version2="7.0"
				fi
		if [[ $SERVER_OS == "CentOS" ]] ; then
		yum remove -y "$version-mysql"
		yum install -y "$version-mysqlnd"
		yum install -y "$version-devel" make gcc glibc-devel libmemcached-devel zlib-devel
			if [[ ! -d /usr/local/lsws/$version/tmp ]] ; then
				mkdir "/usr/local/lsws/$version/tmp"
			fi
		/usr/local/lsws/"${version}"/bin/pecl channel-update pecl.php.net; 
		/usr/local/lsws/"${version}"/bin/pear config-set temp_dir /usr/local/lsws/"${version}"/tmp
		/usr/local/lsws/"${version}"/bin/pecl install timezonedb
		echo "extension=timezonedb.so" > /usr/local/lsws/"${version}"/etc/php.d/20-timezone.ini
		sed -i 's|expose_php = On|expose_php = Off|g' "$php_ini"
		sed -i 's|mail.add_x_header = On|mail.add_x_header = Off|g' "$php_ini"
		sed -i 's|;session.save_path = "/tmp"|session.save_path = "/var/lib/php/session"|g' "$php_ini"
		fi
		
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			if [[ ! -d /usr/local/lsws/cyberpanel-tmp ]] ; then
				echo "yes" > /etc/pure-ftpd/conf/ChrootEveryone
				systemctl restart pure-ftpd-mysql
				DEBIAN_FRONTEND=noninteractive apt install libmagickwand-dev pkg-config build-essential -y
				mkdir /usr/local/lsws/cyberpanel-tmp
				cd /usr/local/lsws/cyberpanel-tmp || exit
				wget https://pecl.php.net/get/timezonedb-2019.3.tgz
				tar xzvf timezonedb-2019.3.tgz
				cd timezonedb-2019.3 || exit
			fi
		/usr/local/lsws/"${version}"/bin/phpize
		./configure --with-php-config=/usr/local/lsws/"${version}"/bin/php-config"${version2}"
		make
		make install
		echo "extension=timezonedb.so" > /usr/local/lsws/"${version}"/etc/php/"${version2}"/mods-available/20-timezone.ini
		make clean
	fi
done

rm -rf /etc/profile.d/cyberpanel*
curl --silent -o /etc/profile.d/cyberpanel.sh https://cyberpanel.sh/?banner 2>/dev/null
chmod +x /etc/profile.d/cyberpanel.sh
RAM2=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
DISK2=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
ELAPSED="$((SECONDS / 3600)) hrs $(((SECONDS / 60) % 60)) min $((SECONDS % 60)) sec"
#MYSQLPASSWD=$(cat /etc/cyberpanel/mysqlPassword)
echo "$ADMIN_PASS" > /etc/cyberpanel/adminPass
/usr/local/CyberPanel/bin/python2 /usr/local/CyberCP/plogical/adminPass.py --password "$ADMIN_PASS"
systemctl restart lscpd
systemctl restart lsws
echo "/usr/local/CyberPanel/bin/python2 /usr/local/CyberCP/plogical/adminPass.py --password \$@" > /usr/bin/adminPass
echo "systemctl restart lscpd" >> /usr/bin/adminPass
chmod +x /usr/bin/adminPass
if [[ $VERSION = "OLS" ]] ; then
	WORD="OpenLiteSpeed"
#	sed -i 's|maxConnections               10000|maxConnections               100000|g' /usr/local/lsws/conf/httpd_config.conf
#	OLS_LATEST=$(curl https://openlitespeed.org/packages/release)
#	wget https://openlitespeed.org/packages/openlitespeed-$OLS_LATEST.tgz
#	tar xzvf openlitespeed-$OLS_LATEST.tgz
#	cd openlitespeed
#	./install.sh
	/usr/local/lsws/bin/lswsctrl stop
	/usr/local/lsws/bin/lswsctrl start
#	rm -f openlitespeed-$OLS_LATEST.tgz
#	rm -rf openlitespeed
#	cd ..
fi
if [[ $VERSION = "ENT" ]] ; then
	WORD="LiteSpeed Enterprise"
	if [[ $SERVER_COUNTRY != "CN" ]] ; then
		/usr/local/lsws/admin/misc/lsup.sh -f -v "$LSWS_STABLE_VER"
	fi
fi

if systemctl status lsws > /dev/null 2>&1; then
	echo "LSWS service is running..."
else
	systemctl stop lsws
	systemctl start lsws
fi

clear
echo "###################################################################"
echo "                CyberPanel Successfully Installed                  "
echo "                                                                   "
echo "                Current Disk usage : $DISK2                        "
echo "                                                                   "
echo "                Current RAM  usage : $RAM2                         "
echo "                                                                   "
echo "                Installation time  : $ELAPSED                      "
echo "                                                                   "
echo "                Visit: https://$SERVER_IP:$CYBERPANEL_PORT                     "
echo "                Panel username: admin                              "
echo "                Panel password: $ADMIN_PASS                            "
#echo "                Mysql username: root                               "
#echo "                Mysql password: $MYSQLPASSWD                       "
echo "                                                                   "
echo "            Please change your default admin password              "
echo "          If you need to reset your panel password, please run:    "
echo "        	adminPass YOUR_NEW_PASSWORD     					   "
echo "                                                                   "
echo "          If you change mysql password, please  modify file in     "
echo -e "         \e[31m/etc/cyberpanel/mysqlPassword\e[39m with new password as well   "
echo "                                                                   "
echo "              Website : https://www.cyberpanel.net                 "
echo "              Forums  : https://forums.cyberpanel.net              "
echo "              Wikipage: https://docs.cyberpanel.net                "
echo "                                                                   "
echo -e "            Enjoy your accelerated Internet by                  "
echo -e "                CyberPanel & $WORD					                     "
echo "###################################################################"
if [[ $PROVIDER != "undefined" ]] ; then
	echo -e "\033[0;32m$PROVIDER\033[39m detected..."
	echo -e "This provider has a \e[31mnetwork-level firewall\033[39m"
else
	echo -e "If your provider has a \e[31mnetwork-level firewall\033[39m"
fi
	echo -e "Please make sure you have opened following port for both in/out:"
	echo -e "\033[0;32mTCP: $CYBERPANEL_PORT\033[39m for CyberPanel"
	echo -e "\033[0;32mTCP: 80\033[39m, \033[0;32mTCP: 443\033[39m and \033[0;32mUDP: 443\033[39m for webserver"
	echo -e "\033[0;32mTCP: 21\033[39m and \033[0;32mTCP: 40110-40210\033[39m for FTP"
	echo -e "\033[0;32mTCP: 25\033[39m, \033[0;32mTCP: 587\033[39m, \033[0;32mTCP: 465\033[39m, \033[0;32mTCP: 110\033[39m, \033[0;32mTCP: 143\033[39m and \033[0;32mTCP: 993\033[39m for mail service"
	echo -e "\033[0;32mTCP: 53\033[39m and \033[0;32mUDP: 53\033[39m for DNS service"
if [[ $SERVER_COUNTRY = CN ]] ; then
	if [[ $PROVIDER == "Tencent Cloud" ]] ; then
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			rm -f /etc/apt/sources.list 
			mv /etc/apt/sources.list-backup /etc/apt/sources.list
			echo "nameserver 127.0.0.53
options edns0" > /run/systemd/resolve/stub-resolv.conf
			echo "nameserver 127.0.0.53
options edns0" > /etc/resolv.conf
			apt update
#revert the previous change on tencent cloud repo.
		fi
	fi
	if [[ $VERSION = "ENT" ]] ; then
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/install/installCyberPanel.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://'"$DOWNLOAD_SERVER"'/litespeed/lsws-'"$LSWS_STABLE_VER"'-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		echo -e "If you have install LiteSpeed Enterprise, please run \e[31m/usr/local/lsws/admin/misc/lsup.sh\033[39m to update it to latest."
	fi
fi

sed -i 's|lsws-5.3.8|lsws-'"$LSWS_STABLE_VER"'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.4.2|lsws-'"$LSWS_STABLE_VER"'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.3.5|lsws-'"$LSWS_STABLE_VER"'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py

if [[ $SILENT != "ON" ]] ; then
printf "%s" "Would you like to restart your server now? [y/N]: "
read -r TMP_YN

if [[ "$TMP_YN" = "N" ]] || [[ "$TMP_YN" = "n" ]] || [[ -z "$TMP_YN" ]]; then
:
else
reboot
exit
fi

exit
fi
#replace URL for CN



else
echo "something went wrong..."
exit
fi
}

argument_mode() {
KEY_SIZE=${#VERSION}
TMP=$(echo "$VERSION" | cut -c5)
TMP2=$(echo "$VERSION" | cut -c10)
TMP3=$(echo "$VERSION" | cut -c15)
if [[ $VERSION == "OLS" || $VERSION == "ols" ]] ; then
	VERSION="OLS"
	echo -e "\nSet to OpenLiteSpeed..."
elif [[ $VERSION == "Trial" ]] || [[ $VERSION == "TRIAL" ]] || [[ $VERSION == "trial" ]] ; then
	VERSION="ENT"
	LICENSE_KEY="TRIAL"
	echo -e "\nLiteSpeed Enterprise trial license set..."
elif [[ $TMP == "-" ]] && [[ $TMP2 == "-" ]] && [[ $TMP3 == "-" ]] && [[ $KEY_SIZE == "19" ]] ; then
	LICENSE_KEY=$VERSION
	VERSION="ENT"
	echo -e "\nLiteSpeed Enterprise license key set..."
else
	echo -e "\nCan not recognize the input value \e[31m$VERSION\e[39m "
	echo -e "\nPlease verify the input value..."
	echo -e "\nPlease run with \e[31m-h\e[39m or \e[31m--help\e[39m for more detail."
	exit
fi

if [[ $ADMIN_PASS == "d" ]] ; then
	ADMIN_PASS="1234567"
	echo -e "\nSet to default password..."
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
elif [[ $ADMIN_PASS == "r" ]] ; then
	ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c $RANDOM_PASSWORD_LENGTH ; echo '')
	echo -e "\nSet to random-generated password..."
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
	echo "$ADMIN_PASS"
else
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
fi
}

if [ $# -eq 0 ] ; then
	echo -e "\nInitializing...\n"
else
	if [[ $1 == "help" ]] ; then
	show_help
	exit
	elif [[ $1 == "dev" ]] ; then
		DEV="ON"
		DEV_ARG="ON"
		SILENT="OFF"
	elif [[ $1 == "default" ]] ; then
	echo -e "\nThis will start default installation...\n"
	SILENT="ON"
	VERSION="OLS"
	ADMIN_PASS="1234567"
	MEMCACHED="ON"
	REDIS="ON"
	else
		while [ -n "${1}" ]; do
			case $1 in
				-v | --version) shift
						if [ "${1}" = '' ]; then
							show_help
							exit
						else
							VERSION="${1}"
							SILENT="ON"
						fi
						;;
				-p | --password) shift
						if [[ "${1}" == '' ]]; then
							ADMIN_PASS="1234567"
						elif [[ "${1}" == 'r' ]] || [[ "$1" == 'random' ]] ; then
							ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c $RANDOM_PASSWORD_LENGTH ; echo '')
						else
							if [ "${#1}" -lt 8 ] ; then
								echo -e "\nPassword lenth less than 8 digital, please choose a more complicated password.\n"
								exit
							fi
							ADMIN_PASS="${1}"
						fi
        		;;
				-a | --addons)
						MEMCACHED="ON"
						REDIS="ON"
        		;;
				-m | --minimal)
						echo "minimal installation is still work in progress..."
						exit
        		;;
				-h | --help)
						show_help
						exit
        		;;
				*)
						echo "unknown argument..."
						show_help
						exit
        		;;
			esac
			shift
			done
			fi
fi



SERVER_IP=$(curl --silent --max-time 10 -4 https://cyberpanel.sh/?ip)
if [[ $SERVER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo -e "Valid IP detected..."
else
	echo -e "Can not detect IP, exit..."
	exit
fi
SERVER_COUNTRY="unknow"
SERVER_COUNTRY=$(curl --silent --max-time 5 https://cyberpanel.sh/?country)
if [[ ${#SERVER_COUNTRY} == "2" ]] || [[ ${#SERVER_COUNTRY} == "6" ]] ; then
	echo -e "\nChecking server..."
	else
	echo -e "\nChecking server..."
	SERVER_COUNTRY="unknow"
fi
#SERVER_COUNTRY="CN"
#test string
if [[ $SERVER_COUNTRY == "CN" ]] ; then
DOWNLOAD_SERVER="cyberpanel.sh"
else
DOWNLOAD_SERVER="$CYBERPANEL_CDN_URL"
fi

check_OS
check_root
check_panel
check_process
check_provider





if [[ $SILENT = "ON" ]] ; then
argument_mode
else
interactive_mode
fi

SECONDS=0
install_required

pip_virtualenv

system_tweak

main_install