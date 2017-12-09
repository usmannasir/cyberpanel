#!/bin/sh

OSNAMEVER=UNKNOWN
OSNAME=
OSVER=
OSTYPE=`uname -m`
MARIADBCPUARCH=


inst_admin_php()
{
    # detect download method
    OS=`uname -s`
    OSTYPE=`uname -m`

    DLCMD=
    DL=`which wget`
    if [ $? -eq 0 ] ; then
        DLCMD="wget -nv -O "
    else
        DL=`which curl`
        if [ $? -eq 0 ] ; then
            DLCMD="curl -L -o "
        else
            if [ "x$OS" = "xFreeBSD" ] ; then
                DL=`which fetch`
                if [ $? -eq 0 ] ; then
                    DLCMD="fetch -o "
                fi
            fi
        fi
    fi

    if [ "x$DLCMD" = "x" ] ; then
        echo "ERROR: cannot find proper download method curl/wget/fetch."
    fi

    echo "DLCMD is $DLCMD"
    echo

    HASADMINPHP=n
    if [ -f "$LSWS_HOME/admin/fcgi-bin/admin_php" ] ; then
        mv "$LSWS_HOME/admin/fcgi-bin/admin_php" "$LSWS_HOME/admin/fcgi-bin/admin_php.bak"
        echo "admin_php found and mv to admin_php.bak"
    fi

    if [ ! -d "$LSWS_HOME/admin/fcgi-bin/" ] ; then
        mkdir -p "$LSWS_HOME/admin/fcgi-bin/"
        echo "Mkdir $LSWS_HOME/admin/fcgi-bin/ for installing admni_php"
    fi
        
    if [ "x$OS" = "xLinux" ] ; then
        if [ "x$OSTYPE" != "xx86_64" ] ; then
            $DLCMD $LSWS_HOME/admin/fcgi-bin/admin_php http://www.litespeedtech.com/packages/lsphp5_bin/i386/lsphp5
        else
            $DLCMD $LSWS_HOME/admin/fcgi-bin/admin_php http://www.litespeedtech.com/packages/lsphp5_bin/x86_64/lsphp5
        fi
        
        if [ $? = 0 ] ; then 
            HASADMINPHP=y
            echo "admin_php downloaded."
        fi
        
#        if [ -f  "$LSWS_HOME/admin/fcgi-bin/admin_php" ] ; then
#            HASADMINPHP=y
#        fi

    elif [ "x$OS" = "xFreeBSD" ] ; then
        if [ "x$OSTYPE" != "xamd64" ] ; then
           $DLCMD $LSWS_HOME/admin/fcgi-bin/admin_php http://www.litespeedtech.com/packages/lsphp5_bin/i386-freebsd/lsphp5
        else
           $DLCMD $LSWS_HOME/admin/fcgi-bin/admin_php http://www.litespeedtech.com/packages/lsphp5_bin/x86_64-freebsd/lsphp5
        fi
       
        if [ $? = 0 ] ; then 
           HASADMINPHP=y
           echo "admin_php downloaded."
        fi
    fi

    if [ "x$HASADMINPHP" = "xn" ] ; then
        echo -e "\033[38;5;148mStart to build php, this may take several minutes, please waiting ...\033[39m"
        $LSWS_HOME/admin/misc/build_admin_php.sh
    else
        chmod "$EXEC_MOD" "$LSWS_HOME/admin/fcgi-bin/admin_php"
    fi

    #final checking of existence of admin_php
    if [ ! -f "$LSWS_HOME/admin/fcgi-bin/admin_php" ] ; then
        echo -e "\033[38;5;148mFinal checking found admin_php not exists, installation abort.\033[39m"
        exit 1
    fi
}


install_lsphp7_centos()
{
    action=install
    ND=nd
    LSPHPVER=70
    yum -y $action epel-release
    rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el$OSVER.noarch.rpm
    yum -y $action lsphp$LSPHPVER lsphp$LSPHPVER-common lsphp$LSPHPVER-gd lsphp$LSPHPVER-process lsphp$LSPHPVER-mbstring lsphp$LSPHPVER-mysql$ND lsphp$LSPHPVER-xml lsphp$LSPHPVER-mcrypt lsphp$LSPHPVER-pdo lsphp$LSPHPVER-imap
    
    if [ ! -f "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" ] ; then
        action=reinstall
        
        yum -y remove lsphp$LSPHPVER-mysql$ND
        yum -y install lsphp$LSPHPVER-mysql$ND
        yum -y $action lsphp$LSPHPVER lsphp$LSPHPVER-common lsphp$LSPHPVER-gd lsphp$LSPHPVER-process lsphp$LSPHPVER-mbstring lsphp$LSPHPVER-xml lsphp$LSPHPVER-mcrypt lsphp$LSPHPVER-pdo lsphp$LSPHPVER-imap
    fi
    
    if [ -f "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" ] ; then
        ln -sf "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" "$LSWS_HOME/fcgi-bin/lsphp7"
    fi
}

install_lsphp7_debian()
{
    LSPHPVER=70

    grep -Fq  "http://rpms.litespeedtech.com/debian/" /etc/apt/sources.list.d/lst_debian_repo.list
    if [ $? != 0 ] ; then
        echo "deb http://rpms.litespeedtech.com/debian/ $OSVER main"  > /etc/apt/sources.list.d/lst_debian_repo.list
    fi
    
    wget -O /etc/apt/trusted.gpg.d/lst_debian_repo.gpg http://rpms.litespeedtech.com/debian/lst_debian_repo.gpg
    wget -O /etc/apt/trusted.gpg.d/lst_repo.gpg http://rpms.litespeedtech.com/debian/lst_repo.gpg
    apt-get -y update
    
    apt-get -y install lsphp$LSPHPVER lsphp$LSPHPVER-mysql lsphp$LSPHPVER-imap lsphp$LSPHPVER-common 
    
    if [ ! -f "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" ] ; then
        apt-get -y --reinstall install lsphp$LSPHPVER lsphp$LSPHPVER-mysql lsphp$LSPHPVER-imap lsphp$LSPHPVER-common 
    fi
    
    if [ -f "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" ] ; then
        ln -sf "$LSWS_HOME/lsphp$LSPHPVER/bin/lsphp" "$LSWS_HOME/fcgi-bin/lsphp7"
    fi
}

check_os()
{
    OSNAMEVER=
    OSNAME=
    OSVER=
    MARIADBCPUARCH=
    
    if [ -f /etc/redhat-release ] ; then
        cat /etc/redhat-release | grep " 5." >/dev/null
        if [ $? = 0 ] ; then
            OSNAMEVER=CENTOS5
            OSNAME=centos
            OSVER=5
        else
            cat /etc/redhat-release | grep " 6." >/dev/null
            if [ $? = 0 ] ; then
                OSNAMEVER=CENTOS6
                OSNAME=centos
                OSVER=6
            else
                cat /etc/redhat-release | grep " 7." >/dev/null
                if [ $? = 0 ] ; then
                    OSNAMEVER=CENTOS7
                    OSNAME=centos
                    OSVER=7

                fi
            fi
        fi
    elif [ -f /etc/lsb-release ] ; then
        cat /etc/lsb-release | grep "DISTRIB_RELEASE=12." >/dev/null
        if [ $? = 0 ] ; then
            OSNAMEVER=UBUNTU12
            OSNAME=ubuntu
            OSVER=precise
            MARIADBCPUARCH="arch=amd64,i386"
            
        else
            cat /etc/lsb-release | grep "DISTRIB_RELEASE=14." >/dev/null
            if [ $? = 0 ] ; then
                OSNAMEVER=UBUNTU14
                OSNAME=ubuntu
                OSVER=trusty
                MARIADBCPUARCH="arch=amd64,i386,ppc64el"
            else
                cat /etc/lsb-release | grep "DISTRIB_RELEASE=16." >/dev/null
                if [ $? = 0 ] ; then
                    OSNAMEVER=UBUNTU16
                    OSNAME=ubuntu
                    OSVER=xenial
                    MARIADBCPUARCH="arch=amd64,i386,ppc64el"
                fi
            fi
        fi    
    elif [ -f /etc/debian_version ] ; then
        cat /etc/debian_version | grep "^7." >/dev/null
        if [ $? = 0 ] ; then
            OSNAMEVER=DEBIAN7
            OSNAME=debian
            OSVER=wheezy
            MARIADBCPUARCH="arch=amd64,i386"
        else
            cat /etc/debian_version | grep "^8." >/dev/null
            if [ $? = 0 ] ; then
                OSNAMEVER=DEBIAN8
                OSNAME=debian
                OSVER=jessie
                MARIADBCPUARCH="arch=amd64,i386"
            else
                cat /etc/debian_version | grep "^9." >/dev/null
                if [ $? = 0 ] ; then
                    OSNAMEVER=DEBIAN9
                    OSNAME=debian
                    OSVER=stretch
                    MARIADBCPUARCH="arch=amd64,i386"
                fi
            fi
        fi
    fi

    if [ "x$OSNAMEVER" != "x" ] ; then
        if [ "x$OSNAME" = "xcentos" ] ; then
            echoG "Current platform is "  "$OSNAME $OSVER."
        else
            export DEBIAN_FRONTEND=noninteractive
            echoG "Current platform is "  "$OSNAMEVER $OSNAME $OSVER."
        fi
    fi
}


inst_lsphp7()
{
    check_os
    if [ "x$OSNAME" = "xcentos" ] ; then
        install_lsphp7_centos
    else
        install_lsphp7_debian
    fi
}


#script start here
cd `dirname "$0"`
source ./functions.sh 2>/dev/null
if [ $? != 0 ]; then
    . ./functions.sh
    if [ $? != 0 ]; then
        echo [ERROR] Can not include 'functions.sh'.
        exit 1
    fi
fi

#If install.sh in admin/misc, need to change directory
LSINSTALL_DIR=`dirname "$0"`
#cd $LSINSTALL_DIR/


init
LSWS_HOME=$1

WS_USER=$2
if [ "x$WS_USER" = "xyes" ] ; then 
    WS_USER=nobody
fi

WS_GROUP=$3
if [ "x$WS_GROUP" = "xyes" ] ; then 
    WS_GROUP=nobody
fi

ADMIN_USER=$4
if [ "x$ADMIN_USER" = "xyes" ] ; then 
    ADMIN_USER=admin
fi

PASS_ONE=$5
if [ "x$PASS_ONE" = "xyes" ] ; then 
    PASS_ONE=123456
fi

ADMIN_EMAIL=$6
if [ "x$ADMIN_EMAIL" = "xyes" ] ; then 
    ADMIN_EMAIL=root@localhost
fi

ADMIN_SSL=$7
ADMIN_PORT=$8
if [ "x$ADMIN_PORT" = "xyes" ] ; then 
    ADMIN_PORT=7080
fi

USE_LSPHP7=$9
shift
DEFAULT_TMP_DIR=$9
shift
PID_FILE=$9
shift
HTTP_PORT=$9
if [ "x$HTTP_PORT" = "xyes" ] ; then 
    HTTP_PORT=8088
fi
shift
IS_LSCPD=$9


VERSION=open
SETUP_PHP=1
PHP_SUFFIX="php"
SSL_HOSTNAME=""

DEFAULT_USER="nobody"
DEFAULT_GROUP="nobody"
grep -q nobody: "/etc/group"
if  [ $? != 0 ] ; then
    DEFAULT_GROUP="nogroup"
fi

if [ "$WS_GROUP" = "nobody" ] ; then
    WS_GROUP=$DEFAULT_GROUP
fi


PHP_INSTALLED=n
INSTALL_TYPE="reinstall"
if [ -f "$LSWS_HOME/conf/httpd_config.xml" ] ; then

    printf '\033[31;42m\e[5mWarning:\e[25m\033[0m\033[31m This version uses a plain text configuration file which can also be modified by hand.\n\033[0m '
    printf '\033[31m \tThe XML configuration file for your current version (1.3.x or below) will be converted\n\tby the installation program to this format and a copy will be made of your current XML\n\033[0m '
    printf '\033[31m \tfile named <filename>.xml.bak. If you have any installed modules, they will need to be\n\trecompiled to comply with the upgraded API.\n\tAre you sure you want to upgrade to this version? [Yes/No]\033[0m '
    read Overwrite_Old
    echo

    if [ "x$Overwrite_Old" = "x" ]; then
        Overwrite_Old=No
    fi

    if [ "x$Overwrite_Old" != "xYes" ] && [ "x$Overwrite_Old" != "xY" ] ; then
        echo "Abort installation!" 
        exit 0
    fi
    echo
    
    echo -e "\033[38;5;148m$LSWS_HOME/conf/httpd_config.xml exists, will be converted to $LSWS_HOME/conf/httpd_config.conf!\033[39m"
    inst_admin_php
    PHP_INSTALLED=y
    
    if [ -e "$LSWS_HOME/conf/httpd_config.conf" ] ; then
        mv "$LSWS_HOME/conf/httpd_config.conf" "$LSWS_HOME/conf/httpd_config.conf.old"
    fi
    
    if [ -e "$LSWS_HOME/DEFAULT/conf/vhconf.conf" ] ; then
        mv "$LSWS_HOME/DEFAULT/conf/vhconf.conf" "$LSWS_HOME/DEFAULT/conf/vhconf.conf.old"
    fi

    if [ ! -d "$LSWS_HOME/backup" ] ; then
        mkdir "$LSWS_HOME/backup"
    fi

    $LSINSTALL_DIR/admin/misc/convertxml.sh $LSWS_HOME
    if [ -e "$LSWS_HOME/conf/httpd_config.xml" ] ; then
        rm "$LSWS_HOME/conf/httpd_config.xml"
    fi
fi

if [ -f "$LSWS_HOME/conf/httpd_config.conf" ] ; then
    INSTALL_TYPE="upgrade"
    #Now check if the user and group match with the conf file
    OLD_USER_CONF=`grep "user" "$LSWS_HOME/conf/httpd_config.conf"`
    OLD_GROUP_CONF=`grep "group" "$LSWS_HOME/conf/httpd_config.conf"`
    OLD_USER=`expr "$OLD_USER_CONF" : '\s*user\s*\(\S*\)'`
    OLD_GROUP=`expr "$OLD_GROUP_CONF" : '\s*group\s*\(\S*\)'`
    
    if [ "$WS_USER" = "$DEFAULT_USER" ] && [ "$WS_GROUP" = "$DEFAULT_GROUP" ] ; then
        WS_USER=$OLD_USER
        WS_GROUP=$OLD_GROUP
    fi
    
    if [ "$OLD_USER" != "$WS_USER" ] || [ "$OLD_GROUP" != "$WS_GROUP" ]; then
        echo -e "\033[38;5;148m$LSWS_HOME/conf/httpd_config.conf exists, but the user/group do not match, installing abort!\033[39m"
        echo -e "\033[38;5;148mYou may change the user/group or remove the direcoty $LSWS_HOME and re-install.\033[39m"
        exit 1
    fi
fi

echo "INSTALL_TYPE is $INSTALL_TYPE"

DIR_OWN=$WS_USER:$WS_GROUP
CONF_OWN=$WS_USER:$WS_GROUP

if [ "x$IS_LSCPD" != "xyes" ] ; then 
    configRuby
fi


#Comment out the below two lines
echo "Target_Dir:$LSWS_HOME User:$WS_USER Group:$WS_GROUP "

if [ "x$IS_LSCPD" != "xyes" ] ; then 
    echo "Admin:$ADMIN_USER Password:$PASS_ONE AdminSSL:$ADMIN_SSL ADMIN_PORT:$ADMIN_PORT "
fi

echo "LSINSTALL_DIR:$LSINSTALL_DIR "
echo "TEMP_DIR:$DEFAULT_TMP_DIR PID_FILE:$PID_FILE"
echo
echo -e "\033[38;5;148mInstalling, please wait...\033[39m"
echo



if [ "x$ADMIN_SSL" = "xyes" ] ; then
    echo "Admin SSL enabled!"
    gen_selfsigned_cert ../adminssl.conf
    cp $LSINSTALL_DIR/${SSL_HOSTNAME}.crt $LSINSTALL_DIR/admin/conf/${SSL_HOSTNAME}.crt
    cp $LSINSTALL_DIR/${SSL_HOSTNAME}.key $LSINSTALL_DIR/admin/conf/${SSL_HOSTNAME}.key
else
    echo "Admin SSL disabled!"
fi

if [ "x$IS_LSCPD" != "xyes" ] ; then 
    buildConfigFiles
    installation
    
    if [ "x$PHP_INSTALLED" = "xn" ] ; then 
        inst_admin_php
    fi
    rm $LSWS_HOME/bin/lshttpd
    ln -sf ./openlitespeed $LSWS_HOME/bin/lshttpd
    
    if [ ! -f "$LSWS_HOME/admin/conf/htpasswd" ] ; then
        ENCRYPT_PASS=`"$LSWS_HOME/admin/fcgi-bin/admin_php" -q "$LSWS_HOME/admin/misc/htpasswd.php" $PASS_ONE`
        echo "$ADMIN_USER:$ENCRYPT_PASS" > "$LSWS_HOME/admin/conf/htpasswd"
    fi

    if [ ! -f "$LSWS_HOME/fcgi-bin/lsphp" ]; then
        cp -f "$LSWS_HOME/admin/fcgi-bin/admin_php" "$LSWS_HOME/fcgi-bin/lsphp5"
        chown "$SDIR_OWN" "$LSWS_HOME/fcgi-bin/lsphp5"
        chmod "$EXEC_MOD" "$LSWS_HOME/fcgi-bin/lsphp5"
        
        #Set default lsphp5
        ln -sf "$LSWS_HOME/fcgi-bin/lsphp5" "$LSWS_HOME/fcgi-bin/lsphp" 
        
        if [ "x$USE_LSPHP7" = "xyes" ] ; then
            inst_lsphp7
            if [ -f "$LSWS_HOME/fcgi-bin/lsphp7" ]; then
                rm "$LSWS_HOME/fcgi-bin/lsphp"
                ln -sf "$LSWS_HOME/fcgi-bin/lsphp7" "$LSWS_HOME/fcgi-bin/lsphp" 
            fi
        fi
    fi


    #compress_admin_file
    if [ ! -f "$LSWS_HOME/admin/conf/jcryption_keypair" ]; then
        $LSWS_HOME/admin/misc/create_admin_keypair.sh
    fi

    chown "$CONF_OWN" "$LSWS_HOME/admin/conf/jcryption_keypair"
    chmod 0600 "$LSWS_HOME/admin/conf/jcryption_keypair"

    chown "$CONF_OWN" "$LSWS_HOME/admin/conf/htpasswd"
    chmod 0600 "$LSWS_HOME/admin/conf/htpasswd"


    #for root user, we'll try to start it automatically
    INST_USER=`id`
    INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`
    if [ $INST_USER = "root" ]; then
        $LSWS_HOME/admin/misc/rc-inst.sh
    fi
    
    echo "PIDFILE=$PID_FILE" > "$LSWS_HOME/bin/lsws_env"
    echo "GRACEFUL_PIDFILE=$DEFAULT_TMP_DIR/graceful.pid" >> "$LSWS_HOME/bin/lsws_env"
else
    installation_lscpd
    rm "$LSWS_HOME/bin/lscpd"
    mv "$LSWS_HOME/bin/openlitespeed" "$LSWS_HOME/bin/lscpd"
    
    if [ ! -f "$LSWS_HOME/fcgi-bin/lsphp" ]; then
        inst_lsphp7
        if [ -f "$LSWS_HOME/fcgi-bin/lsphp7" ]; then
            rm "$LSWS_HOME/fcgi-bin/lsphp"
            ln -sf "$LSWS_HOME/fcgi-bin/lsphp7" "$LSWS_HOME/fcgi-bin/lsphp" 
        else
            mkdir -p $LSWS_HOME/admin/fcgi-bin
            inst_admin_php
            mv "$LSWS_HOME/admin/fcgi-bin/admin_php" "$LSWS_HOME/fcgi-bin/lsphp"
            rm -rf $LSWS_HOME/admin/fcgi-bin
        fi
    fi
fi



echo
echo -e "\033[38;5;148mInstallation finished, Enjoy!\033[39m"
echo


