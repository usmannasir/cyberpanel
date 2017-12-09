#!/bin/sh

LSINSTALL_DIR=`dirname "$0"`
cd $LSINSTALL_DIR
LSINSTALL_DIR=`pwd`
BASE_DIR=`dirname $LSINSTALL_DIR`
BASE_DIR=`dirname $BASE_DIR`

cd /

INST_USER=`id`
INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`
if [ "x$INST_USER" != "xroot" ]; then
	DIR_OWN=`ls -ld $BASE_DIR | awk '{print $3}'`
	if [ "x$DIR_OWN" != "x$INST_USER" ]; then
		echo "[ERROR] You do not have the permission to uninstall LiteSpeed web server!"
		exit 1
	fi
fi

cat<<EOF
 
WARNING: 

All sub directories under "$BASE_DIR" 
created during installation will be removed! 
However, conf/ and logs/ can be optionally preserved. 
If you want to preserve any file under the other sub-directories created 
by installation script, please backup before proceeding.

Manually created sub-directories under "$BASE_DIR" 
will not be touched.

EOF
printf "Do you want to uninstall LiteSpeed Web Server? [y/N]"
read TMP_YN
echo ""
if [ "x$TMP_YN" != "xy" ] && [ "x$TMP_YN" != "xY" ]; then
	echo "Abort!"
	exit 0
fi

if [ "x`uname -s`" = "xFreeBSD" ]; then
	PS_CMD="ps -ax"
else
	PS_CMD="ps -ef"
fi

RUNNING_PROCESS=`$PS_CMD | grep lshttpd | grep -v grep`
if [ "x$RUNNING_PROCESS" != "x" ]; then
	cat <<EOF
LiteSpeed web server is running, it must be stopped in order to continue 
uninstallation.

EOF
	printf "Would you like to stop it now? [Y/n]"
	read TMP_YN
	echo ""
	if [ "x$TMP_YN" = "x" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
		$BASE_DIR/bin/lswsctrl stop
		echo ""
		RUNNING_PROCESS=`$PS_CMD | grep lshttpd | grep -v grep`
		if [ "x$RUNNING_PROCESS" != "x" ]; then
			echo "Failed to stop server, uninstallation abort!"
			exit 1
		fi
	else
		echo "Uninstallation abort!"
		exit 1
	fi
fi

if [ "x$INST_USER" = "xroot" ]; then
	echo "Uninstalling rc scripts ..."
	$LSINSTALL_DIR/rc-uninst.sh
	echo ""
fi
DELETE_ALL=1
printf "Do you want to keep server configuration files? [y/N]"
read TMP_YN
echo ""
if [ "x$TMP_YN" != "xy" ] && [ "x$TMP_YN" != "xY" ]; then
	rm -rf $BASE_DIR/conf
	rm -rf $BASE_DIR/admin/conf
	rm -rf $BASE_DIR/backup
else
	DELETE_ALL=0
fi

printf "Do you want to keep server log files? [y/N]"
read TMP_YN
echo ""
if [ "x$TMP_YN" != "xy" ] && [ "x$TMP_YN" != "xY" ]; then
	rm -rf $BASE_DIR/logs
	rm -rf $BASE_DIR/admin/logs
else
	DELETE_ALL=0
fi

rm -rf $BASE_DIR/docs
rm -rf $BASE_DIR/DEFAULT
rm -rf $BASE_DIR/bin
rm -rf $BASE_DIR/fcgi-bin
rm -rf $BASE_DIR/admin/cgid
rm -rf $BASE_DIR/admin/fcgi-bin
rm -rf $BASE_DIR/admin/html.open
rm -rf $BASE_DIR/admin/misc
rm -rf $BASE_DIR/admin/tmp
rm $BASE_DIR/admin/html
rm -rf $BASE_DIR/cachedata
rm -rf $BASE_DIR/gdata
rm -rf $BASE_DIR/lib
rm -rf $BASE_DIR/share
rm -rf $BASE_DIR/tmp
rm -rf $BASE_DIR/phpbuild
rm -rf $BASE_DIR/add-ons/snmp_monitoring


#Do not remove the modules here since the modules were created by user besides cache.so
rm $BASE_DIR/modules/cache.so



if [ $DELETE_ALL -ne 0 ]; then
	FILES=`ls $BASE_DIR | wc -l`
	if [ $FILES -eq 0 ]; then 
		rm -rf $BASE_DIR
	fi
fi

echo "LiteSpeed Web Server has been successfully uninstalled."



