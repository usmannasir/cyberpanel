#!/bin/sh

OUTPUT=$(cat /etc/*release)
if  echo $OUTPUT | grep -q "CentOS Linux 7" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CentOS"
elif echo $OUTPUT | grep -q "CentOS Linux 8" ; then
        echo -e "\nDetecting Centos 8...\n"
        SERVER_OS="CentOS8"
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
elif echo $OUTPUT | grep -q "CloudLinux 7" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CloudLinux"
elif echo $OUTPUT | grep -q "CloudLinux 8" ; then
        echo "Checking and installing curl and wget"
yum install curl wget -y 1> /dev/null
yum update curl wget ca-certificates -y 1> /dev/null
                SERVER_OS="CloudLinux"
elif echo $OUTPUT | grep -q "Ubuntu 18.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 24.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "Ubuntu 26.04" ; then
apt install -y -qq wget curl
                SERVER_OS="Ubuntu"
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
                echo -e "\nCyberPanel is supported on Ubuntu 18.04, Ubuntu 20.04, Ubuntu 22.04, Ubuntu 24.04, Ubuntu 26.04, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10 and CloudLinux 7.x...\n"
                exit 1
fi

rm -f cyberpanel.sh
rm -f install.tar.gz

CYBERPANEL_GIT_USER="${CYBERPANEL_GIT_USER:-usmannasir}"
CYBERPANEL_BRANCH="${CYBERPANEL_BRANCH:-}"
export CYBERPANEL_GIT_USER CYBERPANEL_BRANCH

INSTALL_BRANCH="$CYBERPANEL_BRANCH"
EXPECT_BRANCH=0
for argument do
        if [ "$EXPECT_BRANCH" -eq 1 ]; then
                INSTALL_BRANCH="$argument"
                EXPECT_BRANCH=0
        elif [ "$argument" = "-b" ] || [ "$argument" = "--branch" ]; then
                EXPECT_BRANCH=1
        elif [ "$argument" = "-r" ] || [ "$argument" = "--repo" ]; then
                EXPECT_BRANCH=2
        elif [ "$EXPECT_BRANCH" -eq 2 ]; then
                CYBERPANEL_GIT_USER="$argument"
                export CYBERPANEL_GIT_USER
                EXPECT_BRANCH=0
        fi
done

case "$INSTALL_BRANCH" in
        "") ;;
        *[!A-Za-z0-9._/-]*) INSTALL_BRANCH="" ;;
        [0-9]*) INSTALL_BRANCH="v$INSTALL_BRANCH" ;;
        v*) ;;
        *) INSTALL_BRANCH="v$INSTALL_BRANCH" ;;
esac
if [ -n "$INSTALL_BRANCH" ]; then
        export CYBERPANEL_BRANCH="$INSTALL_BRANCH"
fi

if [ -n "$INSTALL_BRANCH" ]; then
        INSTALLER_URL="https://raw.githubusercontent.com/${CYBERPANEL_GIT_USER}/cyberpanel/${INSTALL_BRANCH}/cyberpanel.sh"
        if ! curl --fail --location --silent --show-error -o cyberpanel.sh "$INSTALLER_URL" ; then
                echo "Failed to download installer from ${INSTALLER_URL}" >&2
                curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null || exit 1
        fi
else
        # No branch selected: historical CDN bootstrap
        curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null || exit 1
fi
chmod +x cyberpanel.sh
./cyberpanel.sh $@
