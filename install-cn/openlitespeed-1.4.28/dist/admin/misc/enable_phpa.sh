

enablecache()
{
	CACHE=$1
	if [ ! -f $LSWSHOME/lib/$CACHE.so.$PHP_VER ]; then
		cd $LSWSHOME/lib
		wget "http://www.litespeedtech.com/packages/$CACHE/$CACHE-php-$PHP_VER-$DN.tar.gz"
		if [ $? -eq 0 ]; then
			gunzip -c "$CACHE-php-$PHP_VER-$DN.tar.gz" | tar xvf -
			rm $CACHE-php-$PHP_VER-$DN.tar.gz
            ln -sf $CACHE.so.$PHP_VER $LSWSHOME/lib/$CACHE.so
		else
			cat <<EOF 
[WARN] Can not retrieve binary package for $CACHE from www.litespeedtech.com, 
       please download it manually from 
           http://www.litespeedtech.com/download.html 
       or build binary from source code.
       Please make a symbolic link from $CACHE.so.$PHP_VER to
       $LSWSHOME/lib/$CACHE.so.

EOF
		fi
	else
        ln -sf $CACHE.so.$PHP_VER $LSWSHOME/lib/$CACHE.so
	fi
	
	cat <<EOF >>$LSWSHOME/php/php.ini

zend_extension="../lib/$CACHE.so"
$CACHE.shm_size="16"
$CACHE.cache_dir="/tmp/$CACHE"
$CACHE.enable="1"
$CACHE.optimizer="0"
$CACHE.check_mtime="1"
$CACHE.debug="0"
$CACHE.filter=""
$CACHE.shm_max="0"
$CACHE.shm_ttl="0"
$CACHE.shm_prune_period="0"
$CACHE.shm_only="0"
$CACHE.compress="1"

EOF

    ENABLE_CHROOT=0
	CHROOT_PATH=""
	if [ -f "$LSWSHOME/conf/httpd_config.xml" ]; then
		OLD_ENABLE_CHROOT_CONF=`grep "<enableChroot>" "$LSWSHOME/conf/httpd_config.xml"`
		OLD_CHROOT_PATH_CONF=`grep "<chrootPath>" "$LSWSHOME/conf/httpd_config.xml"`
		OLD_ENABLE_CHROOT=`expr "$OLD_ENABLE_CHROOT_CONF" : '.*<enableChroot>\(.*\)</enableChroot>.*'`
		OLD_CHROOT_PATH=`expr "$OLD_CHROOT_PATH_CONF" : '[^<]*<chrootPath>\([^<]*\)</chrootPath>.*'`
		if [ "x$OLD_ENABLE_CHROOT" != "x" ]; then
			ENABLE_CHROOT=$OLD_ENABLE_CHROOT
		fi
		if [ "x$OLD_CHROOT_PATH" != "x" ]; then
			CHROOT_PATH=$OLD_CHROOT_PATH
		fi
	fi

	if [ $ENABLE_CHROOT -eq 0 ]; then
		CHROOT_PATH=""
	fi

	if [ ! -d $CHROOT_PATH/tmp/$CACHE ]; then
		mkdir $CHROOT_PATH/tmp/$CACHE
	fi
	chmod 0777 $CHROOT_PATH/tmp/$CACHE
}




CURDIR=`dirname "$0"`
cd $CURDIR
CURDIR=`pwd`
LSWSHOME=`dirname $CURDIR`
LSWSHOME=`dirname $LSWSHOME`


PF=`uname -p`
OS=`uname -s`


if [ "x$OS" = "xFreeBSD" ]; then
	if [ "x$PF" = "xi386" ]; then
		DN="i386-freebsd"
	else
		echo "unkown platform '$PL' for FreeBSD."
		exit 1
	fi
elif [ "x$OS" = "xSunOS" ]; then
	if [ "x$PF" = "xsparc" ]; then
		DN="sparc-solaris"
	elif [ "x$PF" = "xi386" ]; then
		DN="i386-solaris"
	else
		echo "unkown platform '$PL' for Sun Solaris."
		exit 1
	fi
elif [ "x$OS" = "xLinux" ]; then
	PF=`uname -m`
	if [ "x$PF" = "xi686" ] || [ "x$PF" = "xi586" ] || [ "x$PF" = "xi486" ] || [ "x$PF" = "xi386" ]; then
		DN="i386-linux"
	elif [ "x$PF" = "xppc" ]; then
		DN="ppc-linux"
	elif [ "x$PF" = "xx86_64" ]; then
		DN="x86_64-linux"
		echo "Binary for 64 bits linux is not available, you need to build your own binary."
	else
		echo "unkown platform '$PL' for Linux."
		exit 1
	fi
elif [ "x$OS" = "xDarwin" ]; then
	if [ "x$PF" = "xpowerpc" ]; then
		DN="ppc-osx"
	else
		echo "unknwon platform '$PL' for Darwin/OSX."
	fi
else
	echo "unknwon Operating System '$OS'."
   
fi



SEL=1
SUCC=0

while [ $SUCC -eq "0" ]; do

	cat <<EOF

Please select from the following third party opcode cache for PHP

0. No Cache
1. Alternative PHP Cache (APC)
2. eAccelerator


EOF

	printf "%s" "Please select (0-2) [1]? "
	read TMPS
	echo ""
	if [ "x$TMPS" != "x" ]; then
		if [ `expr "$TMPS" : '[012]'` -gt 0 ]; then
			SEL=$TMPS
			SUCC=1
		fi
	else
		SUCC=1
	fi
done

if [ ! -w $LSWSHOME/php/php.ini ]; then
	echo "Access is denied to $LSWSHOME/php/php.ini"
	exit 1
fi

cp $LSWSHOME/php/php.ini $LSWSHOME/php/php.ini.bak
cp $LSWSHOME/php/php.ini $LSWSHOME/php/php.ini.old

sed -e "s/^.*extension.*apc\.so.*$//" -e "s/^.*zend_extension.*mmcache\.so.*$//" -e "s/^.*zend_extension.*eaccelerator\.so.*$//" -e "s/^.*mmcache\..*=.*$//" -e "s/^.*eaccelerator\..*=.*$//" "$LSWSHOME/php/php.ini.old" > "$LSWSHOME/php/php.ini"
if [ -f "$LSWSHOME/fcgi-bin/lsphp" ]; then
    VER_STR=`$LSWSHOME/fcgi-bin/lsphp -v`
elif [ -f "$LSWSHOME/fcgi-bin/php" ]; then
    VER_STR=`$LSWSHOME/fcgi-bin/php -v`
else
    echo "[ERROR] Cannot find PHP executable, not able to determine PHP version"
    exit 1
fi
PHP_VER=`expr "$VER_STR" : 'PHP \([^ ]*\) .*'`

if [ $SEL -eq 1 ]; then

	if [ ! -f $LSWSHOME/lib/apc.so.$PHP_VER ]; then
		echo "[ERROR] Can not find $LSWSHOME/lib/apc.so.$PHP_VER, please run install.sh again!"
		exit 1
	fi
    ln -sf apc.so.$PHP_VER $LSWSHOME/lib/apc.so
	cat <<EOF >>$LSWSHOME/php/php.ini
extension="../lib/apc.so"

EOF

elif [ $SEL -eq 2 ]; then
	enablecache eaccelerator

fi


rm $LSWSHOME/php/php.ini.old

