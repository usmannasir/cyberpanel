#!/usr/bin/env bash
# install/venvsetup part 4 – after_install

after_install() {
if [ ! -d "/var/lib/php" ]; then
	mkdir /var/lib/php
fi

if [ ! -d "/var/lib/php/session" ]; then
	mkdir /var/lib/php/session
fi

chmod 1733 /var/lib/php/session

if grep "\[ERROR\] We are not able to run ./install.sh return code: 1.  Fatal error, see /var/log/installLogs.txt for full details" /var/log/installLogs.txt > /dev/null; then 
	cd ${DIR}/cyberpanel/install/lsws-*
	./install.sh
	echo -e "\n\n\nIt seems LiteSpeed Enterprise has failed to install, please check your license key is valid"
	echo -e "\nIf this license key has been used before, you may need to go to store to release it first."
	exit
fi


if grep "CyberPanel installation successfully completed" /var/log/installLogs.txt > /dev/null; then

if [[ $DEV == "ON" ]] ; then
python3.6 -m venv /usr/local/CyberCP
source /usr/local/CyberCP/bin/activate

# Try to download requirements file with fallback options
echo "Attempting to download requirements for branch/commit: $BRANCH_NAME"

# First try the specified branch/commit
if wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments.txt 2>/dev/null; then
	echo "Successfully downloaded requirements from $BRANCH_NAME"
elif wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/requirments-old.txt 2>/dev/null; then
	echo "Successfully downloaded requirements-old.txt from $BRANCH_NAME"
elif wget -O requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/requirments.txt 2>/dev/null; then
	echo "Fallback: Downloaded requirements from stable branch"
else
	echo "Warning: Could not download requirements file, using minimal default requirements"
	cat > requirements.txt << 'EOF'
# Minimal CyberPanel requirements - fallback when requirements file is not available
Django==3.2.25
PyMySQL==1.1.0
requests==2.31.0
cryptography==41.0.7
psutil==5.9.6
EOF
fi

safe_pip_install "pip3.6" "requirements.txt" "--ignore-installed"
pip3.6 install python-dotenv 2>/dev/null || echo "⚠️  python-dotenv (after_install) skipped or failed"
systemctl restart lscpd
fi

for version in $(ls /usr/local/lsws | grep lsphp); 
	do
		php_ini=$(find /usr/local/lsws/$version/ -name php.ini)
		version2=${version:5:2}
		version2=$(awk "BEGIN { print "${version2}/10" }")
				if [[ $version2 = "7" ]] ; then
					version2="7.0"
				fi
		if [[ $SERVER_OS == "CentOS" ]] ; then
		yum remove -y $version-mysql
		yum install -y $version-mysqlnd
		yum install -y $version-devel make gcc glibc-devel libmemcached-devel zlib-devel
			if [[ ! -d /usr/local/lsws/$version/tmp ]] ; then
				mkdir /usr/local/lsws/$version/tmp
			fi
		/usr/local/lsws/${version}/bin/pecl channel-update pecl.php.net; 
		/usr/local/lsws/${version}/bin/pear config-set temp_dir /usr/local/lsws/${version}/tmp
		/usr/local/lsws/${version}/bin/pecl install timezonedb
		echo "extension=timezonedb.so" > /usr/local/lsws/${version}/etc/php.d/20-timezone.ini
		sed -i 's|expose_php = On|expose_php = Off|g' $php_ini
		sed -i 's|mail.add_x_header = On|mail.add_x_header = Off|g' $php_ini
		sed -i 's|;session.save_path = "/tmp"|session.save_path = "/var/lib/php/session"|g' $php_ini
		fi
		
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			if [[ ! -d /usr/local/lsws/cyberpanel-tmp ]] ; then
				echo "yes" > /etc/pure-ftpd/conf/ChrootEveryone
				systemctl restart pure-ftpd-mysql
				DEBIAN_FRONTEND=noninteractive apt install libmagickwand-dev pkg-config build-essential -y
				mkdir /usr/local/lsws/cyberpanel-tmp
				cd /usr/local/lsws/cyberpanel-tmp
				wget https://pecl.php.net/get/timezonedb-2019.3.tgz
				tar xzvf timezonedb-2019.3.tgz
				cd timezonedb-2019.3
			fi
		/usr/local/lsws/${version}/bin/phpize
		./configure --with-php-config=/usr/local/lsws/${version}/bin/php-config${version2}
		make
		make install
		# Only create .ini file if extension was successfully installed
		# Check if timezonedb.so exists in the extension directory
		ext_dir=$(/usr/local/lsws/${version}/bin/php-config${version2} --extension-dir)
		if [[ -f "${ext_dir}/timezonedb.so" ]] ; then
			mkdir -p /usr/local/lsws/${version}/etc/php/${version2}/mods-available
			echo "extension=timezonedb.so" > /usr/local/lsws/${version}/etc/php/${version2}/mods-available/20-timezone.ini
		fi
		make clean
	fi
done

rm -rf /etc/profile.d/cyberpanel*
curl --silent -o /etc/profile.d/cyberpanel.sh https://cyberpanel.sh/?banner 2>/dev/null
chmod +x /etc/profile.d/cyberpanel.sh
RAM2=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
DISK2=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
ELAPSED="$(($SECONDS / 3600)) hrs $((($SECONDS / 60) % 60)) min $(($SECONDS % 60)) sec"
MYSQLPASSWD=$(cat /etc/cyberpanel/mysqlPassword)
echo "$ADMIN_PASS" > /etc/cyberpanel/adminPass
/usr/local/CyberPanel/bin/python2 /usr/local/CyberCP/plogical/adminPass.py --password $ADMIN_PASS
systemctl restart lscpd
systemctl restart lsws
echo "/usr/local/CyberPanel/bin/python2 /usr/local/CyberCP/plogical/adminPass.py --password \"\$@\"" > /usr/bin/adminPass
echo "systemctl restart lscpd" >> /usr/bin/adminPass
chmod +x /usr/bin/adminPass
if [[ $VERSION = "OLS" ]] ; then
	WORD="OpenLiteSpeed"
#	sed -i 's|maxConnections               10000|maxConnections               100000|g' /usr/local/lsws/conf/httpd_config.conf
#	OLS_LATEST=$(curl https://openlitespeed.org/packages/release)
#	wget https://openlitespeed.org/packages/openlitespeed-$OLS_LATEST.tgz
#	tar xzvf openlitespeed-$OLS_LATEST.tgz
#	cd openlitespeed
#	./install.sh
	/usr/local/lsws/bin/lswsctrl stop
	/usr/local/lsws/bin/lswsctrl start
#	rm -f openlitespeed-$OLS_LATEST.tgz
#	rm -rf openlitespeed
#	cd ..
fi
if [[ $VERSION = "ENT" ]] ; then
	WORD="LiteSpeed Enterprise"
	if [[ $SERVER_COUNTRY != "CN" ]] ; then
		/usr/local/lsws/admin/misc/lsup.sh -f -v $LSWS_STABLE_VER
	fi
fi

systemctl status lsws 2>&1>/dev/null
if [[ $? == "0" ]] ; then
	echo "LSWS service is running..."
else
	systemctl stop lsws
	systemctl start lsws
fi

clear
echo "###################################################################"
echo "                CyberPanel Successfully Installed                  "
echo "                                                                   "
echo "                Current Disk usage : $DISK2                        "
echo "                                                                   "
echo "                Current RAM  usage : $RAM2                         "
echo "                                                                   "
echo "                Installation time  : $ELAPSED                      "
echo "                                                                   "
echo "                Visit: https://$SERVER_IP:8090                     "
echo "                Panel username: admin                              "
echo "                Panel password: $ADMIN_PASS                            "
#echo "                Mysql username: root                               "
#echo "                Mysql password: $MYSQLPASSWD                       "
echo "                                                                   "
echo "            Please change your default admin password              "
echo "          If you need to reset your panel password, please run:    "
echo "        	adminPass YOUR_NEW_PASSWORD     					   "
echo "                                                                   "
echo "          If you change mysql password, please  modify file in     "
echo -e "         \e[31m/etc/cyberpanel/mysqlPassword\e[39m with new password as well   "
echo "                                                                   "
echo "              Website : https://www.cyberpanel.net                 "
echo "              Forums  : https://forums.cyberpanel.net              "
echo "              Wikipage: https://cyberpanel.net/KnowledgeBase/                "
echo "                                                                   "
echo -e "            Enjoy your accelerated Internet by                  "
echo -e "                CyberPanel & $WORD					                     "
echo "###################################################################"
if [[ $PROVIDER != "undefined" ]] ; then
	echo -e "\033[0;32m$PROVIDER\033[39m detected..."
	echo -e "This provider has a \e[31mnetwork-level firewall\033[39m"
else
	echo -e "If your provider has a \e[31mnetwork-level firewall\033[39m"
fi
	echo -e "Please make sure you have opened following port for both in/out:"
	echo -e "\033[0;32mTCP: 8090\033[39m for CyberPanel"
	echo -e "\033[0;32mTCP: 80\033[39m, \033[0;32mTCP: 443\033[39m and \033[0;32mUDP: 443\033[39m for webserver"
	echo -e "\033[0;32mTCP: 21\033[39m and \033[0;32mTCP: 40110-40210\033[39m for FTP"
	echo -e "\033[0;32mTCP: 25\033[39m, \033[0;32mTCP: 587\033[39m, \033[0;32mTCP: 465\033[39m, \033[0;32mTCP: 110\033[39m, \033[0;32mTCP: 143\033[39m and \033[0;32mTCP: 993\033[39m for mail service"
	echo -e "\033[0;32mTCP: 53\033[39m and \033[0;32mUDP: 53\033[39m for DNS service"
if [[ $SERVER_COUNTRY = CN ]] ; then
	if [[ $PROVIDER == "Tencent Cloud" ]] ; then
		if [[ $SERVER_OS == "Ubuntu" ]] ; then
			rm -f /etc/apt/sources.list 
			mv /etc/apt/sources.list-backup /etc/apt/sources.list
echo > "nameserver 127.0.0.53
options edns0" /run/systemd/resolve/stub-resolv.conf
echo > "nameserver 127.0.0.53
options edns0" /etc/resolv.conf
			apt update
#revert the previous change on tencent cloud repo.
		fi
	fi
	if [[ $VERSION = "ENT" ]] ; then
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/install/installCyberPanel.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://cyberpanel.sh/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		sed -i 's|https://www.litespeedtech.com/packages/5.0/lsws-5.3.8-ent-x86_64-linux.tar.gz|https://'$DOWNLOAD_SERVER'/litespeed/lsws-'$LSWS_STABLE_VER'-ent-x86_64-linux.tar.gz|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
		echo -e "If you have install LiteSpeed Enterprise, please run \e[31m/usr/local/lsws/admin/misc/lsup.sh\033[39m to update it to latest."
	fi
fi

sed -i 's|lsws-5.3.8|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.4.2|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-5.3.5|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-6.0|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i 's|lsws-6.3.4|lsws-'$LSWS_STABLE_VER'|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py

if [[ $SILENT != "ON" ]] ; then
printf "%s" "Would you like to restart your server now? [y/N]: "
read TMP_YN

if [[ "$TMP_YN" = "N" ]] || [[ "$TMP_YN" = "n" ]] || [[ -z "$TMP_YN" ]]; then
:
else
reboot
exit
fi

exit
fi
#replace URL for CN



else
echo "something went wrong..."
exit
fi
}
