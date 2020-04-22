#!/bin/bash
#CyberPanel Upgrade script

export LC_CTYPE=en_US.UTF-8
SUDO_TEST=$(set)
SERVER_OS='Undefined'
OUTPUT=$(cat /etc/*release)
TEMP=$(curl --silent https://cyberpanel.net/version.txt)
BRANCH_NAME=v${TEMP:12:3}.${TEMP:25:1}
GIT_URL="github.com/usmannasir/cyberpanel"
GIT_CONTENT_URL="raw.githubusercontent.com/usmannasir/cyberpanel"
SERVER_COUNTRY="unknow"
SERVER_COUNTRY=$(curl --silent --max-time 5 https://cyberpanel.sh/?country)
if [[ ${#SERVER_COUNTRY} == "2" ]] || [[ ${#SERVER_COUNTRY} == "6" ]] ; then
	echo -e "\nChecking server..."
else
	echo -e "\nChecking server..."
	SERVER_COUNTRY="unknow"
fi

#SERVER_COUNTRY="CN"
#for test

if [[ $SERVER_COUNTRY == "CN" ]] ; then
	GIT_URL="gitee.com/qtwrk/cyberpanel"
	GIT_CONTENT_URL="gitee.com/qtwrk/cyberpanel/raw"
fi

regenerate_cert() {
cat << EOF > /usr/local/CyberCP/cert_conf
[req]
prompt=no
distinguished_name=cyberpanel
[cyberpanel]
commonName = www.example.com
countryName = CP
localityName = CyberPanel
organizationName = CyberPanel
organizationalUnitName = CyberPanel
stateOrProvinceName = CP
emailAddress = mail@example.com
name = CyberPanel
surname = CyberPanel
givenName = CyberPanel
initials = CP
dnQualifier = CyberPanel
[server_exts]
extendedKeyUsage = 1.3.6.1.5.5.7.3.1
EOF
if [[ $1 == "8090" ]] ; then
openssl req -x509 -config /usr/local/CyberCP/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout /usr/local/lscp/conf/key.pem -out /usr/local/lscp/conf/cert.pem
fi

if [[ $1 == "7080" ]] ; then
	if [[ -f /usr/local/lsws/admin/conf/webadmin.key ]] ; then
		key_path="/usr/local/lsws/admin/conf/webadmin.key"
		cert_path="/usr/local/lsws/admin/conf/webadmin.crt"
	else
		key_path="/usr/local/lsws/admin/conf/cert/admin.key"
		cert_path="/usr/local/lsws/admin/conf/cert/admin.crt"
	fi
openssl req -x509 -config /usr/local/CyberCP/cert_conf -extensions 'server_exts' -nodes -days 820 -newkey rsa:2048 -keyout $key_path -out $cert_path
fi
rm -f /usr/local/CyberCP/cert_conf

}

input_branch() {
	echo -e "\nPress Enter key to continue with latest version or Enter specific version such as: \e[31m1.9.4\e[39m , \e[31m1.9.5\e[39m ...etc"
	echo -e "\nIf nothing is input in 10 seconds , script will proceed with latest stable. "
	echo -e "\nPlease press Enter key , or specify a version number ,or wait for 10 seconds timeout: "
	printf "%s" ""
	read -t 10 TMP_YN

	if [[ $TMP_YN == "" ]] ; then
		BRANCH_NAME="v${TEMP:12:3}.${TEMP:25:1}"
		echo -e "\nBranch name set to $BRANCH_NAME"
	else
		base_number="1.9.3"
			if [[ $TMP_YN == *.*.* ]] ; then
				#check input if it's valid format as X.Y.Z
				output=$(awk -v num1="$base_number" -v num2="$TMP_YN" '
				BEGIN {
					print "num1", (num1 < num2 ? "<" : ">="), "num2"
				}
				')
				if [[ $output == *">="* ]] ; then
					echo -e "\nYou must use version number higher than 1.9.4"
					exit
				else
					BRANCH_NAME="v$TMP_YN"
					echo "set branch name to $BRANCH_NAME"
				fi
			else
				echo -e "\nPlease input a valid format version number."
				exit
			fi
	fi
}

install_utility() {
if [[ ! -f /usr/bin/cyberpanel_utility ]] ; then
wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
chmod 700 /usr/bin/cyberpanel_utility
fi
}

check_root() {
echo -e "\nChecking root privileges...\n"
if echo $SUDO_TEST | grep SUDO > /dev/null ; then
	echo -e "\nYou are using SUDO , please run as root user...\n"
	echo -e "\nIf you don't have direct access to root user, please run \e[31msudo su -\e[39m command (do NOT miss the \e[31m-\e[39m at end or it will fail) and then run upgrade command again."
	exit
fi

if [[ $(id -u) != 0 ]]  > /dev/null; then
	echo -e "\nYou must use root user to upgrade CyberPanel...\n"
	exit
else
	echo -e "\nYou are runing as root...\n"
fi
}


check_return() {
#check previous command result , 0 = ok ,  non-0 = something wrong.
if [[ $? -eq "0" ]] ; then
	:
else
	echo -e "\ncommand failed, exiting..."
	exit
fi
}

input_branch

check_root

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

if [ $SERVER_OS = "CentOS7" ] ; then
  yum -y install yum-utils
  yum -y groupinstall development
  yum -y install https://centos7.iuscommunity.org/ius-release.rpm
  yum -y install python36u python36u-pip python36u-devel
elif [ $SERVER_OS = "CentOS8" ] ; then
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

if [ $SERVER_OS = "Ubuntu" ] ; then
  pip3 install virtualenv
  check_return
else
  pip3.6 install virtualenv==16.7.9
  check_return
fi

rm -rf /usr/local/CyberPanel
virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
check_return
rm -f requirments.txt
wget -O requirements.txt https://$GIT_CONTENT_URL/${BRANCH_NAME}/requirments.txt
. /usr/local/CyberPanel/bin/activate
check_return

if [ $SERVER_OS = "Ubuntu" ] ; then
  . /usr/local/CyberPanel/bin/activate
  check_return
  pip3 install --ignore-installed -r requirements.txt
  check_return
else
  source /usr/local/CyberPanel/bin/activate
  check_return
  pip3.6 install --ignore-installed -r requirements.txt
  check_return
fi

virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
check_return
rm -rf upgrade.py
wget https://$GIT_CONTENT_URL/${BRANCH_NAME}/plogical/upgrade.py

if [[ $SERVER_COUNTRY == "CN" ]] ; then
sed -i 's|wget  https://raw.githubusercontent.com/usmannasir/cyberpanel/v1.9.4/lscpd-0.2.4 -P /usr/local/lscp/bin/|cp -f /usr/local/CyberCP/lscpd-0.2.4 /usr/local/lscp/bin/lscpd-0.2.4|g' upgrade.py
sed -i 's|wget  https://raw.githubusercontent.com/usmannasir/cyberpanel/%s/lscpd-0.2.4 -P /usr/local/lscp/bin/|cp -f /usr/local/CyberCP/lscpd-0.2.4 /usr/local/lscp/bin/lscpd-0.2.4|g' upgrade.py
sed -i $'s/0.2.4\' % (branch)/0.2.4\'/' upgrade.py
sed -i 's|raw.githubusercontent.com/usmannasir/cyberpanel|'${GIT_CONTENT_URL}'|g' upgrade.py
sed -i 's|git clone https://github.com/usmannasir/cyberpanel|git clone https://'${GIT_URL}'|g' upgrade.py
fi

/usr/local/CyberPanel/bin/python upgrade.py $BRANCH_NAME
check_return
virtualenv -p /usr/bin/python3 /usr/local/CyberCP
check_return
wget -O requirements.txt https://$GIT_CONTENT_URL/${BRANCH_NAME}/requirments.txt

if [ $SERVER_OS = "Ubuntu" ] ; then
  . /usr/local/CyberCP/bin/activate
  check_return
  pip3 install --ignore-installed -r requirements.txt
  check_return
else
  source /usr/local/CyberCP/bin/activate
  check_return
  pip3.6 install --ignore-installed -r requirements.txt
  check_return
fi


##

rm -f wsgi-lsapi-1.5.tgz
rm -rf wsgi-lsapi-1.4
wget http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-1.5.tgz
tar xf wsgi-lsapi-1.5.tgz
cd wsgi-lsapi-1.5
/usr/local/CyberPanel/bin/python ./configure.py
make

cp lswsgi /usr/local/CyberCP/bin/

sed -i 's|python2|python|g' /usr/bin/adminPass
chmod 700 /usr/bin/adminPass

if [[ ! -f /usr/sbin/ipset ]] && [[ $SERVER_OS == "Ubuntu" ]] ; then
ln -s /sbin/ipset /usr/sbin/ipset
fi

if [[ -f /etc/cyberpanel/webadmin_passwd ]] ; then
chmod 600 /etc/cyberpanel/webadmin_passwd
fi

if [[ -f /etc/pure-ftpd/pure-ftpd.conf ]] ; then
sed -i 's|NoAnonymous                 no|NoAnonymous                 yes|g' /etc/pure-ftpd/pure-ftpd.conf
fi


install_utility

output=$(timeout 3 openssl s_client -connect 127.0.0.1:8090 2>/dev/null)
echo $output | grep -q "mail@example.com"
if [[ $? == "0" ]] ; then
# it is using default installer generated cert
regenerate_cert 8090
fi
output=$(timeout 3 openssl s_client -connect 127.0.0.1:7080 2>/dev/null)
echo $output | grep -q "mail@example.com"
if [[ $? == "0" ]] ; then
regenerate_cert 7080
fi


if [[ $SERVER_OS == "CentOS7" ]] ; then

sed -i 's|error_reporting = E_ALL \&amp; ~E_DEPRECATED \&amp; ~E_STRICT|error_reporting = E_ALL \& ~E_DEPRECATED \& ~E_STRICT|g' /usr/local/lsws/{lsphp72,lsphp73}/etc/php.ini
#fix php.ini &amp; issue

yum list installed lsphp74-devel
	if [[ $? != "0" ]] ; then
		yum install -y lsphp74-devel
	fi
fi

if [[ $SERVER_OS == "Ubuntu" ]] ; then
 dpkg -l lsphp74-dev > /dev/null 2>&1
	if [[ $? != "0" ]] ; then
	apt install -y lsphp74-dev
	fi
fi

if [[ ! -f /usr/local/lsws/lsphp74/lib64/php/modules/zip.so ]] && [[ $SERVER_OS == "CentOS7" ]] ; then
	yum list installed libzip-devel > /dev/null 2>&1
		if [[ $? == "0" ]] ; then
			yum remove -y libzip-devel
		fi

	yum install -y https://cdn.cyberpanel.sh/misc/libzip-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install -y https://cdn.cyberpanel.sh/misc/libzip-devel-0.11.2-6.el7.psychotic.x86_64.rpm
	yum install lsphp74-devel

	if [[ ! -d /usr/local/lsws/lsphp74/tmp ]] ; then
		mkdir /usr/local/lsws/lsphp74/tmp
	fi

	/usr/local/lsws/lsphp74/bin/pecl channel-update pecl.php.net
	/usr/local/lsws/lsphp74/bin/pear config-set temp_dir /usr/local/lsws/lsphp74/tmp
	/usr/local/lsws/lsphp74/bin/pecl install zip
	if [[ $? == 0 ]] ; then
		echo "extension=zip.so" > /usr/local/lsws/lsphp74/etc/php.d/20-zip.ini
		chmod 755 /usr/local/lsws/lsphp74/lib64/php/modules/zip.so
	else
		echo -e "\nlsphp74-zip compilation failed..."
	fi
fi
#fix the lsphp74-zip missing issue.


##
systemctl restart lscpd

rm -f requirements.txt
rm -f requirments.txt
rm -f upgrade.py
rm -rf wsgi-lsapi-1.5
rm -f wsgi-lsapi-1.5.tgz
rm -f /usr/local/composer.sh

# clean up

echo "###################################################################"
echo "                CyberPanel Upgraded                                "
echo "###################################################################"
