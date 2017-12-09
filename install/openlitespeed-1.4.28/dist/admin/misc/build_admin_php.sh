#!/bin/sh

#########################
# You can modify the variables defined
#########################

LSINSTALL_DIR=`dirname "$0"`
cd $LSINSTALL_DIR
LSINSTALL_DIR=`pwd`
BASE_DIR=`dirname $LSINSTALL_DIR`
LSWS_HOME=`dirname $BASE_DIR`

PATH=$PATH
PHP_VERSION=5.6.18
PHP_BUILD_DIR=$LSWS_HOME/phpbuild
mkdir ${PHP_BUILD_DIR}
LOG_FILE=${PHP_BUILD_DIR}/adminphp.log

# detect download method
OS=`uname -s`
DL_METHOD="wget -nv -O"
if [ "x$OS" = "xFreeBSD" ] ; then
    DL=`which fetch`
    DL_METHOD="$DL -o"
else
    # test wget exist or not
    DL=`which wget`
    if [ "$?" -ne "0" ] ; then
        DL=`which curl`
        DL_METHOD="$DL -L -o"
        if [ "$?" -ne "0" ] ; then
            echo "Error: Cannot find proper download method curl/wget."
        fi
    fi
fi

LSAPI_VERSION=6.6
PHP_CONF_OPTIONS="--prefix=/tmp --disable-all --with-litespeed --enable-session --enable-posix --enable-xml --with-libexpat-dir=/usr --with-zlib --enable-sockets --enable-bcmath --enable-json"

PLF=`uname -p`
if [ "x$PLF" = "xx86_64" ] ; then
    PHP_CONF_OPTIONS="${PHP_CONF_OPTIONS} --with-libdir=lib64"
fi

check_errs()
{
  if [ "${1}" -ne "0" ] ; then
    echo "**ERROR** ${2}"
    echo "**ERROR** ${2}" >> ${LOG_FILE}
    exit ${1}
  fi
}

main_msg()
{
	# write to both stdout and progress
	echo "${1}"
	echo "${1}" >> ${LOG_FILE}
}

cat /dev/null ${LOG_FILE}

echo "============================================================="
main_msg "Preparing all source code for building admin_php with PHP ${PHP_VERSION} and LSAPI ${LSAPI_VERSION}"
main_msg "admin_php is solely used for WebAdmin console, should not be used for other purpose. Only minimum set of PHP modules included here."
echo "============================================================="

echo `date`
echo ""

echo "Changing to build directory ${PHP_BUILD_DIR}" 
cd ${PHP_BUILD_DIR}
check_errs $? "Could not get into build directory"

if [ -e "php-${PHP_VERSION}" ] ; then
	rm -rf php-${PHP_VERSION}
	check_errs $? "Could not delete old php directory ${PHP_BUILD_DIR}/php-${PHP_VERSION}"
fi

test_phpsrc_ok()
{
	main_msg "Extracting PHP source archive: tar -zxf ${1}" 
	tar -zxf ${1}
	if [ "$?" -ne "0" ] ; then
		## remove bad copy
		rm -f ${1}
		main_msg "Could not extract PHP source archive"
		return 1
	fi
	return 0
}


PHP_SRC=php-${PHP_VERSION}.tar.gz
PHP_SRC_READY=N

if [ -e "${PHP_SRC}" ] ; then
	main_msg "${PHP_SRC} already downloaded, use the saved copy."
	test_phpsrc_ok ${PHP_SRC}
	if [ "$?" -eq "0" ] ; then
		PHP_SRC_READY=Y
	fi
fi

if [ ${PHP_SRC_READY} = "N" ] ; then
	DOWNLOAD_URL="http://us1.php.net/distributions/${PHP_SRC}"
	main_msg "Retrieving PHP source archive from ${DOWNLOAD_URL}" 
	${DL_METHOD} ${PHP_SRC} ${DOWNLOAD_URL}

	test_phpsrc_ok ${PHP_SRC}
	if [ "$?" -eq "0" ] ; then
		PHP_SRC_READY=Y
	fi
fi

if [ ${PHP_SRC_READY} = "N" ] ; then
    DOWNLOAD_URL="http://us2.php.net/distributions/${PHP_SRC}"
    main_msg "Try again, retrieving PHP source archive from ${DOWNLOAD_URL}" 
    ${DL_METHOD} ${PHP_SRC} ${DOWNLOAD_URL}

    test_phpsrc_ok ${PHP_SRC}
    if [ "$?" -eq "0" ] ; then
        PHP_SRC_READY=Y
    fi
fi

if [ ${PHP_SRC_READY} = "N" ] ; then
	MAIN_VER=`expr '${PHP_VERSION}' : "\(.\)"`
	DOWNLOAD_URL="http://museum.php.net/php${MAIN_VER}/${PHP_SRC}"
	main_msg "Try again, retrieving PHP source archive from ${DOWNLOAD_URL}" 
	${DL_METHOD} ${PHP_SRC} ${DOWNLOAD_URL}

	test_phpsrc_ok ${PHP_SRC}
	if [ "$?" -eq "0" ] ; then
		PHP_SRC_READY=Y
	fi
fi

if [ ${PHP_SRC_READY} = "N" ] ; then
	check_errs $? "Fail to retrieve PHP source archive. Please try manually download."
fi
	
echo ""

# get LSAPI

if [ -e php-litespeed-${LSAPI_VERSION}.tgz ] ; then
	rm -f php-litespeed-${LSAPI_VERSION}.tgz
	check_errs $? "Could not delete old lsapi copy php-litespeed-${LSAPI_VERSION}.tgz"
fi

DOWNLOAD_URL="http://www.litespeedtech.com/packages/lsapi/php-litespeed-${LSAPI_VERSION}.tgz"
main_msg "Retrieving LSAPI from ${DOWNLOAD_URL}"
${DL_METHOD} "php-litespeed-${LSAPI_VERSION}.tgz" ${DOWNLOAD_URL}
check_errs $? "Could not retrieve LSAPI archive"

cd php-${PHP_VERSION}/sapi
check_errs $? "Could not get into php/sapi directory"

if [ -e litespeed/Makefile.frag ] ; then
	mv -f litespeed/Makefile.frag litespeed/Makefile.frag.package 
fi


main_msg "Extracting LSAPI archive: tar -xzf php-litespeed-${LSAPI_VERSION}.tgz" 
tar -xzf "../../php-litespeed-${LSAPI_VERSION}.tgz"
check_errs $? "Could not extract LSAPI archive"

if [ -e litespeed/Makefile.frag.package ] ; then
	mv -f litespeed/Makefile.frag.package litespeed/Makefile.frag 
fi

echo ""
echo "============================================================="
main_msg "Finished gathering all source code for building admin_php"
echo "============================================================="
echo `date`
echo ""
main_msg "**PREPARE_DONE**"
echo ""
echo ""

echo "=============================================="
main_msg "Start building admin_php"
echo "=============================================="



echo "Changing to build directory ${PHP_BUILD_DIR}/php-${PHP_VERSION}" 
cd ${PHP_BUILD_DIR}/php-${PHP_VERSION}
check_errs $? "Could not get into build directory"

touch ac*
check_errs $? "Could not touch ac*"

rm -rf autom4te.*

PHP_MAIN_VER=`expr "${PHP_VERSION}" : '\([0-9]*\.[0-9]*\)'`

PHP_MAIN_VER1=`expr "${PHP_MAIN_VER}" : '\([0-9]*\)\.'`
PHP_MAIN_VER2=`expr "${PHP_MAIN_VER}" : '[0-9]*\.\([0-9]*\)'`

BUILDCONF_FORCE=N
if [ "${PHP_MAIN_VER1}" -lt "5" ] ; then
    BUILDCONF_FORCE=Y
elif [ "${PHP_MAIN_VER1}" = "5" ] && [ "${PHP_MAIN_VER2}" -lt "3" ] ; then
    BUILDCONF_FORCE=Y
fi

if [ ${BUILDCONF_FORCE} = "Y" ] ; then
	./buildconf --force
	check_errs $? "Could not generate configuration script for version prior to 5.3"
fi


main_msg "Configuring PHP build (2-3 minutes)" 
echo "./configure ${PHP_CONF_OPTIONS}"
./configure ${PHP_CONF_OPTIONS}

check_errs $? "Could not configure PHP build"

if [ "x$PLF" = "xx86_64" ] ; then
        # work around for libtool problem for linux
        DLSCH=`grep 'sys_lib_dlsearch_path_spec="/lib /usr/lib ' libtool`
        if [ "x$DLSCH" != "x" ] ; then
                echo "  .. work around for libtool problem: sys_lib_dlsearch_path_spec should use lib64"
                cp libtool libtool.orig
                sed -e 's/sys_lib_dlsearch_path_spec=\"\/lib \/usr\/lib /sys_lib_dlsearch_path_spec=\"\/lib64 \/usr\/lib64 /' libtool.orig > libtool
            if [ "$?" -ne "0" ] ; then
                        echo "   sed command error, please try to modify libtool manually using lib64 for line: sys_lib_dlsearch_path_spec=\"/lib /usr/lib\" "
            fi
        fi
fi


find . -name '*.1' > /tmp/php-1.lst.$$
tar -cf /tmp/php-1.tar.$$ -T /tmp/php-1.lst.$$
make clean
tar -xf /tmp/php-1.tar.$$
rm /tmp/php-1.tar.$$ /tmp/php-1.lst.$$


main_msg "Compiling PHP (5-10 minutes)" 
echo `date`
make
check_errs $? "Could not compile PHP"

main_msg "copy compiled php binary to litespeed directory"

echo "cd $LSWS_HOME/admin/fcgi-bin"
cd $LSWS_HOME/admin/fcgi-bin
check_errs $? "cannot cd to $LSWS_HOME/admin/fcgi-bin"

if [ -e "lsphp-${PHP_VERSION}" ] ; then
	mv admin_php-${PHP_VERSION} admin_php-${PHP_VERSION}.bak
fi

cp ${PHP_BUILD_DIR}/php-${PHP_VERSION}/sapi/litespeed/php admin_php-${PHP_VERSION}
check_errs $? "fail to copy admin_php from ${PHP_BUILD_DIR}/php-${PHP_VERSION}/sapi/litespeed/php"

chmod a+rx admin_php-${PHP_VERSION}

echo "strip admin_php-${PHP_VERSION}"
strip admin_php-${PHP_VERSION}

echo "ln -sf admin_php-${PHP_VERSION} admin_php"
ln -sf admin_php-${PHP_VERSION} admin_php
check_errs $? "fail to creat symbolic link"


echo ""
echo "=============================================="
echo "Finished building admin_php with ${PHP_VERSION} and  LSAPI ${LSAPI_VERSION}"
echo "=============================================="
echo `date`
echo ""
 
 
main_msg "**COMPLETE**"

INST_USER=`id`
INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`

if [  "x$INST_USER" = "xroot" ]; then
    echo "for secuirty reason, change back build dir to regular user"
    echo " chown -R lsadm:lsadm ${PHP_BUILD_DIR}/php-${PHP_VERSION}"
    chown -R lsadm:lsadm ${PHP_BUILD_DIR}/php-${PHP_VERSION}
fi
