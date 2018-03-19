#!/bin/sh
CURDIR=`dirname "$0"`
cd $CURDIR
CURDIR=`pwd`

INST_USER=`id`
INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`
if [ $INST_USER != "root" ]; then
	cat <<EOF
[ERROR] Only root user can uninstall the rc script!
EOF
	exit 1
fi
INIT_DIR=""

if [ "x`uname -s`" = "xFreeBSD" ]; then
	if [ -d "/usr/local/etc/rc.d" ]; then
		
		rm -f /usr/local/etc/rc.d/lsws.sh
		echo "[OK] The startup script has been successfully uninstalled!"
		exit 0
	fi
fi 

if [ -f "/etc/gentoo-release" ]; then
	rc-update del lsws default
	rm /etc/init.d/lsws
	exit 0
fi



for path in /etc/init.d /etc/rc.d/init.d 
do
	if [ "x$INIT_DIR" = "x" ]; then
		if [ -d "$path" ]; then
			INIT_DIR=$path
		fi
	fi
done
if [ "x$INIT_DIR" = "x" ]; then
	echo "[ERROR] failed to find the init.d directory!"
	exit 1
fi

if [ -f "$INIT_DIR/lsws" ]; then
	rm -f $INIT_DIR/lsws
fi

if [ -d "$INIT_DIR/rc2.d" ]; then
    INIT_BASE_DIR=$INIT_DIR
else
    INIT_BASE_DIR=`dirname $INIT_DIR`
fi


if [ -d "$INIT_BASE_DIR/runlevel/default" ]; then
	rm -f $INIT_BASE_DIR/runlevel/default/S88lsws
	rm -f $INIT_BASE_DIR/runlevel/default/K12lsws
fi


if [ -d "$INIT_BASE_DIR/rc2.d" ]; then
	rm -f $INIT_BASE_DIR/rc2.d/S88lsws
	rm -f $INIT_BASE_DIR/rc2.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc3.d" ]; then
	rm -f $INIT_BASE_DIR/rc3.d/S88lsws
	rm -f $INIT_BASE_DIR/rc3.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc5.d" ]; then
	rm -f $INIT_BASE_DIR/rc5.d/S88lsws
	rm -f $INIT_BASE_DIR/rc5.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc0.d" ]; then
	rm -f $INIT_BASE_DIR/rc0.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc1.d" ]; then
	rm -f $INIT_BASE_DIR/rc1.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc6.d" ]; then
	rm -f $INIT_BASE_DIR/rc6.d/K12lsws
fi

echo "[OK] The startup script has been successfully uninstalled!"


