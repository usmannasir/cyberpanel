#!/bin/bash

# Working OS Versions
# CentOS 7
# Debian >=7
# Ubuntu >=14.04
# MacOS High Sierra
# FreeBSD 11
# Non Working OS Versions
# CentOS <=6
# All others are not tested.

cd `dirname "$0"`

MOD_SEC_HOME='ModSecurity/headers'

case "$OSTYPE" in
  darwin*)  OS='mac'
            ;;
  linux*)   OS='linux'
            ;;
  *BSD*)    OS='bsd'
            ;;
  *)        echo 'Operating System not supported!'
            echo 'Supported OS: Linux, Mac, and BSD'
            exit 1
            ;;
esac

if [ $OS = 'linux' ] ; then
  APP_MGRS="apt apt-get yum zypper"
elif [ $OS = 'mac' ] ; then
  APP_MGRS="brew port"
elif [ $OS = 'bsd' ] ; then
  APP_MGRS="pkg"
fi

for APP_MGR in ${APP_MGRS}; do
  APP_MGR_CHECK=`which $APP_MGR &>/dev/null`
  if [ $? -eq 0 ] ; then
    APP_MGR_CMD="$APP_MGR"
    break
  fi
done

PKGS=

#check if libModSecurity installed or not
if [ ! -f $MOD_SEC_HOME/modsecurity/modsecurity.h ] ; then

  #need to update the below for each system
  if [ $OS = 'linux' ] ; then
      EXEC="sudo $APP_MGR_CMD install -y"
      if [ $APP_MGR_CMD = 'zypper' ] ; then
          PKGS="gcc-c++ flex bison yajl yajl-devel curl-devel curl \
              GeoIP-devel doxygen zlib-devel libxml2-devel git libtool autoconf \
              automake pcre-devel"
      elif [ $APP_MGR_CMD = 'yum' ] ; then
          OS_VERSION=`cat /etc/centos-release | awk '{print $3}' | cut -c1`
          if [ $OS_VERSION = 'r' ] ; then
              #Centos 7 or later?
              OS_VERSION=`cat /etc/centos-release | awk '{print $4}' | cut -c1`
          fi
          if [ $OS_VERSION -le 6 ] ; then
              echo 'CentOS 6 and below requires manual compilation as the packages'
              echo 'are too out dated.'
              exit 1
          fi
          PKGS="gcc-c++ flex bison yajl yajl-devel curl-devel curl \
              GeoIP-devel doxygen zlib-devel libxml2-devel git autoconf automake \
              libtool pcre-devel"
      elif [ $APP_MGR_CMD = 'apt' ] || [ $APP_MGR_CMD = 'apt-get' ] ; then
          PKGS="g++ flex bison curl doxygen libyajl-dev libgeoip-dev \
              libtool dh-autoreconf libcurl4-gnutls-dev libxml2 libpcre++-dev \
              libxml2-dev automake autoconf git"
      else
          echo 'No supported package manager found. Please manully compile'
          echo 'libModSecurity or try again.'
          exit 1
      fi
  elif [ $OS = 'mac' ] ; then
      # xcode tools are required to be installed and requires sudo access.
      sudo xcode-select --install
      EXEC="sudo $APP_MGR_CMD install"
      if [ $APP_MGR_CMD = 'brew' ] ; then
          # Brew packages are all local and not system wide.
          PKGS="flex bison yajl curl libgeoip doxygen zlib libxml2 git \
              autoconf automake pcre libtool"
    elif [ $APP_MGR_CMD = 'port' ] ; then
      # Port packages are system wide and require sudo access.
      PKGS="flex bison yajl curl libgeoip doxygen zlib libxml2 git \
      autoconf automake pcre libtool"
    else
      echo 'Neither brew or port package managers were found. Please either'
      echo 'install one and re-run this or manually install the required'
      echo 'packages and build libModSecurity yourself.'
      exit 1
    fi
  elif [ $OS = 'bsd' ] ; then
    if [ $APP_MGR_CMD = 'pkg' ] ; then
      EXEC="sudo $APP_MGR_CMD install -y"
      PKGS="bison git yajl flex curl gcc doxygen GeoIP autoconf \
      libtool automake gmake"
    else
      echo 'pkg is not installed. Please either install it and re-run this'
      echo 'or use portsnap to manually install the needed packages and build'
      echo 'libModSecurity yourself.'
      exit 1
    fi
  fi

  echo "Installing using $EXEC $PKGS"
  $EXEC $PKGS
  echo "Install packages done, exit code $?"

  git clone https://github.com/SpiderLabs/ModSecurity 
  cd ModSecurity
  git checkout -b v3/master origin/v3/master
  ./build.sh
  git submodule init
  git submodule update

  echo 'It will take several minutes, please wait ...'
  if [ $OS = 'linux' ] ; then
    if [ $APP_MGR_CMD = 'apt' ] ; then
      # Configure on Ubuntu does not detect yajl inside of /usr so force it to
      # look there.
      ./configure --with-yajl=/usr
    else
      ./configure
    fi
    make
  elif [ $OS = 'mac' ] ; then
    if [ $APP_MGR_CMD = 'port' ] ; then
      # Port installs yajl to /opt/local so force it to look there.
      ./configure --with-yajl=/opt/local
    elif [ $APP_MGR_CMD = 'brew' ] ; then
      # Brew installs yajl to /usr/local so force it to look there.
      ./configure --with-yajl=/usr/local
    fi
    make
  elif [ $OS = 'bsd' ] ; then
    # Seems configure doesn't detect yajl inside of /usr/local so force it to
    # look there.
    ./configure --with-yajl=/usr/local
    # There are issues with regular make command on BSD but gmake works fine.
    gmake
  fi

  cd -
fi

if [ ! -f $MOD_SEC_HOME/modsecurity/modsecurity.h ] ; then
  echo 'Try to install libModSecurity but failed, please check your system.'
  echo 'Or contact us.'
  echo 'Thanks.'
  exit 1

elif [ ! -f ModSecurity/src/.libs/libmodsecurity.a ] ; then
  echo 'It seems downloaded the libmodsecurity source code correctly but failed to build it.'
  echo 'Please remove ModSecurity directory and try again. '
  echo 'If still can not have it fixed, please check your system or contact us.'
  echo 'Thanks.'
  exit 1

else
  echo 'Done with installation of libModSecurity.'
  echo
  exit 0
fi
