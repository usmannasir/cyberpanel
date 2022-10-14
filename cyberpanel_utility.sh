#!/bin/bash
#CyberPanel utility script

export LC_CTYPE=en_US.UTF-8
SUDO_TEST=$(set)
BRANCH_NAME="stable"
GIT_URL="github.com/usmannasir/cyberpanel"
GIT_CONTENT_URL="raw.githubusercontent.com/usmannasir/cyberpanel"

check_OS() {
	if [[ ! -f /etc/os-release ]] ; then
	  echo -e "Unable to detect the operating system...\n"
	  exit
	fi

	if grep -q -E "CentOS Linux 7|CentOS Linux 8" /etc/os-release ; then
	  Server_OS="CentOS"
	elif grep -q "AlmaLinux-8" /etc/os-release ; then
	  Server_OS="AlmaLinux"
	elif grep -q -E "CloudLinux 7|CloudLinux 8" /etc/os-release ; then
	  Server_OS="CloudLinux"
	elif grep -q -E "Ubuntu 18.04|Ubuntu 20.04|Ubuntu 20.10" /etc/os-release ; then
	  Server_OS="Ubuntu"
	elif grep -q -E "Rocky Linux" /etc/os-release ; then
	  Server_OS="RockyLinux"
	elif grep -q -E "openEuler 20.03|openEuler 22.03" /etc/os-release ; then
	  Server_OS="openEuler"
	else
	  echo -e "Unable to detect your system..."
	  echo -e "\nCyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03...\n"
  	  Debug_Log2 "CyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03... [404]"
	  exit
	fi

	Server_OS_Version=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )
	#to make 20.04 display as 20

	echo -e "System: $Server_OS $Server_OS_Version detected...\n"

	if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]] ; then
	  Server_OS="CentOS"
  	  #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
  	  #treat CloudLinux, Rocky and Alma as CentOS
	fi

}

set_watchdog() {
echo -e "\nPlease choose:"
echo -e "\n1. Install/Update WatchDog."
echo -e "\n2. Start or Check WatchDog."
echo -e "\n3. Kill WatchDog."
echo -e "\n4. Back to Main Menu."
echo -e "\n"
printf "%s" "Please enter number [1-4]: "
read TMP_YN

if [[ $TMP_YN == "1" ]] ; then
	if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
		bash /etc/cyberpanel/watchdog.sh kill
	fi
		rm -f /etc/cyberpanel/watchdog.sh
		rm -f /usr/local/bin/watchdog
		wget -O /etc/cyberpanel/watchdog.sh https://$GIT_CONTENT_URL/$BRANCH_NAME/CPScripts/watchdog.sh
		chmod 700 /etc/cyberpanel/watchdog.sh
		ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
		echo -e "\nWatchDog has been installed/updated..."
		watchdog status
		set_watchdog
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

rm -f /usr/local/CyberPanel/cyberpanel_utility.sh
wget -q -O /usr/local/CyberPanel/cyberpanel_utility.sh https://cyberpanel.sh/misc/cyberpanel_utility.sh
chmod 600 /usr/local/CyberPanel/cyberpanel_utility.sh


SUM=$(md5sum /usr/local/CyberPanel/cyberpanel_utility.sh)
SUM2=${SUM:0:32}
#get md5sum of remote file.

if [[ $SUM1 == $SUM2 ]] ; then
	echo -e "\nCyberPanel Utility Script is up to date...\n"
else
	local_string=$(head -2 /usr/bin/cyberpanel_utility)
	remote_string=$(head -2 /usr/local/CyberPanel/cyberpanel_utility.sh)
	#check file content before replacing itself in case failed to download the file.
	if [[ $local_string == $remote_string ]] ; then
	echo -e "\nUpdating CyberPanel Utility Script..."
	rm -f /usr/bin/cyberpanel_utility
	mv /usr/local/CyberPanel/cyberpanel_utility.sh /usr/bin/cyberpanel_utility
	chmod 700 /usr/bin/cyberpanel_utility
	echo -e "\nCyberPanel Utility update compelted..."
	echo -e "\nPlease execute it again..."
	exit
	else
	echo -e "\nFailed to fetch server file..."
	echo -e "\nKeep using local script..."
	fi
fi

rm -f /usr/local/CyberPanel/cyberpanel_utility.sh

}

cyberpanel_upgrade() {
SERVER_COUNTRY="unknow"
SERVER_COUNTRY=$(curl --silent --max-time 5 https://cyberpanel.sh/?country)
if [[ ${#SERVER_COUNTRY} == "2" ]] || [[ ${#SERVER_COUNTRY} == "6" ]] ; then
	echo -e "\nChecking server..."
else
	echo -e "\nChecking server..."
	SERVER_COUNTRY="unknow"
fi

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	GIT_URL="gitee.com/qtwrk/cyberpanel"
	GIT_CONTENT_URL="gitee.com/qtwrk/cyberpanel/raw"
fi

#echo -e "CyberPanel Upgrade will start in 10 seconds"
#echo -e "If you want to cancel, please press CTRL + C to cancel it"
#sleep 10
echo -e "CyberPanel upgrading..."
rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh -q https://$GIT_CONTENT_URL/${BRANCH_NAME}/cyberpanel_upgrade.sh
chmod 700 /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh
rm -f /usr/local/cyberpanel_upgrade.sh
exit
}

show_help() {
echo -e "\nFetching information...\n"
curl --silent https://cyberpanel.sh/misc/faq.sh | sudo -u nobody bash | less -r
exit
}

addons() {
	echo -e "\nPlease choose:"
	echo -e "\n1. Install Memcached extension for PHP."
	echo -e "\n2. Install Memcached server."
	echo -e "\n3. Install Redis extension for PHP."
	echo -e "\n4. Install Redis server."
	echo -e "\n5. Raise phpMyAdmin upload limits."
	echo -e "\n6. Back to Main Menu.\n"
	printf "%s" "Please enter number [1-6]: "
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
	phpmyadmin_limits
	elif [[ $TMP_YN == "6" ]] ; then
	main_page
	else
	echo -e "  Please enter the right number [1-6]\n"
	exit
	fi
}

phpmyadmin_limits() {
	echo -e "This will change following parameters for PHP 7.3:"
	echo -e "Post Max Size from default 8M to 500M"
	echo -e "Upload Max Filesize from default 2M to 500M"
	echo -e "Memory Limit from default 128M to 768M"
	echo -e "Max Execution Time from default 30 to 600"
	echo -e "\nPlease note this will also apply to all sites use PHP 7.3"
	printf "%s" "Please confirm to proceed: [Y/n]: "
	read TMP_YN
	if [[ $TMP_YN == "Y" ]] || [[ $TMP_YN == "y" ]] ; then 
	
		if [[ "$SERVER_OS" == "CentOS" ]] || [[ "$SERVER_OS" == "openEuler" ]] ; then 
			php_ini_path="/usr/local/lsws/lsphp73/etc/php.ini"
		fi 

		if [[ "$SERVER_OS" == "Ubuntu" ]] ; then 
			php_ini_path="/usr/local/lsws/lsphp73/etc/php/7.3/litespeed/php.ini"
		fi 
			sed -i 's|post_max_size = 8M|post_max_size = 500M|g' $php_ini_path
			sed -i 's|upload_max_filesize = 2M|upload_max_filesize = 500M |g' $php_ini_path
			sed -i 's|memory_limit = 128M|memory_limit = 768M|g' $php_ini_path
			sed -i 's|max_execution_time = 30|max_execution_time = 600|g' $php_ini_path
			systemctl restart lscpd
			echo "Change applied..."
  else 
		echo -e "Please enter Y or n."
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
	if [[ $SERVER_OS == "openEuler" ]] ; then
		dnf install -y lsphp74-redis lsphp73-redis lsphp72-redis lsphp71-redis
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
	if [[ ! -f /usr/bin/redis-cli ]] && [[ $SERVER_OS == "openEuler" ]] ; then
		yum install -y redis6
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
			if [[ $SERVER_OS == "CentOS" ]] || [[ $SERVER_OS == "openEuler" ]] ; then
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
		if [[ ! -f /usr/bin/memcached ]] && [[ $SERVER_OS == "openEuler" ]] ; then
		  yum install memcached -y
		  sed -i 's|OPTIONS=""|OPTIONS="-l 127.0.0.1 -U 0"|g' /etc/sysconfig/memcached
		  #this will disbale UDP and bind to 127.0.0.1 to prevent UDP amplification attack
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
	if [[ $SERVER_OS == "openEuler" ]] ; then
	dnf install -y lsphp74-memcached lsphp73-memcached lsphp72-memcached lsphp71-memcached
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
		echo -e "\nIf you don't have direct access to root user, please run \e[31msudo su -\e[39m command (do NOT miss the \e[31m-\e[39m at end or it will fail) and then run utility command again."
		exit
	fi

	if [[ $(id -u) != 0 ]]  > /dev/null; then
		echo -e "\nYou must use root user to use CyberPanel Utility..."
		exit
	else
		echo -e "\nYou are running as root..."
	fi
}


sudo_check

panel_check

self_check

check_OS

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
