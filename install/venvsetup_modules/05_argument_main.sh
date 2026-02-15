#!/usr/bin/env bash
# install/venvsetup part 5 – argument_mode and main flow

argument_mode() {
KEY_SIZE=${#VERSION}
TMP=$(echo $VERSION | cut -c5)
TMP2=$(echo $VERSION | cut -c10)
TMP3=$(echo $VERSION | cut -c15)
if [[ $VERSION == "OLS" || $VERSION == "ols" ]] ; then
	VERSION="OLS"
	echo -e "\nSet to OpenLiteSpeed..."
elif [[ $VERSION == "Trial" ]] || [[ $VERSION == "TRIAL" ]] || [[ $VERSION == "trial" ]] ; then
	VERSION="ENT"
	LICENSE_KEY="TRIAL"
	echo -e "\nLiteSpeed Enterprise trial license set..."
elif [[ $TMP == "-" ]] && [[ $TMP2 == "-" ]] && [[ $TMP3 == "-" ]] && [[ $KEY_SIZE == "19" ]] ; then
	LICENSE_KEY=$VERSION
	VERSION="ENT"
	echo -e "\nLiteSpeed Enterprise license key set..."
else
	echo -e "\nCan not recognize the input value \e[31m$VERSION\e[39m "
	echo -e "\nPlease verify the input value..."
	echo -e "\nPlease run with \e[31m-h\e[39m or \e[31m--help\e[39m for more detail."
	exit
fi

if [[ $ADMIN_PASS == "d" ]] ; then
	ADMIN_PASS="1234567"
	echo -e "\nSet to default password..."
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
elif [[ $ADMIN_PASS == "r" ]] ; then
	ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
	echo -e "\nSet to random-generated password..."
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
	echo $ADMIN_PASS
else
	echo -e "\nAdmin password will be set to \e[31m$ADMIN_PASS\e[39m"
fi
}

if [ $# -eq 0 ] ; then
	echo -e "\nInitializing...\n"
else
	if [[ $1 == "help" ]] ; then
	show_help
	exit
	elif [[ $1 == "dev" ]] ; then
		DEV="ON"
		DEV_ARG="ON"
		SILENT="OFF"
	elif [[ $1 == "default" ]] ; then
	echo -e "\nThis will start default installation...\n"
	SILENT="ON"
	POSTFIX_VARIABLE="ON"
	POWERDNS_VARIABLE="ON"
	PUREFTPD_VARIABLE="ON"
	VERSION="OLS"
	ADMIN_PASS="1234567"
	MEMCACHED="ON"
	REDIS="ON"
	else
		while [ ! -z "${1}" ]; do
			case $1 in
				-v | --version) shift
						if [ "${1}" = '' ]; then
							show_help
							exit
						else
							VERSION="${1}"
							SILENT="ON"
						fi
						;;
				-p | --password) shift
						if [[ "${1}" == '' ]]; then
							ADMIN_PASS="1234567"
						elif [[ "${1}" == 'r' ]] || [[ $1 == 'random' ]] ; then
							ADMIN_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16 ; echo '')
						else
							if [ ${1} -lt 8 ] ; then
								echo -e "\nPassword lenth less than 8 digital, please choose a more complicated password.\n"
								exit
							fi
							ADMIN_PASS="${1}"
						fi
        		;;
				-a | --addons)
						MEMCACHED="ON"
						REDIS="ON"
        		;;
				-m | --minimal)
						echo "minimal installation is still work in progress..."
						exit
        		;;
				-h | --help)
						show_help
						exit
        		;;
				*)
						echo "unknown argument..."
						show_help
						exit
        		;;
			esac
			shift
			done
			fi
fi



SERVER_IP=$(curl --silent --max-time 10 -4 https://cyberpanel.sh/?ip)
if [[ $SERVER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo -e "Valid IP detected..."
else
	echo -e "Can not detect IP, exit..."
	exit
fi
SERVER_COUNTRY="unknow"
SERVER_COUNTRY=$(curl --silent --max-time 5 https://cyberpanel.sh/?country)
if [[ ${#SERVER_COUNTRY} == "2" ]] || [[ ${#SERVER_COUNTRY} == "6" ]] ; then
	echo -e "\nChecking server..."
	else
	echo -e "\nChecking server..."
	SERVER_COUNTRY="unknow"
fi
#SERVER_COUNTRY="CN"
#test string
if [[ $SERVER_COUNTRY == "CN" ]] ; then
DOWNLOAD_SERVER="cyberpanel.sh"
else
DOWNLOAD_SERVER="cdn.cyberpanel.sh"
fi

check_OS
check_root
check_panel
check_process
check_provider





if [[ $SILENT = "ON" ]] ; then
argument_mode
else
interactive_mode
fi

SECONDS=0
install_required

pip_virtualenv

system_tweak

