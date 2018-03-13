
# resolve links - $0 may be a softlink
PROG="$0"
PIDFILE=/tmp/lshttpd/lshttpd.pid

EXECUTABLE=lshttpd
BASE_DIR=`dirname "$PROG"`
if [ ! -x "$BASE_DIR"/"$EXECUTABLE" ]; then
	echo "[ERROR] Cannot find $BASE_DIR/$EXECUTABLE"
	exit 1
fi

if [ -f $PIDFILE ] ; then
	PID=`cat $PIDFILE`
	if [ "x$PID" != "x" ] && kill -0 $PID 2>/dev/null ; then
		STATUS="web server is running with pid=$PID."
		RUNNING=1
	else
		STATUS="web server is not running"
		RUNNING=0
	fi
else
	STATUS="[ERROR] web server is not running, can't find pid file."
	RUNNING=0
fi

start() {
	echo "start server"
}

stop() {
	echo "stop server" 
}

reload() {
	if kill -HUP $PID ; then
		echo "web server reloads configuration"
	else
		echo "can't send SIGHUP to web server"
	fi
}

help() {
	echo $"Usage: $PROG {start|stop|restart|reload|help}"
	cat <<EOF

start    - start web server
stop     - stop web server
restart  - restart (stop then start) web server
reload   - reload the configuration by sending SIGHUP to web server
help     - this screen
		
EOF
}

case "$1" in 
	start)
		if [ $RUNNING -eq 1 ]; then
			echo "$STATUS"
		else
			start
		fi
		;;
	stop)
		if [ $RUNNING -eq 1 ]; then
			stop
		else
			echo "$STATUS"
		fi
		;;
	restart)
		if [ $RUNNING -eq 1 ]; then
			stop
		fi
		start
		;;
	reload)
		if [ $RUNNING -eq 1 ]; then
			reload
		else
			echo "$STATUS"
		fi
		;;
	*)
		help
		exit 2
		;;
esac

