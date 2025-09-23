#!/bin/sh

OUTPUT=$(cat /etc/*release)
if  echo $OUTPUT | grep -q "CentOS Linux 7" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CentOS"
elif echo $OUTPUT | grep -q "CentOS Stream 9" ; then
        echo -e "\nDetecting Centos Stream 9...\n"
        SERVER_OS="CentOSStream9"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "AlmaLinux 8" ; then
        echo -e "\nDetecting AlmaLinux 8...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "AlmaLinux 9" ; then
        echo -e "\nDetecting AlmaLinux 9...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "AlmaLinux 10" ; then
        echo -e "\nDetecting AlmaLinux 10...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "CloudLinux 8" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CloudLinux"
elif echo $OUTPUT | grep -q "CloudLinux 9" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CloudLinux"
elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 24.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 24.04.3" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Debian GNU/Linux 11" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Debian GNU/Linux 12" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Debian GNU/Linux 13" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Rocky Linux 8" ; then
        echo -e "\nDetecting Rocky Linux 8...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "Rocky Linux 9" ; then
        echo -e "\nDetecting Rocky Linux 9...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "Red Hat Enterprise Linux 8" ; then
        echo -e "\nDetecting RHEL 8...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "Red Hat Enterprise Linux 9" ; then
        echo -e "\nDetecting RHEL 9...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "CentOS Linux 9" ; then
        echo -e "\nDetecting CentOS 9...\n"
        SERVER_OS="CentOS8"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "openEuler 20.03" ; then
        echo -e "\nDetecting openEuler 20.03...\n"
        SERVER_OS="openEuler"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
elif echo $OUTPUT | grep -q "openEuler 22.03" ; then
        echo -e "\nDetecting openEuler 22.03...\n"
        SERVER_OS="openEuler"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
else

                echo -e "\nUnable to detect your OS...\n"
                echo -e "\nCyberPanel is supported on:\n"
                echo -e "Ubuntu: 20.04, 22.04, 24.04, 24.04.3\n"
                echo -e "Debian: 11, 12, 13\n"
                echo -e "AlmaLinux: 8, 9, 10\n"
                echo -e "RockyLinux: 8, 9\n"
                echo -e "RHEL: 8, 9\n"
                echo -e "CentOS: 7, 9, Stream 9\n"
                echo -e "CloudLinux: 8, 9\n"
                echo -e "openEuler: 20.03, 22.03\n"
                exit 1
fi

rm -f cyberpanel.sh
rm -f install.tar.gz
curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null
chmod +x cyberpanel.sh
./cyberpanel.sh $@