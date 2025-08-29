#!/bin/sh

#script to install some lsphp74 extension

SERVER_OS=""


if hash yum 2>/dev/null; then
  printf "\nyum detected...\n"
  SERVER_OS="CentOS"
fi

if hash apt 2>/dev/null; then
  printf "\napt detected...\n"
  SERVER_OS="Ubuntu"
fi

if [ "${SERVER_OS}" = "" ] ; then
  printf "\nunable to detect the system...\n"
  exit 1
fi


if [ ! -f /usr/local/lsws/lsphp74/lib64/php/modules/zip.so ] && [ "${SERVER_OS}" = "CentOS" ] ; then
    # If package is installed, remove it first
    if yum list installed libzip-devel >/dev/null 2>&1; then
      yum remove -y libzip-devel
    fi

	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y http://packages.psychotic.ninja/7/plus/x86_64/RPMS/libzip-devel-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y lsphp74-devel

  if [ ! -d /usr/local/lsws/lsphp74/tmp ] ; then
    mkdir /usr/local/lsws/lsphp74/tmp
  fi

	/usr/local/lsws/lsphp74/bin/pecl channel-update pecl.php.net
	/usr/local/lsws/lsphp74/bin/pear config-set temp_dir /usr/local/lsws/lsphp74/tmp
    if /usr/local/lsws/lsphp74/bin/pecl install zip >/dev/null 2>&1; then
      echo "extension=zip.so" > /usr/local/lsws/lsphp74/etc/php.d/20-zip.ini
      chmod 755 /usr/local/lsws/lsphp74/lib64/php/modules/zip.so
      printf "\nInstalling lsphp74-zip\n"
    else
      printf "\nlsphp74-zip compilation failed...\n"
    fi
fi


if [ "${SERVER_OS}" = "CentOS" ] ; then
  yum install -y lsphp74-redis
  printf "\nInstalling lsphp74-redis\n"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-redis
  printf "\nInstalling lsphp74-redis\n"
fi

if [ "${SERVER_OS}" = "CentOS" ] ; then
  yum install -y lsphp74-memcached
  printf "\nInstalling lsphp74-memcached\n"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-memcached
  printf "\nInstalling lsphp74-memcached\n"
fi

if [ "${SERVER_OS}" = "CentOS" ] ; then
  yum install -y lsphp74-imagick
  printf "\nInstalling lsphp74-imagick\n"
else
  DEBIAN_FRONTEND=noninteractive apt install -y lsphp74-imagick
  printf "\nInstalling lsphp74-imagick\n"
fi




if [ "${SERVER_OS}" = "CentOS" ] ; then
  yum install -y lsphp74-sodium
  printf "\nInstalling lsphp74-sodium\n"
else
  mkdir /usr/local/lsws/cyberpanel-tmp
  cd /usr/local/lsws/cyberpanel-tmp || exit
  DEBIAN_FRONTEND=noninteractive apt install -y libsodium-dev
  wget -O libsodium.tgz http://pecl.php.net/get/libsodium
  tar xzvf libsodium.tgz
  cd libsodium-* || exit 1
  /usr/local/lsws/lsphp74/bin/phpize
  ./configure --with-php-config=/usr/local/lsws/lsphp74/bin/php-config7.4
  make
  make install
  echo "extension=sodium.so" > /usr/local/lsws/lsphp74/etc/php/7.4/mods-available/20-sodium.ini
  pkill lsphp74
  printf "\nInstalling lsphp74-sodium\n"
fi
