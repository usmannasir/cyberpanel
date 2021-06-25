#!/bin/bash
## Uninstall Mailscanner CyberPanel

if [ -f /etc/os-release ]; then
  OS=$(head -1 /etc/os-release)
  UBUNTUVERSION=$(sed '6q;d' /etc/os-release)
  CENTOSVERSION=$(sed '5q;d' /etc/os-release)
  CLNVERSION=$(sed '3q;d' /etc/os-release)
fi

systemctl stop mailscanner

if [ "$OS" = "NAME=\"Ubuntu\"" ]; then
  apt purge -y mailscanner

elif
  [ "$OS" = "NAME=\"CentOS Linux\"" ]
then
  yum remove -y MailScanner

elif [ "$OS" = "NAME=\"CloudLinux\"" ]; then
  yum remove -y MailScanner

fi

sed -i 's/\/^Received:\/ HOLD/\/^Received:\/ IGNORE/g' /etc/postfix/header_checks
rm -rf /etc/MailScanner
rm -rf /usr/share/MailScanner
rm -rf /usr/local/CyberCP/public/mailwatch

systemctl restart postfix dovecot
