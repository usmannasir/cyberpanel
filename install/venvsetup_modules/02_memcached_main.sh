#!/usr/bin/env bash
# install/venvsetup part 2 – memcached through main_install

memcached_installation() {
if [[ $SERVER_OS == "CentOS" ]] ; then
	yum install -y lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached lsphp56-pecl-memcached lsphp55-pecl-memcached lsphp54-pecl-memcached 
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
	DEBIAN_FRONTEND=noninteractive apt install -y lsphp73-memcached lsphp72-memcached lsphp71-memcached lsphp70-memcached
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

if [ "$(cat /sys/devices/virtual/dmi/id/product_uuid | cut -c 1-3)" = 'EC2' ] && [ -d /home/ubuntu ]; then 
	PROVIDER='Amazon Web Service'
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
elif echo $OUTPUT | grep -q "Ubuntu 18.04" ; then
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
if [[ $(id -u) != 0 ]]  > /dev/null; then
	echo -e "You must use root account to do this"
	echo -e "or run following command: (do NOT miss the quotes)"
	echo -e "\e[31msudo su -c \"sh <(curl https://cyberpanel.sh || wget -O - https://cyberpanel.sh)\"\e[39m"
	exit 1
else
	echo -e "You are runing as root...\n"
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

<<COMMENT
echo -e "\nInstall minimal service for CyberPanel? This will skip PowerDNS, Postfix and Pure-FTPd."
printf "%s" "Minimal installation [y/N]: "
read TMP_YN
if [ `expr "x$TMP_YN" : 'x[Yy]'` -gt 1 ]; then
		echo -e "\nMinimal installation selected..."
		POSTFIX_VARIABLE="OFF"
		POWERDNS_VARIABLE="OFF"
		PUREFTPD_VARIABLE="OFF"
else
		printf "%s" "Install Postfix? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		POSTFIX_VARIABLE="OFF"
		else
		POSTFIX_VARIABLE="ON"
		fi
		printf "%s" "Install PowerDNS? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		POWERDNS_VARIABLE="OFF"
		else
		POWERDNS_VARIABLE="ON"
		fi
		printf "%s" "Install PureFTPd? [Y/n]: "
		read TMP_YN
		if [[ $TMP_YN =~ ^(no|n|N) ]] ; then
		PUREFTPD_VARIABLE="OFF"
		else
		PUREFTPD_VARIABLE="ON"
		fi
fi
COMMENT
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
	read TMP_YN
	BRANCH_NAME=$TMP_YN
	echo -e "Branch name set to $BRANCH_NAME"
#else
#	DEV="OFF"
#fi
fi

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

echo -e "\nWhich MariaDB version do you want to install? \e[31m11.8\e[39m (LTS, default) or \e[31m12.1\e[39m?"
printf "%s" "Choose [1] for 11.8 LTS (recommended), [2] for 12.1, or press Enter for default [1]: "
read TMP_YN
if [[ $TMP_YN =~ ^(2|12\.1) ]] ; then
	MARIADB_VER="12.1"
	echo -e "\nMariaDB 12.1 will be installed.\n"
else
	MARIADB_VER="11.8"
	echo -e "\nMariaDB 11.8 LTS will be installed (default).\n"
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

sed -i 's|lsws-5.4.2|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
sed -i 's|lsws-5.3.5|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
sed -i 's|lsws-6.0|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
sed -i 's|lsws-6.3.4|lsws-'$LSWS_STABLE_VER'|g' installCyberPanel.py
#this sed must be done after license validation
	
echo -e "Preparing..."
echo -e "Installation will start in 10 seconds, if you wish to stop please press CTRL + C"
sleep 10
main_install_run
}

