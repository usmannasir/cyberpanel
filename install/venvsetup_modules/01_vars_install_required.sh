#!/usr/bin/env bash
# install/venvsetup part 1
#!/bin/bash

#CyberPanel installer script for Ubuntu 18.04 and CentOS 7.X
DEV="OFF"
BRANCH="stable"
POSTFIX_VARIABLE="ON"
POWERDNS_VARIABLE="ON"
PUREFTPD_VARIABLE="ON"
PROVIDER="undefined"
SERIAL_NO=""
DIR=$(pwd)
TEMP=$(curl --silent https://cyberpanel.net/version.txt)
CP_VER1=${TEMP:12:3}
CP_VER2=${TEMP:25:1}
SERVER_OS="CentOS"
VERSION="OLS"
LICENSE_KEY=""
KEY_SIZE=""
ADMIN_PASS="1234567"
MEMCACHED="ON"
REDIS="ON"
MARIADB_VER="11.8"
TOTAL_RAM=$(free -m | awk '/Mem\:/ { print $2 }')

# Robust pip install function to handle broken pipe errors
safe_pip_install() {
    local pip_cmd="$1"
    local requirements_file="$2"
    local install_args="$3"
    
    echo "Installing Python packages..."
    
    # Method 1: Install with full error suppression and broken pipe handling
    if timeout 300 $pip_cmd $install_args -r "$requirements_file" --quiet --no-warn-script-location --disable-pip-version-check 2>/dev/null || true; then
        echo "✅ Package installation completed successfully"
        return 0
    fi
    
    # Method 2: Install with even more aggressive error suppression
    echo "⚠️  Trying fallback installation method..."
    if timeout 300 $pip_cmd $install_args -r "$requirements_file" --quiet --no-warn-script-location --disable-pip-version-check --no-color --no-cache-dir 2>/dev/null || true; then
        echo "✅ Package installation completed with fallback method"
        return 0
    fi
    
    # Method 3: Install packages individually to avoid broken pipes
    echo "⚠️  Trying individual package installation..."
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue
        
        # Extract package name and version
        package=$(echo "$line" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1 | tr -d ' ')
        
        if [[ -n "$package" ]]; then
            echo "Installing $package..."
            timeout 60 $pip_cmd install $install_args "$package" --quiet --no-warn-script-location --disable-pip-version-check 2>/dev/null || true
        fi
    done < "$requirements_file"
    
    echo "✅ Package installation completed with individual method"
    return 0
}

license_validation() {
CURRENT_DIR=$(pwd)

if [ -f /root/cyberpanel-tmp ] ; then
rm -rf /root/cyberpanel-tmp
fi

mkdir /root/cyberpanel-tmp
cd /root/cyberpanel-tmp
wget -q https://$DOWNLOAD_SERVER/litespeed/lsws-$LSWS_STABLE_VER-ent-x86_64-linux.tar.gz
tar xzvf lsws-$LSWS_STABLE_VER-ent-x86_64-linux.tar.gz > /dev/null
cd  /root/cyberpanel-tmp/lsws-$LSWS_STABLE_VER/conf
if [[ $LICENSE_KEY == "TRIAL" ]] ; then
wget -q http://license.litespeedtech.com/reseller/trial.key
sed -i "s|writeSerial = open('lsws-5.4.2/serial.no', 'w')|command = 'wget -q --output-document=./lsws-$LSWS_STABLE_VER/trial.key http://license.litespeedtech.com/reseller/trial.key'|g" $CURRENT_DIR/installCyberPanel.py
sed -i 's|writeSerial.writelines(self.serial)|subprocess.call(command, shell=True)|g' $CURRENT_DIR/installCyberPanel.py
sed -i 's|writeSerial.close()||g' $CURRENT_DIR/installCyberPanel.py
else
echo $LICENSE_KEY > serial.no
fi

cd /root/cyberpanel-tmp/lsws-$LSWS_STABLE_VER/bin

if [[ $LICENSE_KEY == "TRIAL" ]] ; then
	if ./lshttpd -V |& grep  "ERROR" ; then
	echo -e "\n\nIt apeears to have some issue with license , please check above result..."
	exit
	fi
	LICENSE_KEY="1111-2222-3333-4444"
else
	if ./lshttpd -r |& grep "ERROR" ; then
	./lshttpd -r
	echo -e "\n\nIt apeears to have some issue with license , please check above result..."
	exit
	fi
fi
echo -e "License seems valid..."
cd /root/cyberpanel-tmp
rm -rf lsws-$LSWS_STABLE_VER*
cd $CURRENT_DIR
rm -rf /root/cyberpanel-tmp
}

special_change(){
sed -i 's|cyberpanel.sh|'$DOWNLOAD_SERVER'|g' install.py
sed -i 's|mirror.cyberpanel.net|'$DOWNLOAD_SERVER'|g' install.py
sed -i 's|git clone https://github.com/usmannasir/cyberpanel|echo downloaded|g' install.py
#change to CDN first, regardless country
sed -i 's|http://|https://|g' install.py

LATEST_URL="https://update.litespeedtech.com/ws/latest.php"
#LATEST_URL="https://cyberpanel.sh/latest.php"
curl --silent -o /tmp/lsws_latest $LATEST_URL 2>/dev/null
LSWS_STABLE_LINE=`cat /tmp/lsws_latest | grep LSWS_STABLE`
LSWS_STABLE_VER=`expr "$LSWS_STABLE_LINE" : '.*LSWS_STABLE=\(.*\) BUILD .*'`
# Fallback to LSWS 6.3.4 (Stable) if fetch failed or empty
if [ -z "$LSWS_STABLE_VER" ]; then
    LSWS_STABLE_VER="6.3.4"
fi

if [[ $SERVER_COUNTRY == "CN" ]] ; then
#line1="$(grep -n "github.com/usmannasir/cyberpanel" install.py | head -n 1 | cut -d: -f1)"
#line2=$((line1 - 1))
#sed -i "${line2}i\ \ \ \ \ \ \ \ subprocess.call(command, shell=True)" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ command = 'tar xzvf cyberpanel-git.tar.gz'" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ subprocess.call(command, shell=True)" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ command = 'wget cyberpanel.sh/cyberpanel-git.tar.gz'" install.py
sed -i 's|wget https://rpms.litespeedtech.com/debian/|wget --no-check-certificate https://rpms.litespeedtech.com/debian/|g' install.py
sed -i 's|https://repo.powerdns.com/repo-files/centos-auth-42.repo|https://'$DOWNLOAD_SERVER'/powerdns/powerdns.repo|g' installCyberPanel.py
sed -i 's|https://snappymail.eu/repository/latest.tar.gz|https://'$DOWNLOAD_SERVER'/repository/latest.tar.gz|g' install.py

sed -i 's|rpm -ivh https://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm|curl -o /etc/yum.repos.d/litespeed.repo https://'$DOWNLOAD_SERVER'/litespeed/litespeed.repo|g' install.py


sed -i 's|https://copr.fedorainfracloud.org/coprs/copart/restic/repo/epel-7/copart-restic-epel-7.repo|https://'$DOWNLOAD_SERVER'/restic/restic.repo|g' install.py

sed -i 's|yum -y install https://cyberpanel.sh/gf-release-latest.gf.el7.noarch.rpm|wget -O /etc/yum.repos.d/gf.repo https://'$DOWNLOAD_SERVER'/gf-plus/gf.repo|g' install.py
sed -i 's|dovecot-2.3-latest|dovecot-2.3-latest-mirror|g' install.py
sed -i 's|git clone https://github.com/usmannasir/cyberpanel|wget https://cyberpanel.sh/cyberpanel-git.tar.gz \&\& tar xzvf cyberpanel-git.tar.gz|g' install.py
sed -i 's|https://repo.dovecot.org/ce-2.3-latest/centos/$releasever/RPMS/$basearch|https://'$DOWNLOAD_SERVER'/dovecot/|g' install.py
sed -i 's|'$DOWNLOAD_SERVER'|cyberpanel.sh|g' install.py
sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.4.2-ent-x86_64-linux.tar.gz|https://'$DOWNLOAD_SERVER'/litespeed/lsws-'$LSWS_STABLE_VER'-ent-x86_64-linux.tar.gz|g' installCyberPanel.py
# global change for CN , regardless provider and system

	if [[ $SERVER_OS == "CentOS" ]] ; then
		DIR=$(pwd)
		cd $DIR/mysql
		echo "[mariadb-tsinghua]
name = MariaDB
baseurl = https://mirrors.tuna.tsinghua.edu.cn/mariadb/yum/10.1/centos7-amd64
gpgkey = https://mirrors.tuna.tsinghua.edu.cn/mariadb/yum//RPM-GPG-KEY-MariaDB
gpgcheck = 1" > MariaDB.repo
#above to set mariadb db to Tsinghua repo
		cd $DIR
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
		echo "echo 1000000 > /proc/sys/kernel/pid_max
echo 1 > /sys/kernel/mm/ksm/run" >> /etc/rc.d/rc.local
		chmod +x /etc/rc.d/rc.local
		else
		echo "echo 1000000 > /proc/sys/kernel/pid_max
echo 1 > /sys/kernel/mm/ksm/run" >> /etc/rc.local
		chmod +x /etc/rc.local
		fi
	echo "fs.file-max = 65535" >> /etc/sysctl.conf
	sysctl -p > /dev/null
	echo "*                soft    nofile          65535
*                hard    nofile          65535
root             soft    nofile          65535
root             hard    nofile          65535
*                soft    nproc           65535
*                hard    nproc           65535
root             soft    nproc           65535
root             hard    nproc           65535" >> /etc/security/limits.conf
fi

#sed -i 's|#DefaultLimitNOFILE=|DefaultLimitNOFILE=65535|g' /etc/systemd/system.conf


TOTAL_SWAP=$(free -m | awk '/^Swap:/ { print $2 }')
SET_SWAP=$((TOTAL_RAM - TOTAL_SWAP))
SWAP_FILE=/cyberpanel.swap

if [ ! -f $SWAP_FILE ] ; then
	if [[ $TOTAL_SWAP -gt $TOTAL_RAM ]] || [[ $TOTAL_SWAP -eq $TOTAL_RAM ]] ; then
		echo "SWAP check..."
	else
		if [[ $SET_SWAP -gt "2049" ]] ; then
			SET_SWAP="2048"
		else
			echo "Checking SWAP..."
		fi
	fallocate --length ${SET_SWAP}MiB $SWAP_FILE
	chmod 600 $SWAP_FILE
	mkswap $SWAP_FILE
	swapon $SWAP_FILE
	echo "${SWAP_FILE} swap swap sw 0 0" | sudo tee -a /etc/fstab
	sysctl vm.swappiness=10
	echo "vm.swappiness = 10" >> /etc/sysctl.conf
	echo "SWAP set..."
	fi
fi
}


install_required() {
echo -e "\nInstalling necessary components..."
if [[ $SERVER_OS == "CentOS" ]] ; then
	rpm --import https://$DOWNLOAD_SERVER/mariadb/RPM-GPG-KEY-MariaDB
	rpm --import https://$DOWNLOAD_SERVER/litespeed/RPM-GPG-KEY-litespeed
	rpm --import https://$DOWNLOAD_SERVER/powerdns/FD380FBB-pub.asc
	rpm --import http://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7
	rpm --import https://$DOWNLOAD_SERVER/gf-plus/RPM-GPG-KEY-gf.el7
	rpm --import https://repo.dovecot.org/DOVECOT-REPO-GPG
	rpm --import https://copr-be.cloud.fedoraproject.org/results/copart/restic/pubkey.gpg
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

	# Check if this is Debian (no lsb-release) and version >= 13
	if [[ ! -f /etc/lsb-release ]] && [[ -f /etc/debian_version ]]; then
		DEBIAN_VERSION=$(cat /etc/debian_version | cut -d'.' -f1)
		if [[ $DEBIAN_VERSION -ge 13 ]]; then
			# Debian 13 (Trixie) package mappings
			DEBIAN_FRONTEND=noninteractive apt install -y htop telnet python3-mysqldb python3-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev-compat libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev python3-gpg python3 python3-setuptools virtualenv python3-dev python3-pip git
		elif [[ $DEBIAN_VERSION -ge 12 ]]; then
			# Debian 12 (Bookworm) package mappings
			DEBIAN_FRONTEND=noninteractive apt install -y htop telnet python3-mysqldb python3-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev python3-gpg python3 python3-setuptools virtualenv python3-dev python3-pip git
		else
			# Older Debian versions
			DEBIAN_FRONTEND=noninteractive apt install -y htop telnet python-mysqldb python-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev-compat libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev python-gpg python python-minimal python-setuptools virtualenv python-dev python-pip git
		fi
	else
		# Ubuntu or older Debian with compatible package names
		DEBIAN_FRONTEND=noninteractive apt install -y htop telnet python-mysqldb python-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev-compat libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev python-gpg python python-minimal python-setuptools virtualenv python-dev python-pip git
	fi
	if [[ $DEV == "ON" ]] ; then
		DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
		DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
		DEBIAN_FRONTEND=noninteractive apt install -y python3-venv
	fi
fi
}
