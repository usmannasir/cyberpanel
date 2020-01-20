#!/bin/bash
#CyberPanel utility script

export LC_CTYPE=en_US.UTF-8
SUDO_TEST=$(set)
BRANCH_NAME="stable"

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
	echo -e "\nDetecting Ubuntu 18.04...\n"
	SERVER_OS="Ubuntu"
else
	cat /etc/*release
	echo -e "\nUnable to detect your OS...\n"
	echo -e "\nCyberPanel is supported on Ubuntu 18.04, CentOS 7.x, CentOS 8.x and CloudLinux 7.x...\n"
	exit 1
fi
}

set_watchdog() {
echo -e "\nPlease choose:"
echo -e "\n1. Install WatchDog."
echo -e "\n2. Start or Check WatchDog."
echo -e "\n3. Kill WatchDog."
echo -e "\n4. Back to Main Menu."
echo -e "\n"
printf "%s" "Please enter number [1-4]: "
read TMP_YN

if [[ $TMP_YN == "1" ]] ; then
	if [[ ! -f /etc/cyberpanel/watchdog.sh ]] ; then
		echo -e "\nWatchDog no found..."
		wget -O /etc/cyberpanel/watchdog.sh https://cyberpanel.sh/misc/watchdog.sh
		chmod 700 /etc/cyberpanel/watchdog.sh
		ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
		echo -e "\nWatchDos has been installed..."
		set_watchdog
	else
		echo -e "\nWatchDos is already installed..."
		set_watchdog
	fi
elif [[ $TMP_YN == "2" ]] ; then
	if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
		watchdog status
		exit
	else
		echo -e "\nYou don't have WatchDog installed, please install it first..."
		set_watchdog
	fi
elif [[ $TMP_YN == "3" ]] ; then
	if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
		echo -e "\n"
		watchdog kill
		exit
	else
		echo -e "\nYou don't have WatchDog installed, please install it first..."
		set_watchdog
	fi
elif [[ $TMP_YN == "4" ]] ; then
	main_page
else
	echo -e "\nPlease enter correct number..."
	exit
fi
}

check_return() {
#check previous command result , 0 = ok ,  non-0 = something wrong.
if [[ $? -eq "0" ]] ; then
	:
else
	echo -e "\ncommand failed, exiting..."
	exit
fi
}

self_check() {
echo -e "\nChecking Cyberpanel Utility update..."
SUM=$(md5sum /usr/bin/cyberpanel_utility)
SUM1=${SUM:0:32}
#get md5sum of local file

rm -f /tmp/cyberpanel_utility.sh
wget -q -O /tmp/cyberpanel_utility.sh https://cyberpanel.sh/misc/cyberpanel_utility.sh


SUM=$(md5sum /tmp/cyberpanel_utility.sh)
SUM2=${SUM:0:32}
#get md5sum of remote file.

if [[ $SUM1 == $SUM2 ]] ; then
	echo -e "\nCyberPanel Utility Script is up to date...\n"
else
	local_string=$(head -2 /usr/bin/cyberpanel_utility)
	remote_string=$(head -2 /tmp/cyberpanel_utility.sh)
	#check file content before replacing itself in case failed to download the file.
	if [[ $local_string == $remote_string ]] ; then
	echo -e "\nUpdating CyberPanel Utility Script..."
	rm -f /usr/bin/cyberpanel_utility
	mv /tmp/cyberpanel_utility.sh /usr/bin/cyberpanel_utility
	chmod 700 /usr/bin/cyberpanel_utility
	echo -e "\nCyberPanel Utility update compelted..."
	echo -e "\nPlease execute it again..."
	exit
	else
	echo -e "\nFailed to fetch server file..."
	echo -e "\nKeep using local script..."
	fi
fi

rm -f /tmp/cyberpanel_utility.sh

}

cyberpanel_upgrade() {
echo -e "CyberPanel Upgrade will start in 10 seconds"
echo -e "If you want to cancel, please press CTRL + C to cancel it"
sleep 10
echo -e "CyberPanel upgrading..."
rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh -q https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh
chmod 700 /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh
rm -f /usr/local/cyberpanel_upgrade.sh
exit
}

show_help() {
echo -e "\nFetching information...\n"
curl --silent https://cyberpanel.sh/misc/faq.sh | sudo -u nobody bash
exit
}

addons() {
	echo -e "\nPlease choose:"
	echo -e "\n1. Install Memcached extension for PHP."
	echo -e "\n2. Install Memcached server."
	echo -e "\n3. Install Redis extension for PHP."
	echo -e "\n4. Install Redis server."
	echo -e "\n5. Back to Main Menu.\n"
	printf "%s" "Please enter number [1-5]: "
	read TMP_YN

	if [[ $TMP_YN == "1" ]] ; then
	install_php_memcached
	elif [[ $TMP_YN == "2" ]] ; then
	install_memcached
	elif [[ $TMP_YN == "3" ]]; then
	install_php_redis
	elif [[ $TMP_YN == "4" ]] ; then
	install_redis
	elif [[ $TMP_YN == "5" ]] ; then
	main_page
	else
	echo -e "  Please enter the right number [1-5]\n"
	exit
	fi
}

install_php_redis() {
	if [[ $SERVER_OS == "CentOS" ]] ; then
		yum install -y lsphp74-redis lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis lsphp56-redis lsphp55-redis lsphp54-redis
	fi
	if [[ $SERVER_OS == "Ubuntu" ]] ; then
		DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-redis lsphp73-redis lsphp72-redis lsphp71-redis lsphp70-redis
	fi
	echo -e "\nRedis extension for PHP has been installed..."
	exit
}

install_redis() {
	if [[ -f /usr/bin/redis-cli ]] ; then
		echo -e "\nRedis is already installed..."
	fi
	if [[ ! -f /usr/bin/redis-cli ]] && [[ $SERVER_OS == "CentOS" ]] ; then
		yum install -y redis
	fi
	if [[ ! -f /usr/bin/redis-cli ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
		DEBIAN_FRONTEND=noninteractive apt install -y redis
	fi
	if ifconfig -a | grep inet6 ; then
		echo -e "\n IPv6 detected..."
	else
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
		sed -i 's|bind 127.0.0.1 ::1|bind 127.0.0.1|g' /etc/redis/redis.conf
		#remove ipv6 binding to prevent Redis fail to start.
		fi
		echo -e "\n no IPv6 detected..."
	fi

	if systemctl is-active --quiet redis ; then
	systemctl status redis
	else
	systemctl enable redis
	systemctl start redis
	systemctl status redis
	fi
}

install_memcached() {
echo -e "\n Would you like to install Memcached or LiteSpeed Mmecached ?"
echo -e "\n 1. LiteSpeed Memcached"
echo -e "\n 2. Memcached"
echo -e "\n 3. Back to Main Menu\n"
printf "%s" "Please enter number [1-3]: "
read TMP_YN

	if [[ $TMP_YN == "1" ]] ; then
		if systemctl is-active --quiet memcached ; then
			echo -e "\nIt seems Memcached server is already running..."
			systemctl status memcached
			exit
		fi
		if [[ -f /usr/local/lsmcd/bin/lsmcd ]] ; then
			echo -e "\nLiteSpeed Memcached is already installed..."
		else
			if [[ $SERVER_OS == "CentOS" ]] ; then
				yum groupinstall "Development Tools" -y
				yum install autoconf automake zlib-devel openssl-devel expat-devel pcre-devel libmemcached-devel cyrus-sasl* -y
			elif [[ $SERVER_OS == "Ubuntu" ]] ; then
				DEBIAN_FRONTEND=noninteractive apt install build-essential zlib1g-dev libexpat1-dev openssl libssl-dev libsasl2-dev libpcre3-dev git -y
			fi
				wget https://cdn.cyberpanel.sh/litespeed/lsmcd.tar.gz
				tar xzvf lsmcd.tar.gz
				DIR=$(pwd)
				cd $DIR/lsmcd
				./fixtimestamp.sh
				./configure CFLAGS=" -O3" CXXFLAGS=" -O3"
				make
				make install
				cd $DIR
		fi
		if systemctl is-active --quiet lsmcd ; then
		systemctl status lsmcd
		else
		systemctl enable lsmcd
		systemctl start lsmcd
		systemctl status lsmcd
		fi

	elif [[ $TMP_YN == "2" ]] ; then
		if systemctl is-active --quiet lsmcd ; then
			echo -e "\nIt seems LiteSpeed Memcached server is already running..."
			systemctl status lsmcd
			exit
		fi
		if [[ -f /usr/bin/memcached ]] ; then
		echo -e "\nMemcached is already installed..."
		fi
		if [[ ! -f /usr/bin/memcached ]] && [[ $SERVER_OS == "CentOS" ]] ; then
		  yum install memcached -y
		  sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
		  #this will disbale UDP and bind to 127.0.0.1 to prevent UDP amplification attack
		fi
		if [[ ! -f /usr/bin/memcached ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
		  DEBIAN_FRONTEND=noninteractive apt install memcached -y
		fi
		if systemctl is-active --quiet memcached ; then
		systemctl status memcached
		else
		systemctl enable memcached
		systemctl start memcached
		systemctl status memcached
		fi
	elif [[ $TMP_YN == "3" ]] ; then
	main_page
	else
	echo -e "  Please enter the right number [1-3]\n"
	exit
	fi
}

install_php_memcached() {
	if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp74-memcached lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached lsphp56-pecl-memcached lsphp55-pecl-memcached lsphp54-pecl-memcached
	fi
	if [[ $SERVER_OS == "Ubuntu" ]] ; then
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-memcached lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached
	fi
	echo -e "\nMemcached extension for PHP has been installed..."
	exit
}

main_page() {
echo -e "		CyberPanel Utility Tools \e[31m(beta)\e[39m

  1. Upgrade CyberPanel.

  2. Addons.

  3. WatchDog \e[31m(beta)\e[39m

  4. Frequently Asked Question (FAQ)

  5. Exit.

  "
read -p "  Please enter the number[1-5]: " num
echo ""
case "$num" in
	1)
	cyberpanel_upgrade
	;;
	2)
	addons
	;;
	3)
	set_watchdog
	;;
	4)
	show_help
	;;
	5)
	exit
	;;
	*)
	echo -e "  Please enter the right number [1-5]\n"
	exit
	;;
esac
}

panel_check(){
if [[ ! -f /etc/cyberpanel/machineIP ]] ; then
	echo -e "\nCan not detect CyberPanel..."
	echo -e "\nExit..."
	exit
fi
}

sudo_check() {
	echo -e "\nChecking root privileges..."
	if echo $SUDO_TEST | grep SUDO > /dev/null ; then
		echo -e "\nYou are using SUDO , please run as root user..."
		echo -e "If you don't have direct access to root user, please run \e[31msudo su -\e[39m command and then run installation command again."
		exit
	fi

	if [[ $(id -u) != 0 ]]  > /dev/null; then
		echo -e "\nYou must use root user to use CyberPanel Utility..."
		exit
	else
		echo -e "\nYou are runing as root..."
	fi
}


panel_check

sudo_check

check_OS

self_check


if [ $# -eq 0 ] ; then
main_page
else
	if [[ $1 == "upgrade" ]] || [[ $1 == "-u" ]] || [[ $1 == "--update" ]] || [[ $1 == "--upgrade" ]] || [[ $1 == "update" ]]; then
		cyberpanel_upgrade
	fi
	if [[ $1 == "help" ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] ; then
		show_help
		exit
	fi
echo -e "\nUnrecognized argument..."
exit
fi
