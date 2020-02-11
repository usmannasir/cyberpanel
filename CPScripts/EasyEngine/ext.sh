#!/bin/bash

#script to install some lsphp74 extension

SERVER_OS=""


hash yum 2>/dev/null
  if [[ $? == "0" ]] ; then
  echo -e "\nyum detected..."
  SERVER_OS="CentOS"
  fi

hash apt 2>/dev/null
  if [[ $? == "0" ]] ; then
  echo -e "\napt detected..."
  SERVER_OS="Ubuntu"
  fi

if [[ $SERVER_OS == "" ]] ; then
  echo -e "\nunable to detect the system..."
  exit
fi


if [[ ! -f /usr/local/lsws/lsphp74/lib64/php/modules/zip.so ]] && [[ $SERVER_OS == "CentOS" ]] ; then
	yum list installed libzip-devel
		if [[ $? == "0" ]] ; then
			yum remove -y libzip-devel
		fi

	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-devel-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y lsphp74-devel

	if [[ ! -d /usr/local/lsws/lsphp74/tmp ]] ; then
		mkdir /usr/local/lsws/lsphp74/tmp
	fi

	/usr/local/lsws/lsphp74/bin/pecl channel-update pecl.php.net
	/usr/local/lsws/lsphp74/bin/pear config-set temp_dir /usr/local/lsws/lsphp74/tmp
	/usr/local/lsws/lsphp74/bin/pecl install zip
	if [[ $? == 0 ]] ; then
		echo "extension=zip.so" > /usr/local/lsws/lsphp74/etc/php.d/20-zip.ini
		chmod 755 /usr/local/lsws/lsphp74/lib64/php/modules/zip.so
		echo -e "\nInstalling lsphp74-zip"
	else
		echo -e "\nlsphp74-zip compilation failed..."
	fi
fi


if [[ $SERVER_OS == "CentOS" ]] ; then
  yum install -y lsphp74-redis
  		echo -e "\nInstalling lsphp74-redis"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-redis
  		echo -e "\nInstalling lsphp74-redis"
fi

if [[ $SERVER_OS == "CentOS" ]] ; then
  yum install -y lsphp74-memcached
  		echo -e "\nInstalling lsphp74-memcached"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-memcached
  		echo -e "\nInstalling lsphp74-memcached"
fi

if [[ $SERVER_OS == "CentOS" ]] ; then
  yum install -y lsphp74-imagick
  		echo -e "\nInstalling lsphp74-imagick"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-imagick
  		echo -e "\nInstalling lsphp74-imagick"
fi




if [[ $SERVER_OS == "CentOS" ]] ; then
  yum install -y lsphp74-sodium
  		echo -e "\nInstalling lsphp74-sodium"
else
  mkdir /usr/local/lsws/cyberpanel-tmp
  cd /usr/local/lsws/cyberpanel-tmp
  DEBIAN_FRONTEND=noninteractive apt install -y libsodium-dev
  wget -O libsodium.tgz http://pecl.php.net/get/libsodium
  tar xzvf libsodium.tgz
  cd libsodium-*
  /usr/local/lsws/lsphp74/bin/phpize
  ./configure --with-php-config=/usr/local/lsws/lsphp74/bin/php-config7.4
  make
  make install
  echo "extension=sodium.so" > /usr/local/lsws/lsphp74/etc/php/7.4/mods-available/20-sodium.ini
  pkill lsphp74
  		echo -e "\nInstalling lsphp74-sodium"
fi
