SERVER_OS='Undefined'
OUTPUT=$(cat /etc/*release)

echo -e "\nChecking OS..."
OUTPUT=$(cat /etc/*release)
if  echo $OUTPUT | grep -q "CentOS Linux 7" ; then
	echo -e "\nDetecting CentOS 7.X...\n"
	SERVER_OS="CentOS7"
	yum clean all
  yum update -y
elif echo $OUTPUT | grep -q "CloudLinux 7" ; then
	echo -e "\nDetecting CloudLinux 7.X...\n"
	SERVER_OS="CentOS7"
	yum clean all
  yum update -y
elif  echo $OUTPUT | grep -q "CentOS Linux 8" ; then
	echo -e "\nDetecting CentOS 8.X...\n"
	SERVER_OS="CentOS8"
	yum clean all
  yum update -y
elif echo $OUTPUT | grep -q "Ubuntu 18.04" ; then
	echo -e "\nDetecting Ubuntu 18.04...\n"
	SERVER_OS="Ubuntu"
else
	cat /etc/*release
	echo -e "\nUnable to detect your OS...\n"
	echo -e "\nCyberPanel is supported on Ubuntu 18.04, CentOS 7.x, CentOS 8.x and CloudLinux 7.x...\n"
	exit 1
fi

if [[ $SERVER_OS == "CentOS7" ]] ; then
  yum -y install yum-utils
  yum -y groupinstall development
  yum -y install https://centos7.iuscommunity.org/ius-release.rpm
  yum -y install python36u python36u-pip python36u-devel
elif [[ $SERVER_OS == "CentOS8" ]] ; then
  yum install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git platform-python-devel tar
	dnf --enablerepo=PowerTools install gpgme-devel -y
	dnf install python3 -y
else
  apt update -y
	DEBIAN_FRONTEND=noninteractive apt upgrade -y
	DEBIAN_FRONTEND=noninteracitve apt install -y htop telnet python-mysqldb python-dev libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadbclient-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev python-gpg python python-minimal python-setuptools virtualenv python-dev python-pip git
  DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
	DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
	DEBIAN_FRONTEND=noninteractive apt install -y python3-venv
fi

if [[ $SERVER_OS == "Ubuntu" ]] ; then
  pip3 install virtualenv
else
  pip3.6 install virtualenv
fi

rm -rf /usr/local/CyberPanel
virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
source /usr/local/CyberPanel/bin/activate
rm -rf requirments.txt
wget https://raw.githubusercontent.com/usmannasir/cyberpanel/$1/requirments.txt

if [[ $SERVER_OS == "Ubuntu" ]] ; then
  pip3 install --ignore-installed -r requirments.txt
else
  pip3.6 install --ignore-installed -r requirments.txt
fi

virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
rm -rf upgrade.py
wget https://raw.githubusercontent.com/usmannasir/cyberpanel/$1/plogical/upgrade.py
/usr/local/CyberPanel/bin/python upgrade.py $1

##

virtualenv -p /usr/bin/python3 /usr/local/CyberCP
source /usr/local/CyberCP/bin/activate
wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$1/requirments.txt
if [[ $SERVER_OS == "Ubuntu" ]] ; then
  pip3 install --ignore-installed -r requirments.txt
else
  pip3.6 install --ignore-installed -r requirments.txt
fi


##

rm -f wsgi-lsapi-1.4.tgz
rm -rf wsgi-lsapi-1.4
wget http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-1.4.tgz
tar xf wsgi-lsapi-1.4.tgz
cd wsgi-lsapi-1.4
/usr/local/CyberPanel/bin/python ./configure.py
make
cp lswsgi /usr/local/CyberCP/bin/

##

sed -i 's|import views|from . import views|g' /usr/local/CyberCP/configservercsf/urls.py
systemctl restart lscpd

echo "###################################################################"
echo "                CyberPanel Upgraded                                "
echo "###################################################################"