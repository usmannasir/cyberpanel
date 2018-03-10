#!/bin/bash
yum clean all
yum update -y
yum install wget which curl -y
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
wget https://mirror.cyberpanel.net/install-cn.tar.gz
tar xzvf install-cn.tar.gz
cd install
chmod +x install.py
server_ip="$(wget -qO- http://whatismyip.akamai.com/)"
python install.py $server_ip