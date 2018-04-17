#!/bin/bash
yum autoremove epel-release -y
rm -f /etc/yum.repos.d/epel.repo
rm -f /etc/yum.repos.d/epel.repo.rpmsave
yum install epel-release -y
#some provider's centos7 template come with incorrect or misconfigured epel.repo
if systemctl is-active named | grep -q 'active'; then
  systemctl stop named
  systemctl disable named
  echo "Disabling named to aviod powerdns conflicts..."
  else
  echo "named is not installed or active, to next step..."
fi
# above if will check if server has named.service running that occupies port 53 which makes powerdns failed to start
yum clean all
yum update -y
yum install wget which curl -y
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
wget https://mirror.cyberpanel.net/install-cn.tar.gz
tar xzvf install-cn.tar.gz
cd install-cn
chmod +x install.py
server_ip="$(wget -qO- http://whatismyip.akamai.com/)"
python install.py $server_ip
