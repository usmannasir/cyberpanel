#!/bin/bash
## Uninstall Mailscanner CyberPanel

### OS Detection
Server_OS=""
Server_OS_Version=""
if grep -q -E "CentOS Linux 7|CentOS Linux 8" /etc/os-release ; then
  Server_OS="CentOS"
elif grep -q "AlmaLinux-8" /etc/os-release ; then
  Server_OS="AlmaLinux"
elif grep -q -E "CloudLinux 7|CloudLinux 8" /etc/os-release ; then
  Server_OS="CloudLinux"
elif grep -q -E "Rocky Linux" /etc/os-release ; then
  Server_OS="RockyLinux"
elif grep -q -E "Ubuntu 18.04|Ubuntu 20.04|Ubuntu 20.10|Ubuntu 22.04" /etc/os-release ; then
  Server_OS="Ubuntu"
elif grep -q -E "openEuler 20.03|openEuler 22.03" /etc/os-release ; then
  Server_OS="openEuler"
else
  echo -e "Unable to detect your system..."
  echo -e "\nCyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03...\n"
  exit
fi

Server_OS_Version=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )

echo -e "System: $Server_OS $Server_OS_Version detected...\n"

if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]] ; then
  Server_OS="CentOS"
  #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
  #treat CloudLinux, Rocky and Alma as CentOS
fi

systemctl stop mailscanner


if [[ $Server_OS = "CentOS" ]] && [[ "$Server_OS_Version" = "7" ]] ; then

  yum remove -y MailScanner

elif [[ $Server_OS = "CentOS" ]] && [[ "$Server_OS_Version" = "8" ]] ; then

  yum remove -y MailScanner

elif [[ $Server_OS = "Ubuntu" ]]; then

 apt purge -y mailscanner

fi

sed -i 's/\/^Received:\/ HOLD/\/^Received:\/ IGNORE/g' /etc/postfix/header_checks
rm -rf /etc/MailScanner
rm -rf /usr/share/MailScanner
rm -rf /usr/local/CyberCP/public/mailwatch

systemctl restart postfix dovecot
