#!/bin/bash
yum autoremove epel-release -y
rm -f /etc/yum.repos.d/epel.repo
rm -f /etc/yum.repos.d/epel.repo.rpmsave
yum install epel-release -y
#some provider's centos7 template come with incorrect or misconfigured epel.repo
yum clean all
yum update -y
yum install wget which curl -y
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
wget https://cyberpanel.net/install.tar.gz
tar xzvf install.tar.gz
cd install
chmod +x install.py
server_ip="$(wget -qO- http://whatismyip.akamai.com/)"
python install.py $server_ip
