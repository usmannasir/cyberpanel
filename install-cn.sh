#!/bin/bash

function get_python_version(){
	#获取本机python版本号。这里2>&1是必须的，python -V这个是标准错误输出的，需要转换
    U_V1=`python -V 2>&1|awk '{print $2}'|awk -F '.' '{print $1}'`
    U_V2=`python -V 2>&1|awk '{print $2}'|awk -F '.' '{print $2}'`
    U_V3=`python -V 2>&1|awk '{print $2}'|awk -F '.' '{print $3}'`
    echo $U_V1.$U_V2.$U_V3
}

# V1 > V2
function version_gt() { test "$(echo "$@" | tr " " "\n" | sort -V | head -n 1)" != "$1"; }
# V1 >= V2
function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -rV | head -n 1)" == "$1"; }
# V1 <= V2
function version_le() { test "$(echo "$@" | tr " " "\n" | sort -V | head -n 1)" == "$1"; }
# V1 < V2
function version_lt() { test "$(echo "$@" | tr " " "\n" | sort -rV | head -n 1)" != "$1"; }



SYSTEM_VERSION=$(cat /etc/redhat-release|sed -r 's/.* ([0-9]+)\..*/\1/')
PYTHON_VERSION=$(python -V|sed -r 's/.* ([0-9]+)\..*/\1/')
SYSTEM_VERSION=$(cat /etc/redhat-release|sed -r 's/.* ([0-9]+)\..*/\1/')
PYTHON_VERSION=$(get_python_version)


echo 系统：$ID
echo 版本：$SYSTEM_VERSION
if [[ $SYSTEM_VERSION -le 7 ]] && version_le $PYTHON_VERSION 2.7; then
	echo "prepare to upgrade python."
	yum update -y
	rpm --import http://linuxsoft.cern.ch/cern/slc68/x86_64/RPM-GPG-KEY-cern
	wget -O /etc/yum.repos.d/slc6-devtoolset.repo http://linuxsoft.cern.ch/cern/devtoolset/slc6-devtoolset.repo
	yum groupinstall -y "Development tools"
	yum install devtoolset-2-toolchain -y
	source /opt/rh/devtoolset-2/enable
	echo "source /opt/rh/devtoolset-2/enable" >> ~/.bashrc 
	yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel
	cd ~
	if [[ ! -x ~/Python-2.7.14.tgz ]]; then
		rm -rf Python-2.7.14.tgz* 
	fi
	wget https://www.python.org/ftp/python/2.7.14/Python-2.7.14.tgz
	tar zxf Python-2.7.14.tgz
	cd Python-2.7.14
	echo "updating python"
	./configure
	make && make install
	cd ~
	echo "configure python"
	mv /usr/bin/python /usr/bin/python.old
	rm -f /usr/bin/python-config
	ln -s /usr/local/bin/python /usr/bin/python
	ln -s /usr/local/bin/python-config /usr/bin/python-config
	ln -s /usr/local/include/python2.7/ /usr/include/python2.7
	echo "install pip"
	wget https://bootstrap.pypa.io/ez_setup.py -O - | python
	easy_install pip
	pip install distribute
	echo "fix yum"
	cp -r /usr/lib/python2.6/site-packages/yum /usr/local/lib/python2.7/site-packages/
	cp -r /usr/lib/python2.6/site-packages/rpmUtils /usr/local/lib/python2.7/site-packages/
	cp -r /usr/lib/python2.6/site-packages/iniparse /usr/local/lib/python2.7/site-packages/
	cp -r /usr/lib/python2.6/site-packages/urlgrabber /usr/local/lib/python2.7/site-packages/
	cp -r /usr/lib64/python2.6/site-packages/rpm /usr/local/lib/python2.7/site-packages/
	cp -r /usr/lib64/python2.6/site-packages/curl /usr/local/lib/python2.7/site-packages/
	cp -p /usr/lib64/python2.6/site-packages/pycurl.so /usr/local/lib/python2.7/site-packages/
	cp -p /usr/lib64/python2.6/site-packages/_sqlitecache.so /usr/local/lib/python2.7/site-packages/
	cp -p /usr/lib64/python2.6/site-packages/sqlitecachec.py /usr/local/lib/python2.7/site-packages/
	cp -p /usr/lib64/python2.6/site-packages/sqlitecachec.pyc /usr/local/lib/python2.7/site-packages/
	cp -p /usr/lib64/python2.6/site-packages/sqlitecachec.pyo /usr/local/lib/python2.7/site-packages/
fi
yum autoremove epel-release -y || yum remove epel-release -y
rm -f /etc/yum.repos.d/epel.repo
rm -f /etc/yum.repos.d/epel.repo.rpmsave
yum clean all
yum install epel-release -y
#some provider's centos7 template come with incorrect or misconfigured epel.repo
yum update -y 
if systemctl is-active named | grep -q 'active'; then
  systemctl stop named
  systemctl disable named
  echo "Disabling named to aviod powerdns conflicts..."
elif chkconfig --list | grep -q 'named'; then
  service named stop
  chkconfig --del named
  echo "Disabling named to aviod powerdns conflicts..."
else
  echo "named is not installed or active, to next step..."
fi

# above if will check if server has named.service running that occupies port 53 which makes powerdns failed to start
yum clean all
yum update -y
yum install wget which curl git virt-what -y
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
cd ~
git clone https://github.com/jimorsm/cyberpanel.git
cd cyberpanel/install-cn
chmod +x install.py
server_ip="$(wget -qO- http://whatismyip.akamai.com/)"
python install.py $server_ip