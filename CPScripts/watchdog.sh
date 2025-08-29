#!/bin/bash

# Add any services to be watched by the watchdog
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

# Helper: return PIDs matching a pattern (one per line). Uses pgrep when available,
# falls back to ps+awk if not.
get_pids() {
	local pattern="$*"
	if command -v pgrep >/dev/null 2>&1; then
		pgrep -f -- "$pattern" 2>/dev/null || true
	else
		ps aux | awk -v pat="$pattern" 'index($0, pat) && $0 !~ /awk/ {print $2}' || true
	fi
}

# Helper: return matching process lines (like pgrep -a). Uses pgrep -a when available.
get_pids_with_cmdline() {
	local pattern="$*"
	if command -v pgrep >/dev/null 2>&1; then
		pgrep -a -f -- "$pattern" 2>/dev/null || true
	else
		ps aux | awk -v pat="$pattern" 'index($0, pat) && $0 !~ /awk/ {print $0}' || true
	fi
}

watchdog_check() {
for ((x=0; x<SERVICE_COUNT; x++)) ; do
	DISPLAY_NAME=${SERVICE_LIST[x*3]}
	SERVICE_NAME=${SERVICE_LIST[(x*3)+1]}
	IFS=';' read -ra SERVICE_ARGS <<< "${SERVICE_LIST[(x*3)+2]}"
	SERVICE_ARG=${SERVICE_ARGS[0]}
    
	echo -e "\nChecking ${DISPLAY_NAME}..."
	pid=$(get_pids "watchdog ${SERVICE_ARG}")
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for ${DISPLAY_NAME} is gone , restarting..."
		nohup watchdog "${SERVICE_ARG}" > /dev/null 2>&1 &
		echo -e "\nWatchDog for ${DISPLAY_NAME} has been started..."
	else
		echo -e "\nWatchDog for ${DISPLAY_NAME} is running...\n"
	get_pids_with_cmdline "watchdog ${SERVICE_ARG}" || true
	fi
done
}

check_service() {
	if systemctl status "$NAME" >/dev/null 2>&1; then
			if [[ $NAME == "mariadb" ]] ; then
				pid=$(get_pids "/usr/sbin/mysqld")
				if [[ $pid != "" ]] ; then
					printf '%s' '-1000' > /proc/"$pid"/oom_score_adj
				fi
			fi
			echo "$NAME service is running..."
		else
			echo "$NAME is down , try to restart it..."
			if [[ $NAME == "lsws" ]] ; then
				pkill lsphp
			fi
			if [[ $NAME == "mariadb" ]] ; then
				pid=$(get_pids "/usr/sbin/mysqld")
				if [[ $pid != "" ]] ; then
					printf '%s' '-1000' > /proc/"$pid"/oom_score_adj
				fi
			fi
			systemctl stop "$NAME"
			systemctl start "$NAME"
			if [ -f /etc/cyberpanel/watchdog.flag ] ; then
			flag="/etc/cyberpanel/watchdog.flag"
			LINE3=$(awk 'NR==3' $flag)
			LINE2=$(awk 'NR==2' $flag)
			LINE1=$(awk 'NR==1' $flag)

			FROM=${LINE3#*=}
			SENDER=${LINE2#*=}
			TO=${LINE1#*=}
			sendmail -F "$SENDER" -f "$FROM" -i "$TO" <<MAIL_END
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
		
			pid=$(get_pids "watchdog ${SERVICE_ARG}" )
			if [ -n "$pid" ] ; then
				# kill may accept multiple PIDs; loop to be safe
				while IFS= read -r _pid; do
					kill -15 "$_pid" || true
				done <<< "$pid"
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



while true
	do
		if [[ $NAME == "pdns" ]] ; then
			if [ -f /home/cyberpanel/powerdns ] ; then
				check_service
			fi
		elif [[ $NAME == "postfix" ]] ; then
			if  [ -f /home/cyberpanel/postfix ] ; then
				check_service
			fi
		elif [[ $NAME == "pure-ftpd" ]] || [[ $NAME == "pure-ftpd-mysql" ]] ; then
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
