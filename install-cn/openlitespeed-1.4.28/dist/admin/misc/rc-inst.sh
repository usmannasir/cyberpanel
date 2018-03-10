#!/bin/sh
CURDIR=`dirname "$0"`
cd $CURDIR
CURDIR=`pwd`

INST_USER=`id`
INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`
if [ $INST_USER != "root" ]; then
	cat <<EOF
[ERROR] Only root user can install the rc script!
EOF
	exit 1
fi
INIT_DIR=""

if [ "x`uname -s`" = "xDarwin" ]; then

	STARTUP_ITEM=/System/Library/StartupItems/lsws
	if [ ! -d $STARTUP_ITEM ]; then
		mkdir $STARTUP_ITEM
	fi
	cp "$CURDIR/lsws.rc" $STARTUP_ITEM/lsws
	cat <<EOF >$STARTUP_ITEM/StartupParameters.plist
{
  Description     = "LiteSpeed web server";
  Provides        = ("Web Server");
  Requires        = ("DirectoryServices");
  Uses            = ("Disks", "NFS");
  OrderPreference = "None";
}

EOF


	exit 0
fi

if [ "x`uname -s`" = "xFreeBSD" ]; then
	if [ -d "/usr/local/etc/rc.d" ]; then
		
		cp "$CURDIR/lsws.rc" /usr/local/etc/rc.d/lsws.sh
		chmod 755 /usr/local/etc/rc.d/lsws.sh
		echo "[OK] The startup script has been successfully installed!"
		exit 0
	else
		cat <<EOF	
[ERROR] /usr/local/etc/rc.d/ does not exit in this FreeBSD system!

EOF
		exit 1
	fi
else
	if [ -f "/etc/gentoo-release" ]; then
		cp "$CURDIR/lsws.rc.gentoo" /etc/init.d/lsws
		chmod a+x /etc/init.d/lsws
		rc-update add lsws default
		exit 0
	fi

    grep "Debian" /etc/issue 2>/dev/null 1>&2
    if [ $? -eq 0  ]; then
        cp "$CURDIR/lsws.rc" /etc/init.d/lsws
        chmod a+x /etc/init.d/lsws
        update-rc.d lsws defaults
        exit 0
    fi
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

cp "$CURDIR/lsws.rc" $INIT_DIR/lsws
chmod 755 $INIT_DIR/lsws


if [ -d "$INIT_BASE_DIR/runlevel/default" ]; then
	ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/runlevel/default/S88lsws
	ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/runlevel/default/K12lsws
fi


if [ -d "$INIT_BASE_DIR/rc2.d" ]; then
	ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc2.d/S88lsws
	ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc2.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc3.d" ]; then
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc3.d/S88lsws
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc3.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc5.d" ]; then
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc5.d/S88lsws
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc5.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc0.d" ]; then
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc0.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc1.d" ]; then
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc1.d/K12lsws
fi

if [ -d "$INIT_BASE_DIR/rc6.d" ]; then
ln -fs $INIT_DIR/lsws $INIT_BASE_DIR/rc6.d/K12lsws
fi

echo "[OK] The startup script has been successfully installed!"

exit 0