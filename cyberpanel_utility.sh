#!/bin/bash
#CyberPanel utility script

export LC_CTYPE=en_US.UTF-8
SUDO_TEST=$(set)
BRANCH_NAME="stable"


set_watchdog() {
echo -e "\nPlease choose:"
echo -e "\n1. Install WatchDog."
echo -e "\n2. Start or Check WatchDog."
echo -e "\n3. Kill WatchDog."
echo -e "\n4. Back to Main Menu."
echo -e "\n"
printf "%s" "Please enter number [1-4]: "
read TMP_YN

if [[ $TMP_YN == "1" ]] ; then
	if [[ ! -f /etc/cyberpanel/watchdog.sh ]] ; then
		echo -e "\nWatchDog no found..."
		wget -O /etc/cyberpanel/watchdog.sh https://cyberpanel.sh/misc/watchdog.sh
		chmod +x /etc/cyberpanel/watchdog.sh
		ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
		echo -e "\nWatchDos has been installed..."
		set_watchdog
	else
		echo -e "\nWatchDos is already installed..."
		set_watchdog
	fi
elif [[ $TMP_YN == "2" ]] ; then
	if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
		watchdog status
		exit
	else
		echo -e "\nYou don't have WatchDog installed, please install it first..."
		set_watchdog
	fi
elif [[ $TMP_YN == "3" ]] ; then
	if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
		echo -e "\n"
		watchdog kill
		exit
	else
		echo -e "\nYou don't have WatchDog installed, please install it first..."
		set_watchdog
	fi
elif [[ $TMP_YN == "4" ]] ; then
	main_page
else
	echo -e "\nPlease enter correct number..."
	exit
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

self_check() {
echo -e "\nChecking Cyberpanel Utility update..."
SUM=$(md5sum /usr/bin/cyberpanel_utility)
SUM1=${SUM:0:32}
#get md5sum of local file

rm -f /tmp/cyberpanel_utility.sh
wget -q -O /tmp/cyberpanel_utility.sh https://cyberpanel.sh/misc/cyberpanel_utility.sh


SUM=$(md5sum /tmp/cyberpanel_utility.sh)
SUM2=${SUM:0:32}
#get md5sum of remote file.

if [[ $SUM1 == $SUM2 ]] ; then
	echo -e "\nCyberPanel Utility Script is up to date...\n"
else
	local_string=$(head -2 /usr/bin/cyberpanel_utility)
	remote_string=$(head -2 /tmp/cyberpanel_utility.sh)
	#check file content before replacing itself in case failed to download the file.
	if [[ $local_string == $remote_string ]] ; then
	echo -e "\nUpdating CyberPanel Utility Script..."
	rm -f /usr/bin/cyberpanel_utility
	mv /tmp/cyberpanel_utility.sh /usr/bin/cyberpanel_utility
	chmod 700 /usr/bin/cyberpanel_utility
	echo -e "\nCyberPanel Utility update compelted..."
	echo -e "\nPlease execute it again..."
	exit
	else
	echo -e "\nFailed to fetch server file..."
	echo -e "\nKeep using local script..."
	fi
fi

rm -f /tmp/cyberpanel_utility.sh

}

cyberpanel_upgrade() {
echo -e "CyberPanel upgrading..."
rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh -q https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh
chmod +x /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh
rm -f /usr/local/cyberpanel_upgrade.sh
exit
}

get_faq() {
echo -e "\nFetching information...\n"
curl https://cyberpanel.sh/misc/faq.txt
exit
}

addons() {
echo -e "place holder"
}

main_page() {
echo -e "		CyberPanel Utility Tools \e[31m(beta)\e[39m

  1. Upgrade CyberPanel.

  2. Addons.

  3. WatchDog \e[31m(beta)\e[39m

  4. Frequently Asked Question (FAQ)

  5. Exit.

  "
read -p "  Please enter the number[1-5]: " num
echo ""
case "$num" in
	1)
	cyberpanel_upgrade
	;;
	2)
	addons
	;;
	3)
	set_watchdog
	;;
	4)
	get_faq
	;;
	5)
	exit
	;;
	*)
	echo -e "  Please enter the right number [1-5]\n"
	exit
	;;
esac
}

panel_check(){
if [[ ! -f /etc/cyberpanel/machineIP ]] ; then
	echo -e "\nCan not detect CyberPanel..."
	echo -e "\nExit..."
	exit
fi
}

sudo_check() {
	echo -e "\nChecking root privileges..."
	if echo $SUDO_TEST | grep SUDO > /dev/null ; then
		echo -e "\nYou are using SUDO , please run as root user..."
		echo -e "If you don't have direct access to root user, please run \e[31msudo su -\e[39m command and then run installation command again."
		exit
	fi

	if [[ $(id -u) != 0 ]]  > /dev/null; then
		echo -e "\nYou must use root user to use CyberPanel Utility..."
		exit
	else
		echo -e "\nYou are runing as root..."
	fi
}

show_help() {
echo -e "\nCyberPanel Utility Script"
echo -e "\nYou can use argument --upgrade to run CyberPanel upgrade without interaction for automated job."
echo -e "\nExample: cyberpanel utility --upgrade"
exit
}

panel_check

sudo_check

self_check


if [ $# -eq 0 ] ; then
main_page
else
	if [[ $1 == "upgrade" ]] || [[ $1 == "-u" ]] || [[ $1 == "--update" ]] || [[ $1 == "--upgrade" ]] || [[ $1 == "update" ]]; then
		cyberpanel_upgrade
	fi
	if [[ $1 == "help" ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] ; then
		show_help
		exit
	fi
echo -e "\nUnrecognized argument..."
exit
fi
