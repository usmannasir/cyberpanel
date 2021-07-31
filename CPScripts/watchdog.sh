#!/bin/bash

show_help() {
echo -e "\nrun command: \e[31mnohup bash /etc/cyberpanel/watchdog.sh SERVICE_NAME >/dev/null 2>&1 &\e[39m"
echo -e "\nreplace \e[31mSERVICE_NAME\e[39m to the service name, acceptable word: \e[31mmariadb\e[39m, \e[31mlsws\e[39m, \e[31mpowerdns\e[39m, \e[31mdovecot\e[39m, \e[31mpostfix\e[39m, or \e[31mpureftpd\e[39m"
echo -e "\nWatchdog will check service status every 60 seconds and tries to restart if it is not running and also send an email to designated address"
echo -e "\nto exit watchdog , run command \e[31mbash /etc/cyberpanel/watchdog.sh kill\e[39m"
echo -e "\n\nplease also create \e[31m/etc/cyberpanel/watchdog.flag\e[39m file with following format:"
echo -e "TO=address@email.com"
echo -e "SENDER=sender name"
echo -e "FROM=sender@email.com"
echo -e "You may proceed without flag file , but that will make email sending failed."
}

watchdog_check() {
echo -e "\nChecking LiteSpeed ..."
pid=$(ps aux | grep "watchdog lsws"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for LSWS is gone , restarting..."
		nohup watchdog lsws > /dev/null 2>&1 &
		echo -e "\nWatchDog for LSWS has been started..."
	else
		echo -e "\nWatchDog for LSWS is running...\n"
		echo $(ps aux | grep "watchdog lsws"  | grep -v grep)
	fi

echo -e "\nChecking MariaDB ..."
pid=$(ps aux | grep "watchdog mariadb"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for MariaDB is gone , restarting..."
		nohup watchdog mariadb > /dev/null 2>&1 &
		echo -e "\nWatchDog for MariaDB has been started..."
	else
		echo -e "\nWatchDog for MariaDB is running...\n"
		echo $(ps aux | grep "watchdog mariadb"  | grep -v grep)
	fi

echo -e "\nChecking PowerDNS ..."
pid=$(ps aux | grep "watchdog powerdns"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for PowerDNS is gone , restarting..."
		nohup watchdog powerdns > /dev/null 2>&1 &
		echo -e "\nWatchDog for PowerDNS has been started..."
	else
		echo -e "\nWatchDog for PowerDNS is running...\n"
		echo $(ps aux | grep "watchdog powerdns"  | grep -v grep)
	fi

echo -e "\nChecking Dovecot ..."
pid=$(ps aux | grep "watchdog dovecot"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for Dovecot is gone , restarting..."
		nohup watchdog dovecot > /dev/null 2>&1 &
		echo -e "\nWatchDog for Dovecot has been started..."
	else
		echo -e "\nWatchDog for Dovecot is running...\n"
		echo $(ps aux | grep "watchdog dovecot"  | grep -v grep)
	fi

echo -e "\nChecking Postfix ..."
pid=$(ps aux | grep "watchdog postfix"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for Postfix is gone , restarting..."
		nohup watchdog postfix > /dev/null 2>&1 &
		echo -e "\nWatchDog for Postfix has been started..."
	else
		echo -e "\nWatchDog for Postfix is running...\n"
		echo $(ps aux | grep "watchdog postfix"  | grep -v grep)
	fi

echo -e "\nChecking Pure-FTPd ..."
pid=$(ps aux | grep "watchdog pureftpd"  | grep -v grep | awk '{print $2}')
	if [[ "$pid" == "" ]] ; then
		echo -e "\nWatchDog for Pure-FTPd is gone , restarting..."
		nohup watchdog pureftpd > /dev/null 2>&1 &
		echo -e "\nWatchDog for Pure-FTPd has been started..."
	else
		echo -e "\nWatchDog for Pure-FTPd is running...\n"
		echo $(ps aux | grep "watchdog pureftpd"  | grep -v grep)
	fi
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

if [[ $1 == "mariadb" ]] || [[ $1 == "database" ]] || [[ $1 == "mysql" ]] ; then
	NAME="mariadb"
	echo "Watchdog on MariaDB is started up ..."
elif [[ $1 == "web" ]] || [[ $1 == "lsws" ]] || [[ $1 == "litespeed" ]] || [[ $1 == "openlitespeed" ]] ; then
	NAME="lsws"
	echo "Watchdog on LiteSpeed is started up ..."
elif [[ $1 == "powerdns" ]] || [[ $1 == "dns" ]] ; then
	NAME="powerdns"
	echo "Watchdog on PowerDNS is starting up ..."
elif [[ $1 == "dovecot" ]] || [[ $1 == "imap" ]] || [[ $1 == "pop3" ]]; then
	NAME="dovecot"
	echo "Watchdog on Dovecot is starting up ..."
elif [[ $1 == "postfix" ]] || [[ $1 == "smtp" ]] ; then
	NAME="postfix"
	echo "Watchdog on PostFix is starting up ..."
elif [[ $1 == "pureftpd" ]] || [[ $1 == "ftp" ]] || [[ $1 == "pure-ftpd" ]]; then
	NAME="pure-ftpd"
	echo "Watchdog on Pure-FTPd is starting up ..."
elif [[ $1 == "help" ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] || [[ $1 == "" ]] ; then
	show_help
exit
elif [[ $1 == "check" ]] || [[ $1 == "status" ]] ; then
	watchdog_check
	exit
elif [[ $1 == "kill" ]] ; then
pid=$(ps aux | grep "watchdog lsws"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
pid=$(ps aux | grep "watchdog mariadb"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
pid=$(ps aux | grep "watchdog powerdns"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
pid=$(ps aux | grep "watchdog dovecot"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
pid=$(ps aux | grep "watchdog postfix"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
pid=$(ps aux | grep "watchdog pureftpd"  | grep -v grep | awk '{print $2}')
if [[ "$pid" != "" ]] ; then
kill -15 $pid
fi
echo "watchdog has been killed..."
exit
else
show_help

echo -e "\n\n\nunknown service name..."
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
