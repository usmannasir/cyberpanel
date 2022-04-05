#!/bin/bash

# Add any services to be watched by the watchdog to the SERVICE_LIST
# Format of the service list: "Display Name" "Service Name" "semicolon delimited list of watchdog arguments"
SERVICE_LIST=(
	"LiteSpeed" "lsws" "lsws;web;litespeed;openlitespeed"
	"MariaDB" "mariadb" "mariadb;database;mysql"
	"PowerDNS" "pdns" "powerdns;dns"
	"Dovecot" "dovecot" "dovecot;imap;pop3"
	"PostFix" "postfix" "postfix;smtp"
	"Pure-FTPd" "pure-ftpd" "pureftpd;pure-ftpd;ftp"
)

SERVICE_COUNT=$((${#SERVICE_LIST[@]}/3))

show_help() {
	echo -e "\nrun command: \e[31mnohup bash /etc/cyberpanel/watchdog.sh SERVICE_NAME >/dev/null 2>&1 &\e[39m"
	echo -e "\nreplace \e[31mSERVICE_NAME\e[39m to the service name, acceptable word:"

	for ((x=0; x<SERVICE_COUNT; x++)) ; do
		IFS=';' read -ra SERVICE_ARGS <<< "${SERVICE_LIST[(x*3)+2]}"
		echo -e "  \e[31m${SERVICE_ARGS[0]}\e[39m"
	done

	echo -e "\nWatchdog will check service status every 60 seconds and tries to restart if it is not running and also send an email to designated address"
	echo -e "\nto exit watchdog , run command \e[31mbash /etc/cyberpanel/watchdog.sh kill\e[39m"
	echo -e "\n\nplease also create \e[31m/etc/cyberpanel/watchdog.flag\e[39m file with following format:"
	echo -e "TO=address@email.com"
	echo -e "SENDER=sender name"
	echo -e "FROM=sender@email.com"
	echo -e "You may proceed without flag file , but that will make email sending failed."
}

watchdog_check() {
for ((x=0; x<SERVICE_COUNT; x++)) ; do
	DISPLAY_NAME=${SERVICE_LIST[x*3]}
	SERVICE_NAME=${SERVICE_LIST[(x*3)+1]}
	IFS=';' read -ra SERVICE_ARGS <<< "${SERVICE_LIST[(x*3)+2]}"
	SERVICE_ARG=${SERVICE_ARGS[0]}
	
	echo -e "\nChecking ${DISPLAY_NAME}..."
	pid=$(ps aux | grep "watchdog ${SERVICE_ARG}" | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for ${DISPLAY_NAME} is gone , restarting..."
		nohup watchdog ${SERVICE_ARG} > /dev/null 2>&1 &
		echo -e "\nWatchDog for ${DISPLAY_NAME} has been started..."
	else
		echo -e "\nWatchDog for ${DISPLAY_NAME} is running...\n"
		echo $(ps aux | grep "watchdog ${SERVICE_ARG}" | grep -v grep)
	fi
done
}

check_service() {
	systemctl status $NAME 2>&1>/dev/null
		if [[ $? == "0" ]] ; then
			if [[ $NAME == "mariadb" ]] ; then
				pid=$(ps aux | grep "/usr/sbin/mysqld"  | grep -v grep | awk '{print $2}')
					if [[ $pid != "" ]] ; then
						echo "-1000" > /proc/$pid/oom_score_adj
					fi 
				pid=$(ps aux | grep "/usr/sbin/mysqld"  | grep -v grep | awk '{print $2}')
					if [[ $pid != "" ]] ; then
						echo "-1000" > /proc/$pid/oom_score_adj
					fi
			fi
			echo "$NAME service is running..."
		else
			echo "$NAME is down , try to restart it..."
			if [[ $NAME == "lsws" ]] ; then
				pkill lsphp
			fi
			if [[ $NAME == "mariadb" ]] ; then
				pid=$(ps aux | grep "/usr/sbin/mysqld"  | grep -v grep | awk '{print $2}')
					if [[ $pid != "" ]] ; then
						echo "-1000" > /proc/$pid/oom_score_adj
					fi 
				pid=$(ps aux | grep "/usr/sbin/mysqld"  | grep -v grep | awk '{print $2}')
					if [[ $pid != "" ]] ; then
						echo "-1000" > /proc/$pid/oom_score_adj
					fi
			fi
			systemctl stop $NAME
			systemctl start $NAME
			if [ -f /etc/cyberpanel/watchdog.flag ] ; then
			flag="/etc/cyberpanel/watchdog.flag"
			LINE3=$(awk 'NR==3' $flag)
			LINE2=$(awk 'NR==2' $flag)
			LINE1=$(awk 'NR==1' $flag)

			FROM=${LINE3#*=}
			SENDER=${LINE2#*=}
			TO=${LINE1#*=}
			sendmail -F $SENDER -f $FROM -i $TO <<MAIL_END
Subject: $NAME is down...
To: $TO
$NAME is down , watchdog attempted to restarting it...

MAIL_END
			fi
		fi
}


if [[ $1 == "help" ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] || [[ $1 == "" ]] ; then
	show_help
	exit
elif [[ $1 == "check" ]] || [[ $1 == "status" ]] ; then
	watchdog_check
	exit
elif [[ $1 == "kill" ]] ; then
	for ((x=0; x<SERVICE_COUNT; x++)); do
		IFS=';' read -ra SERVICE_ARGS <<< "${SERVICE_LIST[(x*3)+2]}"
		SERVICE_ARG=${SERVICE_ARGS[0]}
		
		pid=$(ps aux | grep "watchdog ${SERVICE_ARG}" | grep -v grep | awk '{print $2}')
		if [[ "$pid" != "" ]] ; then
			kill -15 $pid
		fi
	done
	echo "watchdog has been killed..."
	exit
fi

# Check if $1 matches any service argument names
SERVICE_FOUND=0
for ((x=0; x<SERVICE_COUNT; x++)) ; do
	DISPLAY_NAME=${SERVICE_LIST[x*3]}
	SERVICE_NAME=${SERVICE_LIST[(x*3)+1]}
	IFS=';' read -ra SERVICE_ARGS <<< "${SERVICE_LIST[(x*3)+2]}"
	SERVICE_ARG=${SERVICE_ARGS[0]}

	for arg in "${SERVICE_ARGS[@]}" ; do
		if [[ $1 == "$arg" ]] ; then
			SERVICE_FOUND=1
			NAME=$SERVICE_NAME
			echo "Watchdog on ${DISPLAY_NAME} is starting up ..."
		fi
	done
done

if [[ $SERVICE_FOUND == 0 ]] ; then
	echo -e "unknown service name \e[31m$1\e[39m..."

	show_help
	exit
fi



while [ true = true ]
	do
		if [[ $NAME == "pdns" ]] ; then
			if [ -f /home/cyberpanel/powerdns ] ; then
				check_service
			fi
		elif [[ $NAME == "postfix" ]] ; then
			if  [ -f /home/cyberpanel/postfix ] ; then
				check_service
			fi
		elif [[ $name == "pure-ftpd" ]] || [[ $name == "pure-ftpd-mysql" ]] ; then
			if [ -f /home/cyberpanel/pureftpd ] ; then
				if [ -f /etc/lsb-release ] ; then
					NAME="pure-ftpd-mysql"
				else
					NAME="pure-ftpd"
				fi

				check_service
			fi
		else
			check_service
		fi
	sleep 60
done
