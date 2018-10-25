#!/bin/bash
#yum autoremove epel-release -y
#rm -f /etc/yum.repos.d/epel.repo
#rm -f /etc/yum.repos.d/epel.repo.rpmsave
#yum install epel-release -y
#some provider's centos7 template come with incorrect or misconfigured epel.repo
#if systemctl is-active named | grep -q 'active'; then
#  systemctl stop named
#  systemctl disable named
#  echo "Disabling named to aviod powerdns conflicts..."
#  else
#  echo "named is not installed or active, to next step..."
#fi
# above if will check if server has named.service running that occupies port 53 which makes powerdns failed to start
apt-get clean all
apt-get update -y
apt-get install curl -y
#setenforce 0
#sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
#wget https://cyberpanel.net/install.tar.gz
#tar xzvf install.tar.gz
apt-get install python -y
apt-get install git -y
#git clone https://github.com/rperper/cyberpanel.git 
cd cyberpanel
cd install
chmod +x install.py
server_ip="$(wget -qO- http://whatismyip.akamai.com/)"
python install.py $server_ip
