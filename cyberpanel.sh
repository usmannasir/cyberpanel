#!/bin/bash

#CyberPanel installer script for CentOS 7.X, CentOS 8.X, CloudLinux 7.X and Ubuntu 18.04

SUDO_TEST=$(set)

export LC_CTYPE=en_US.UTF-8
export LC_ALL=en_US.UTF-8
if [[ $? != "0" ]] ; then
	apt upgrade
	DEBIAN_FRONTEND=noninteractive apt install -y locales
	locale-gen "en_US.UTF-8"
	update-locale LC_ALL="en_US.UTF-8"
fi

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
TOTAL_RAM=$(free -m | awk '/Mem\:/ { print $2 }')
CENTOS_8="False"
WATCHDOG="OFF"
BRANCH_NAME="v${TEMP:12:3}.${TEMP:25:1}"

check_return() {
#check previous command result , 0 = ok ,  non-0 = something wrong.
if [[ $? -eq "0" ]] ; then
	:
else
	echo -e "\ncommand failed, exiting..."
	exit
fi
}

install_utility() {
if [[ ! -f /usr/bin/cyberpanel_utility ]] ; then
wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
chmod 700 /usr/bin/cyberpanel_utility
fi

#BASH_PATH="/root/.bashrc"
#if ! cat $BASH_PATH | grep -q cyberpanel_utility ; then
#echo -e "\n\ncyberpanel() {
#if [[ \$1 == \"utility\" ]] ; then
#/usr/bin/cyberpanel_utility \${@:2:99}
#elif [[ \$1 == \"help\" ]] ; then
#/usr/bin/cyberpanel_utility --help
#elif [[ \$1 == \"upgrade\" ]] || [[ \$1 == \"update\" ]] ; then
#/usr/bin/cyberpanel_utility --upgrade
#else
#/usr/bin/cyberpanel \"\$@\"
#fi
#}" >> $BASH_PATH
#fi

}

watchdog_setup() {
if [[ $WATCHDOG == "ON" ]] ; then
wget -O /etc/cyberpanel/watchdog.sh https://$DOWNLOAD_SERVER/misc/watchdog.sh
chmod 700 /etc/cyberpanel/watchdog.sh
ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
pid=$(ps aux | grep "watchdog lsws"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		nohup watchdog lsws > /dev/null 2>&1 &
	fi
echo -e "Checking MariaDB ..."
pid=$(ps aux | grep "watchdog mariadb"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		nohup watchdog mariadb > /dev/null 2>&1 &
	fi

	if [[ $SERVER_OS == "CentOS" ]] ; then
	echo "nohup watchdog lsws > /dev/null 2>&1 &
	nohup watchdog mariadb > /dev/null 2>&1 &" >> /etc/rc.d/rc.local
	else
	echo "nohup watchdog lsws > /dev/null 2>&1 &
	nohup watchdog mariadb > /dev/null 2>&1 &" >> /etc/rc.local
	fi
echo -e "\n Setting up WatchDog..."
fi
}

webadmin_passwd() {
if [[ $VERSION == "OLS" ]] ; then
	php_command="admin_php"
else
	php_command="admin_php5"
fi

WEBADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
TEMP=`/usr/local/lsws/admin/fcgi-bin/${php_command} /usr/local/lsws/admin/misc/htpasswd.php ${WEBADMIN_PASS}`
echo "" > /usr/local/lsws/admin/conf/htpasswd
echo "admin:$TEMP" > /usr/local/lsws/admin/conf/htpasswd
echo ${WEBADMIN_PASS} > /etc/cyberpanel/webadmin_passwd
chmod 600 /etc/cyberpanel/webadmin_passwd
}

check_virtualization() {
echo -e "Checking virtualization type..."
if hostnamectl | grep "Virtualization: lxc" ; then
	echo -e "\nLXC detected..."
	echo -e "CyberPanel does not support LXC"
	echo -e "Exiting..."
	exit
fi
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

if [[ $PROVIDER == "Alibaba Cloud" ]] ; then
	if ! grep -q "100.100.2.136" /etc/resolv.conf ; then
		echo -e "\nnameserver 100.100.2.136" >> /etc/resolv.conf
	fi
	if ! grep -q "100.100.2.138" /etc/resolv.conf ; then
		echo -e "\nnameserver 100.100.2.138" >> /etc/resolv.conf
	fi
else
	if ! grep -q "1.1.1.1" /etc/resolv.conf ; then
		echo -e "\nnameserver 1.1.1.1" >> /etc/resolv.conf
	fi
	if ! grep -q "8.8.8.8" /etc/resolv.conf ; then
		echo -e "\nnameserver 8.8.8.8" >> /etc/resolv.conf
	fi
fi
cp /etc/resolv.conf /etc/resolv.conf-tmp

line1="$(grep -n "f.write('nameserver 8.8.8.8')" installCyberPanel.py | head -n 1 | cut -d: -f1)"
sed -i "${line1}i\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ subprocess.call(command, shell=True)" installCyberPanel.py
sed -i "${line1}i\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ command = 'cat /etc/resolv.conf-tmp > /etc/resolv.conf'" installCyberPanel.py

LATEST_URL="https://update.litespeedtech.com/ws/latest.php"
#LATEST_URL="https://cyberpanel.sh/latest.php"
curl --silent -o /tmp/lsws_latest $LATEST_URL 2>/dev/null
LSWS_STABLE_LINE=`cat /tmp/lsws_latest | grep LSWS_STABLE`
LSWS_STABLE_VER=`expr "$LSWS_STABLE_LINE" : '.*LSWS_STABLE=\(.*\) BUILD .*'`

if [[ $PROVIDER == "Alibaba Cloud" ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
		mkdir /root/.config
		mkdir /root/.config/pip
		cat << EOF > /root/.config/pip/pip.conf
[global]
index-url = https://pypi.python.org/simple/
[install]
trusted-host=pypi.python.org
EOF
		echo -e "\nSet pip repo..."
fi
#seems Alibaba cloud , other than CN , also requires change on ubuntu.

if [[ $SERVER_COUNTRY == "CN" ]] ; then
#line1="$(grep -n "github.com/usmannasir/cyberpanel" install.py | head -n 1 | cut -d: -f1)"
#line2=$((line1 - 1))
#sed -i "${line2}i\ \ \ \ \ \ \ \ subprocess.call(command, shell=True)" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ command = 'tar xzvf cyberpanel-git.tar.gz'" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ subprocess.call(command, shell=True)" install.py
#sed -i "${line2}i\ \ \ \ \ \ \ \ command = 'wget cyberpanel.sh/cyberpanel-git.tar.gz'" install.py
	sed -i 's|wget https://rpms.litespeedtech.com/debian/|wget --no-check-certificate https://rpms.litespeedtech.com/debian/|g' install.py
	sed -i 's|https://repo.powerdns.com/repo-files/centos-auth-42.repo|https://'$DOWNLOAD_SERVER'/powerdns/powerdns.repo|g' installCyberPanel.py
	sed -i 's|https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip|https://'$DOWNLOAD_SERVER'/misc/rainloop-community-latest.zip|g' install.py
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
		mkdir /root/.config
		mkdir /root/.config/pip
		cat << EOF > /root/.config/pip/pip.conf
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
[install]
trusted-host=pypi.tuna.tsinghua.edu.cn
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
		pip config set global.index-url https://pypi.python.org/simple/
		mkdir /root/.config
		mkdir /root/.config/pip
		cat << EOF > /root/.config/pip/pip.conf
[global]
index-url = https://pypi.python.org/simple/
[install]
trusted-host=pypi.python.org
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
number=$(grep -n "127.0.0.1" /etc/hosts |  cut -d: -f 1)
my_hostname=$(hostname)

	if [[ ! -z $number ]] ; then
		for number2 in $number;
			do
				string=$(sed "${number2}q;d" /etc/hosts)
				if [[ "$string" == *"$my_hostname"* ]] ; then
		  	:
		  	else
		  	new_string="$string $my_hostname"
		  	sed -i "${number2}s/.*/${new_string}/" /etc/hosts
		  	fi
			done
	else
		echo "127.0.0.1 $my_hostname " >> /etc/hosts
	fi

#this should address on "sudo: unable to resolve host ..." on Ubuntu , it's not issue but annoying.

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
	timeout 10 rpm --import https://$DOWNLOAD_SERVER/mariadb/RPM-GPG-KEY-MariaDB
	timeout 10 rpm --import https://$DOWNLOAD_SERVER/litespeed/RPM-GPG-KEY-litespeed
	timeout 10 rpm --import https://$DOWNLOAD_SERVER/powerdns/FD380FBB-pub.asc
	timeout 10 rpm --import http://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7
	timeout 10 rpm --import https://$DOWNLOAD_SERVER/gf-plus/RPM-GPG-KEY-gf.el7
	timeout 10 rpm --import https://repo.dovecot.org/DOVECOT-REPO-GPG
	timeout 10 rpm --import https://copr-be.cloud.fedoraproject.org/results/copart/restic/pubkey.gpg
	yum clean all
	yum update -y
	yum autoremove epel-release -y
	rm -f /etc/yum.repos.d/epel.repo
	rm -f /etc/yum.repos.d/epel.repo.rpmsave
	yum install epel-release -y

	if [[ $CENTOS_8 == "False" ]] ; then
	  yum install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc python-devel libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel python-pip git
		check_return
	fi
	if [[ $CENTOS_8 == "True" ]] ; then
		yum install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git platform-python-devel tar
		check_return
		dnf --enablerepo=PowerTools install gpgme-devel -y
		check_return
	fi

if [[ $DEV == "ON" ]] ; then
	  if [[ $CENTOS_8 == "False" ]] ; then
      yum -y install yum-utils
      yum -y groupinstall development
      yum -y install https://centos7.iuscommunity.org/ius-release.rpm
      yum -y install python36u python36u-pip python36u-devel
			check_return
    fi
    if [[ $CENTOS_8 == "True" ]] ; then
      dnf install python3 -y
			check_return
    fi
    if [[ $SERVER_OS == "CentOS" ]] ; then
      pip3.6 install virtualenv==16.7.9
    else
      pip3.6 install virtualenv
    fi
		check_return
	fi
fi

if [[ $SERVER_OS == "Ubuntu" ]] ; then
	apt update -y
	DEBIAN_FRONTEND=noninteractive apt upgrade -y
	DEBIAN_FRONTEND=noninteracitve apt install -y htop telnet python-mysqldb python-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadbclient-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev python-gpg python python-minimal python-setuptools virtualenv python-dev python-pip git
	check_return
	if [[ $DEV == "ON" ]] ; then
		DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
		check_return
		DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
		check_return
		DEBIAN_FRONTEND=noninteractive apt install -y python3-venv
		check_return
	fi
fi
}

memcached_installation() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp74-memcached lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached lsphp56-pecl-memcached lsphp55-pecl-memcached lsphp54-pecl-memcached
		if [[ $TOTAL_RAM -eq "2048" ]] || [[ $TOTAL_RAM -gt "2048" ]] ; then
			yum groupinstall "Development Tools" -y
			yum install autoconf automake zlib-devel openssl-devel expat-devel pcre-devel libmemcached-devel cyrus-sasl* -y
			wget https://$DOWNLOAD_SERVER/litespeed/lsmcd.tar.gz
			tar xzvf lsmcd.tar.gz
			DIR=$(pwd)
			cd $DIR/lsmcd
			./fixtimestamp.sh
			./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
			make
			make install
			systemctl enable lsmcd
			systemctl start lsmcd
			cd $DIR
		else
			yum install -y memcached
			sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
			systemctl enable memcached
			systemctl start memcached
		fi
fi
if [[ $SERVER_OS == "Ubuntu" ]] ; then
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-memcached lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached
		if [[ $TOTAL_RAM -eq "2048" ]] || [[ $TOTAL_RAM -gt "2048" ]] ; then
			DEBIAN_FRONTEND=noninteractive apt install build-essential zlib1g-dev libexpat1-dev openssl libssl-dev libsasl2-dev libpcre3-dev git -y
			wget https://$DOWNLOAD/litespeed/lsmcd.tar.gz
			tar xzvf lsmcd.tar.gz
			DIR=$(pwd)
			cd $DIR/lsmcd
			./fixtimestamp.sh
			./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
			make
			make install
			cd $DIR
			systemctl enable lsmcd
			systemctl start lsmcd
		else
			DEBIAN_FRONTEND=noninteractive apt install -y memcached
			systemctl enable memcached
			systemctl start memcached
		fi
fi

if ps -aux | grep "lsmcd" | grep -v grep ; then
	echo -e "\n\nLiteSpeed Memcached installed and running..."
fi

if ps -aux | grep "memcached" | grep -v grep ; then
	echo -e "\n\nMemcached installed and running..."
fi

}

redis_installation() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp74-redis lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis lsphp56-redis lsphp55-redis lsphp54-redis redis
fi
if [[ $SERVER_OS == "Ubuntu" ]] ; then
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-redis lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis redis
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
	systemctl stop redis-server
	rm -f /var/run/redis/redis-server.pid
	systemctl enable redis-server
	systemctl start redis-server
fi

if ps -aux | grep "redis" | grep -v grep ; then
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

if [[ -f /sys/devices/virtual/dmi/id/product_uuid ]] ; then
if [ "$(cat /sys/devices/virtual/dmi/id/product_uuid | cut -c 1-3)" = 'EC2' ] && [ -d /home/ubuntu ]; then
	PROVIDER='Amazon Web Service'
fi
fi

}


check_OS() {
echo -e "\nChecking OS..."
OUTPUT=$(cat /etc/*release)
if  echo $OUTPUT | grep -q "CentOS Linux 7" ; then
	echo -e "\nDetecting CentOS 7.X...\n"
	SERVER_OS="CentOS"
elif echo $OUTPUT | grep -q "CloudLinux 7" ; then
	echo -e "\nDetecting CloudLinux 7.X...\n"
	SERVER_OS="CentOS"
elif  echo $OUTPUT | grep -q "CentOS Linux 8" ; then
	echo -e "\nDetecting CentOS 8.X...\n"
	SERVER_OS="CentOS"
	CENTOS_8="True"
elif echo $OUTPUT | grep -q "Ubuntu 18.04" ; then
	if uname -m | grep -q 64 ; then
	echo -e "\nDetecting Ubuntu 18.04...\n"
	SERVER_OS="Ubuntu"
	else
		echo -e "\nUbuntu 18.04 x32 detected...ths only works on x64 system."
		exit
	fi
else
	cat /etc/*release
	echo -e "\nUnable to detect your OS...\n"
	echo -e "\nCyberPanel is supported on Ubuntu 18.04 x86_64, CentOS 7.x, CentOS 8.x and CloudLinux 7.x...\n"
	exit 1
fi
}

check_root() {
echo -e "\nChecking root privileges...\n"
if echo $SUDO_TEST | grep SUDO > /dev/null ; then
	echo -e "\nYou are using SUDO , please run as root user...\n"
	echo -e "If you don't have direct access to root user, please run \e[31msudo su -\e[39m command and then run installation command again."
	exit
fi

if [[ $(id -u) != 0 ]]  > /dev/null; then
	echo -e "\nYou must use root user to install CyberPanel...\n"
#	echo -e "or run following command: (do NOT miss the quotes)"
#	echo -e "\e[31msudo su -c \"sh <(curl https://cyberpanel.sh || wget -O - https://cyberpanel.sh)\"\e[39m"
	exit 1
else
	echo -e "\nYou are runing as root...\n"
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
echo -e "\nUsage: wget https://cyberpanel.sh/cyberpanel.sh"
echo -e "\nchmod +x cyberpanel.sh"
echo -e "\n./cyberpanel.sh -v ols/SERIAL_NUMBER -c 1 -a 1"
echo -e "\n -v or --version: choose to install CyberPanel OpenLiteSpeed or CyberPanel Enterprise, available options are \e[31mols\e[39m and \e[31mSERIAL_NUMBER\e[39m, default ols"
echo -e "\n Please be aware, this serial number must be obtained from LiteSpeed Store."
echo -e "\n And if this serial number has been used before, it must be released/migrated in Store first, otherwise it will fail to start."
echo -e "\n -a or --addons: install addons: memcached, redis, PHP extension for memcached and redis, 1 for install addons, 0 for not to install, default 0, only applicable for CentOS system."
echo -e "\n -p or --password: set password of new installation, empty for default 1234567, [r] or [random] for randomly generated 16 digital password, any other value besdies [d] and [r(andom)] will be accept as password, default use 1234567."
echo -e "\n -m: set to minimal mode which will not install PowerDNS, Pure-FTPd and Postfix"
echo -e "\n Example:"
echo -e "\n ./cyberpanel.sh -v ols -p r or ./cyberpanel.sh --version ols --password random"
echo -e "\n This will install CyberPanel OpenLiteSpeed and randomly generate the password."
echo -e "\n ./cyberpanel.sh default"
echo -e "\n This will install everything default , which is OpenLiteSpeed and nothing more.\n"
}

license_input() {
VERSION="ENT"
echo -e "\nPlease note that your server has \e[31m$TOTAL_RAM MB\e[39m RAM"
echo -e "If you are using \e[31mFree Start\e[39m license, It will not start due to \e[31m2GB RAM limit\e[39m.\n"
echo -e "If you do not have any license, you can also use trial license (if server has not used trial license before), type \e[31mTRIAL\e[39m\n"

printf "%s" "Please input your serial number for LiteSpeed WebServer Enterprise:"
read LICENSE_KEY
if [ -z "$LICENSE_KEY" ] ; then
	echo -e "\nPlease provide license key\n"
	exit
fi

echo -e "The serial number you input is: \e[31m$LICENSE_KEY\e[39m"
printf "%s"  "Please verify it is correct. [y/N]"
read TMP_YN
if [ -z "$TMP_YN" ] ; then
	echo -e "\nPlease type \e[31my\e[39m\n"
	exit
fi

KEY_SIZE=${#LICENSE_KEY}
TMP=$(echo $LICENSE_KEY | cut -c5)
TMP2=$(echo $LICENSE_KEY | cut -c10)
TMP3=$(echo $LICENSE_KEY | cut -c15)

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
read -p "  Please enter the number[1-3]: " num
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

echo && read -p "Please enter the number[1-4]: " num
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
	echo -e "${Error} please enter the right number [1-4]"
	;;
esac
}

interactive_install() {
RAM=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
DISK=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
#clear
echo -e "		CyberPanel Installer v$CP_VER1$CP_VER2

  RAM check : $RAM

  Disk check : $DISK (Minimal \e[31m10GB\e[39m free space)

  1. Install CyberPanel with \e[31mOpenLiteSpeed\e[39m.

  2. Install Cyberpanel with \e[31mLiteSpeed Enterprise\e[39m.

  3. Exit.

  "
read -p "  Please enter the number[1-3]: " num
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


echo -e "\nInstall Full service for CyberPanel? This will include PowerDNS, Postfix and Pure-FTPd."
echo -e ""
printf "%s" "Full installation [Y/n]: "
read TMP_YN
if [[ `expr "x$TMP_YN" : 'x[Yy]'` -gt 1 ]] || [[ $TMP_YN == "" ]] ; then
		echo -e "\nFull installation selected..."
		POSTFIX_VARIABLE="ON"
		POWERDNS_VARIABLE="ON"
		PUREFTPD_VARIABLE="ON"
else
		echo -e ""
		printf "%s" "Install Postfix? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		POSTFIX_VARIABLE="OFF"
		else
		POSTFIX_VARIABLE="ON"
		fi
		echo -e ""
		printf "%s" "Install PowerDNS? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		POWERDNS_VARIABLE="OFF"
		else
		POWERDNS_VARIABLE="ON"
		fi
		echo -e ""
		printf "%s" "Install PureFTPd? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		PUREFTPD_VARIABLE="OFF"
		else
		PUREFTPD_VARIABLE="ON"
		fi
fi

#above comment for future use

#if [[ $DEV_ARG == "ON" ]] ; then
#echo -e "Press \e[31mEnter\e[39m to continue with stable version of CyberPanel, or"
#echo -e "\nPlease enter \e[31mbeta\e[39m and then press \e[31mEnter\e[39m to install CyberPanel with Python 3."
#echo -e "\nCentOS 8 will autoamtically proceed with Python 3 branch."
#printf "%s" ""
#read TMP_YN

echo -e "\nPress Enter key to continue with latest version or Enter specific version such as: \e[31m1.9.4\e[39m , \e[31m1.9.5\e[39m ...etc"
printf "%s" ""
read TMP_YN

DEV="ON"
if [[ $TMP_YN == "" ]] ; then
	BRANCH_NAME="v${TEMP:12:3}.${TEMP:25:1}"
	echo -e "\nBranch name set to $BRANCH_NAME"
else
	base_number="1.9.3"
		if [[ $TMP_YN == *.*.* ]] ; then
			#check input if it's valid format as X.Y.Z
			output=$(awk -v num1="$base_number" -v num2="$TMP_YN" '
			BEGIN {
				print "num1", (num1 < num2 ? "<" : ">="), "num2"
			}
			')
			if [[ $output == *">="* ]] ; then
				echo -e "\nYou must use version number higher than 1.9.4"
				exit
			else
				BRANCH_NAME="v$TMP_YN"
				echo "set branch name to $BRANCH_NAME"
			fi
		else
			echo -e "\nPlease input a valid format version number."
			exit
		fi
fi

#if [[ $TMP_YN == "beta" ]] ; then
#  DEV="ON"
##	echo -e "\nPlease specify branch name"
##	printf "%s" ""
##	read TMP_YN
#	BRANCH_NAME="p3"
#	echo -e "Branch name set to $BRANCH_NAME"
#else
#	DEV="OFF"
#
#	if [[ $CENTOS_8 == "True" ]] ; then
#	DEV="ON"
#	BRANCH_NAME="p3"
#		fi
#fi



#fi

echo -e "\nPlease choose to use default admin password \e[31m1234567\e[39m, randomly generate one \e[31m(recommended)\e[39m or specify the admin password?"
printf "%s" "Choose [d]fault, [r]andom or [s]et password: [d/r/s] "
read TMP_YN

if [[ $TMP_YN =~ ^(d|D| ) ]] || [[ -z $TMP_YN ]]; then
	ADMIN_PASS="1234567"
	echo -e "\nAdmin password will be set to $ADMIN_PASS\n"
elif [[ $TMP_YN =~ ^(r|R) ]] ; then
	ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
	echo -e "\nAdmin password will be provided once installation is completed...\n"
elif [[ $TMP_YN =~ ^(s|S) ]] ; then
	echo -e "\nPlease enter your password:"
	printf "%s" ""
	read TMP_YN
		if [ -z "$TMP_YN" ] ; then
  		echo -e "\nPlease do not use empty string...\n"
			exit
		fi
		if [ ${#TMP_YN} -lt 8 ] ; then
			echo -e "\nPassword lenth less than 8 digital, please choose a more complicated password.\n"
			exit
		fi
	TMP_YN1=$TMP_YN
	echo -e "\nPlease confirm  your password:\n"
	printf "%s" ""
	read TMP_YN
	if [ -z "$TMP_YN" ] ; then
  	echo -e "\nPlease do not use empty string...\n"
		exit
	fi
	TMP_YN2=$TMP_YN
	if [ $TMP_YN1 = $TMP_YN2 ] ; then
		ADMIN_PASS=$TMP_YN1
	else
		echo -e "\nRepeated password didn't match , please check...\n"
		exit
	fi
else
	ADMIN_PASS="1234567"
	echo -e "\nAdmin password will be set to $ADMIN_PASS\n"
fi

echo -e "\nDo you wish to install Memcached extension and backend?"
printf "%s" "Please select [Y/n]: "
read TMP_YN
if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
	MEMCACHED="OFF"
else
	MEMCACHED="ON"
fi

echo -e "\nDo you wish to install Redis extension and backend?"
printf "%s" "Please select [Y/n]: "
read TMP_YN
if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
	REDIS="OFF"
else
	REDIS="ON"
fi

echo -e "\nWould you like to set up a WatchDog \e[31m(beta)\e[39m for Web service and Database service ?"
echo -e "The watchdog script will be automatically started up after installation and server reboot"
echo -e "If you want to kill the watchdog , run \e[31mwatchdog kill\e[39m"
echo -e "Please type Yes or no (with capital \e[31mY\e[39m):"
printf "%s"
read TMP_YN
if [[ $TMP_YN == "Yes" ]] ; then
	WATCHDOG="ON"
else
	WATCHDOG="OFF"
fi
}

main_install() {

if [[ -e /usr/local/CyberCP ]] ; then
	echo -e "\n CyberPanel already installed, exiting..."
exit
fi

special_change

if [[ $VERSION == "ENT" ]] ; then
	echo -e "\nValidating the license..."
	echo -e "\nThis may take a minute..."
	echo -e "\nplease be patient...\n\n"
	license_validation
	SERIAL_NO="--ent ent --serial "
fi

sed -i 's|lsws-5.4.2|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
sed -i 's|lsws-5.3.5|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
#this sed must be done after license validation

echo -e "Preparing..."
echo -e "Installation will start in 10 seconds, if you wish to stop please press CTRL + C"
sleep 10
debug="1"
if [[ $debug == "0" ]] ; then
	echo "/usr/local/CyberPanel/bin/python install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY --postfix $POSTFIX_VARIABLE --powerdns $POWERDNS_VARIABLE --ftp $PUREFTPD_VARIABLE"
	exit
fi

if [[ $debug == "1" ]] ; then
	/usr/local/CyberPanel/bin/python install.py $SERVER_IP $SERIAL_NO $LICENSE_KEY --postfix $POSTFIX_VARIABLE --powerdns $POWERDNS_VARIABLE --ftp $PUREFTPD_VARIABLE

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
		mkdir /root/.config
		mkdir /root/.config/pip
		cat << EOF > /root/.config/pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
EOF
fi

if [[ $PROVIDER == "Alibaba Cloud" ]] ; then
	pip install --upgrade pip
	pip install setuptools==40.8.0
fi

if [[ $SERVER_OS == "CentOS" ]] ; then
    pip install virtualenv==16.7.9
  else
    pip install virtualenv
fi

virtualenv --system-site-packages /usr/local/CyberPanel
source /usr/local/CyberPanel/bin/activate
rm -rf requirements.txt
wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/1.8.0/requirments.txt
pip install --ignore-installed -r requirements.txt
check_return
virtualenv --system-site-packages /usr/local/CyberPanel
fi

if [[ $DEV == "ON" ]] ; then
	#install dev branch
	#wget https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt
	cd /usr/local/
	virtualenv -p /usr/bin/python3 CyberPanel
  source /usr/local/CyberPanel/bin/activate
  wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt
  pip3.6 install --ignore-installed -r requirements.txt
	check_return
	cd -
fi

if [ -f requirements.txt ] && [ -d cyberpanel ] ; then
	rm -rf cyberpanel
	rm -f requirements.txt
fi

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	wget https://cyberpanel.sh/cyberpanel-git.tar.gz
	tar xzvf cyberpanel-git.tar.gz > /dev/null
	cp -r cyberpanel /usr/local/cyberpanel
	cd cyberpanel/install
else
	if [[ $DEV == "ON" ]] ; then
	git clone https://github.com/usmannasir/cyberpanel
	cd cyberpanel
	git checkout $BRANCH_NAME
	check_return
	cd -
	cp -r cyberpanel /usr/local/cyberpanel
	cd cyberpanel/install
	else
	git clone https://github.com/usmannasir/cyberpanel
	cp -r cyberpanel /usr/local/cyberpanel
	cd cyberpanel/install
	fi
fi
curl https://cyberpanel.sh/?version
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
	cd ${DIR}/cyberpanel/install/lsws-*
	./install.sh
	echo -e "\n\n\nIt seems LiteSpeed Enterprise has failed to install, please check your license key is valid"
	echo -e "\nIf this license key has been used before, you may need to go to store to release it first."
	exit
fi


if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt > /dev/null; then

if [[ $DEV == "ON" ]] ; then

	if [[ $PROVIDER == "Alibaba Cloud" ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
	cat << EOF > /root/.config/pip/pip.conf
[global]
index-url = https://pypi.python.org/simple/
[install]
trusted-host=pypi.python.org
EOF
	fi

virtualenv -p /usr/bin/python3 /usr/local/CyberCP
source /usr/local/CyberCP/bin/activate
wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt
pip3.6 install --ignore-installed -r requirements.txt
check_return
systemctl restart lscpd
fi

for version in $(ls /usr/local/lsws | grep lsphp);
	do
		php_ini=$(find /usr/local/lsws/$version/ -name php.ini)
		version2=${version:5:2}
		version2=$(awk "BEGIN { print "${version2}/10" }")
				if [[ $version2 = "7" ]] ; then
					version2="7.0"
				fi
		if [[ $SERVER_OS == "CentOS" ]] ; then
		yum remove -y $version-mysql
		yum install -y $version-mysqlnd
		yum install -y $version-devel make gcc glibc-devel libmemcached-devel zlib-devel
			if [[ ! -d /usr/local/lsws/$version/tmp ]] ; then
				mkdir /usr/local/lsws/$version/tmp
			fi
		/usr/local/lsws/${version}/bin/pecl channel-update pecl.php.net
		/usr/local/lsws/${version}/bin/pear config-set temp_dir /usr/local/lsws/${version}/tmp
		/usr/local/lsws/${version}/bin/pecl install timezonedb
		echo "extension=timezonedb.so" > /usr/local/lsws/${version}/etc/php.d/20-timezone.ini
		chmod 755 /usr/local/lsws/${version}/lib64/php/modules/timezonedb.so
		sed -i 's|expose_php = On|expose_php = Off|g' $php_ini
		sed -i 's|mail.add_x_header = On|mail.add_x_header = Off|g' $php_ini
		sed -i 's|;session.save_path = "/tmp"|session.save_path = "/var/lib/php/session"|g' $php_ini
		fi

		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			if [[ ! -d /usr/local/lsws/cyberpanel-tmp ]] ; then
				if [[ -d /etc/pure-ftpd/conf ]] ; then
				echo "yes" > /etc/pure-ftpd/conf/ChrootEveryone
				systemctl restart pure-ftpd-mysql
				fi
				DEBIAN_FRONTEND=noninteractive apt install libmagickwand-dev pkg-config build-essential -y
				mkdir /usr/local/lsws/cyberpanel-tmp
				cd /usr/local/lsws/cyberpanel-tmp
				wget -O timezonedb.tgz https://pecl.php.net/get/timezonedb
				tar xzvf timezonedb.tgz
				cd timezonedb-*
			fi
		/usr/local/lsws/${version}/bin/phpize
		./configure --with-php-config=/usr/local/lsws/${version}/bin/php-config${version2}
		make
		make install
		echo "extension=timezonedb.so" > /usr/local/lsws/${version}/etc/php/${version2}/mods-available/20-timezone.ini
		make clean
	fi
done

rm -rf /etc/profile.d/cyberpanel*
curl --silent -o /etc/profile.d/cyberpanel.sh https://cyberpanel.sh/?banner 2>/dev/null
chmod +x /etc/profile.d/cyberpanel.sh
RAM2=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
DISK2=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
ELAPSED="$(($SECONDS / 3600)) hrs $((($SECONDS / 60) % 60)) min $(($SECONDS % 60)) sec"
MYSQLPASSWD=$(cat /etc/cyberpanel/mysqlPassword)
echo "$ADMIN_PASS" > /etc/cyberpanel/adminPass
/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py --password $ADMIN_PASS
mkdir -p /etc/opendkim
systemctl restart lscpd
systemctl restart lsws
echo "/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py --password \$@" > /usr/bin/adminPass
echo "systemctl restart lscpd" >> /usr/bin/adminPass
chmod 700 /usr/bin/adminPass
if [[ $VERSION = "OLS" ]] ; then
	WORD="OpenLiteSpeed"
#	sed -i 's|maxConnections               10000|maxConnections               100000|g' /usr/local/lsws/conf/httpd_config.conf
#	OLS_LATEST=$(curl https://openlitespeed.org/packages/release)
#	wget https://openlitespeed.org/packages/openlitespeed-$OLS_LATEST.tgz
#	tar xzvf openlitespeed-$OLS_LATEST.tgz
#	cd openlitespeed
#	./install.sh
	systemctl stop lsws
	systemctl start lsws
#	rm -f openlitespeed-$OLS_LATEST.tgz
#	rm -rf openlitespeed
#	cd ..
fi
if [[ $VERSION = "ENT" ]] ; then
	WORD="LiteSpeed Enterprise"
	if [[ $SERVER_COUNTRY != "CN" ]] ; then
		/usr/local/lsws/admin/misc/lsup.sh -f -v $LSWS_STABLE_VER
	fi
fi

systemctl status lsws 2>&1>/dev/null
if [[ $? == "0" ]] ; then
	echo "LSWS service is running..."
else
	systemctl stop lsws
	systemctl start lsws
fi

webadmin_passwd

watchdog_setup

install_utility

if [[ ! -f /usr/sbin/ipset ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
ln -s /sbin/ipset /usr/sbin/ipset
fi

if [[ ! -f /usr/local/lsws/lsphp74/lib64/php/modules/zip.so ]] && [[ $SERVER_OS == "CentOS" ]] && [[ $CENTOS_8 == "False" ]]; then
	yum list installed libzip-devel
		if [[ $? == "0" ]] ; then
			yum remove -y libzip-devel
	fi
	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-devel-0.11.2-6.el7.psychotic.x86_64.rpm
	/usr/local/lsws/lsphp74/bin/pecl install zip
	echo "extension=zip.so" > /usr/local/lsws/lsphp74/etc/php.d/20-zip.ini
	chmod 755 /usr/local/lsws/lsphp74/lib64/php/modules/zip.so
fi
#fix the lsphp74-zip missing issue.


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
echo "                Visit: https://$SERVER_IP:8090                     "
echo "                Panel username: admin                              "
echo "                Panel password: $ADMIN_PASS                        "
echo "                WebAdmin console username: admin                         "
echo "                WebAdmin console password: $WEBADMIN_PASS                "
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
	echo -e "\033[0;32mTCP: 8090\033[39m for CyberPanel"
	echo -e "\033[0;32mTCP: 80\033[39m, \033[0;32mTCP: 443\033[39m and \033[0;32mUDP: 443\033[39m for webserver"
	echo -e "\033[0;32mTCP: 21\033[39m and \033[0;32mTCP: 40110-40210\033[39m for FTP"
	echo -e "\033[0;32mTCP: 25\033[39m, \033[0;32mTCP: 587\033[39m, \033[0;32mTCP: 465\033[39m, \033[0;32mTCP: 110\033[39m, \033[0;32mTCP: 143\033[39m and \033[0;32mTCP: 993\033[39m for mail service"
	echo -e "\033[0;32mTCP: 53\033[39m and \033[0;32mUDP: 53\033[39m for DNS service"
if [[ $SERVER_COUNTRY = CN ]] ; then
	if [[ $PROVIDER == "Tencent Cloud" ]] ; then
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			rm -f /etc/apt/sources.list
			mv /etc/apt/sources.list-backup /etc/apt/sources.list
echo > "nameserver 127.0.0.53
options edns0" /run/systemd/resolve/stub-resolv.conf
echo > "nameserver 127.0.0.53
options edns0" /etc/resolv.conf
			apt update
#revert the previous change on tencent cloud repo.
		fi
	fi
	if [[ $VERSION = "ENT" ]] ; then
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/install/installCyberPanel.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://'$DOWNLOAD_SERVER'/litespeed/lsws-'$LSWS_STABLE_VER'-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		echo -e "If you have install LiteSpeed Enterprise, please run \e[31m/usr/local/lsws/admin/misc/lsup.sh\033[39m to update it to latest."
	fi
fi

sed -i 's|lsws-5.3.8|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.4.2|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.3.5|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py

if [[ -f /etc/pure-ftpd/pure-ftpd.conf ]] ; then
sed -i 's|NoAnonymous                 no|NoAnonymous                 yes|g' /etc/pure-ftpd/pure-ftpd.conf
fi

if [[ $SILENT != "ON" ]] ; then
printf "%s" "Would you like to restart your server now? [y/N]: "
read TMP_YN

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
DEV="ON"
BRANCH_NAME="stable"
#default to python3 branch.
KEY_SIZE=${#VERSION}
TMP=$(echo $VERSION | cut -c5)
TMP2=$(echo $VERSION | cut -c10)
TMP3=$(echo $VERSION | cut -c15)
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
	ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
	echo -e "\nSet to random-generated password..."
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
	echo $ADMIN_PASS
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
	POSTFIX_VARIABLE="ON"
	POWERDNS_VARIABLE="ON"
	PUREFTPD_VARIABLE="ON"
	VERSION="OLS"
	ADMIN_PASS="1234567"
	MEMCACHED="ON"
	REDIS="ON"
	else
		while [ ! -z "${1}" ]; do
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
						elif [[ "${1}" == 'r' ]] || [[ $1 == 'random' ]] ; then
							ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
						else
							if [ ${1} -lt 8 ] ; then
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
						POSTFIX_VARIABLE="OFF"
						POWERDNS_VARIABLE="OFF"
						PUREFTPD_VARIABLE="OFF"
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
DOWNLOAD_SERVER="cdn.cyberpanel.sh"
fi

check_OS
check_virtualization
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