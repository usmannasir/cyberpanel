#!/bin/sh

if [ -f "/etc/os-release" ]; then
  . /etc/os-release
else
  ID="unsupported"
  PRETTY_NAME="Your OS does not have a /etc/os-release file"
fi

if [ "$ID" = "ubuntu" ] && [ "$UBUNTU_CODENAME" = "bionic" ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt -q -y -o Dpkg::Options::=--force-confnew update
  apt -q -y -o Dpkg::Options::=--force-confnew install wget curl
  SERVER_OS="Ubuntu"
elif [ "$ID" = "centos" ] || [ "$ID" = "cloudlinux" ]; then
  case "$VERSION_ID" in
    7|7.*)
      yum install curl wget -y 1> /dev/null
      yum update curl wget ca-certificates -y 1> /dev/null
      if [ "$ID" = "centos" ]; then
        SERVER_OS="CentOS"
      else
        SERVER_OS="CloudLinux"
      fi
      ;;
    8|8.*)
      printf >&2 '\nCentOS 8/CloudLinux 8 support is currently experimental!\n'
      yum install curl wget -y 1> /dev/null
      yum update curl wget ca-certificates -y 1> /dev/null
      SERVER_OS="CentOS8"
      ;;
  esac
else
  printf >&2 '\nYour OS -- %s -- is not currently supported!\n' "$PRETTY_NAME"
  printf >&2 '\nCyberPanel is currently supported on Ubuntu 18.04, CentOS 7 and CloudLinux 7.\n'
  exit 1
fi

rm -f cyberpanel.sh install.tar.gz
curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&${SERVER_OS}" 2>/dev/null
chmod +x cyberpanel.sh
./cyberpanel.sh "$@"
