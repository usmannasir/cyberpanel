#!/bin/sh

cd `dirname "$0"`
source ./functions.sh 2>/dev/null
if [ $? != 0 ]; then
    . ./functions.sh
    if [ $? != 0 ]; then
        echo [ERROR] Can not include 'functions.sh'.
        exit 1
    fi
fi


test_license()
{
    COPY_LICENSE_KEY=1
    if [ -f "$LSWS_HOME/conf/serial.no" ]; then
        if [ ! -f "$LSINSTALL_DIR/serial.no" ]; then
            cp "$LSWS_HOME/conf/serial.no" "$LSINSTALL_DIR/serial.no"
        else
            diff "$LSWS_HOME/conf/serial.no" "$LSINSTALL_DIR/serial.no" 1>/dev/null
            if [ $? -ne 0 ]; then
                COPY_LICENSE_KEY=0
            fi
        fi
    fi
#    if [ $COPY_LICENSE_KEY -eq 1 ]; then
#        if [ -f "$LSWS_HOME/conf/license.key" ] && [ ! -f "$LSINSTALL_DIR/license.key" ]; then
#            cp "$LSWS_HOME/conf/license.key" "$LSINSTALL_DIR/license.key"
#        fi
#        if [ -f "$LSWS_HOME/conf/license.key" ] && [ -f "$LSINSTALL_DIR/license.key" ]; then
#            diff "$LSWS_HOME/conf/license.key" "$LSINSTALL_DIR/license.key"
#            if [ $? -ne 0 ]; then
#                cp "$LSWS_HOME/conf/license.key" "$LSINSTALL_DIR/license.key"
#            fi
#        fi
#    fi
    if [ -f "$LSINSTALL_DIR/license.key" ] && [ -f "$LSINSTALL_DIR/serial.no" ]; then
        echo "License key and serial number are available, testing..."
        echo
        bin/lshttpd -V
        if [ $? -eq 0 ]; then
            LICENSE_OK=1
            if [ -f "$LSINSTALL_DIR/conf/license.key" ]; then
                mv "$LSINSTALL_DIR/conf/license.key" "$LSINSTALL_DIR/license.key"
                bin/lshttpd -t
            fi
        fi
        echo
    fi

    if [ "x$LICENSE_OK" = "x" ]; then
        if [ -f "$LSINSTALL_DIR/serial.no" ]; then
#            echo "Serial number is available."
#            printf "Would you like to register a license key for this server? [Y/n]"
#            read TMP_YN
#            echo ""
#            if [ "x$TMP_YN" = "x" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
                echo "Contacting licensing server ..."

                echo ""
                $LSINSTALL_DIR/bin/lshttpd -r
                
                if [ $? -eq 0 ]; then
                    echo "[OK] License key received."
                    $LSINSTALL_DIR/bin/lshttpd -t
                    if [ $? -eq 0 ]; then
                        LICENSE_OK=1
                    else
                        echo "The license key received does not work."
                    fi
                fi
#            fi
        fi
    fi

    if [ "x$LICENSE_OK" = "x" ]; then

        if [ -f "$LSINSTALL_DIR/trial.key" ]; then
            $LSINSTALL_DIR/bin/lshttpd -t
            if [ $? -ne 0 ]; then
                exit 1
            fi
        else
            cat <<EOF
[ERROR] Sorry, installation will abort without a valid license key.
 
For evaluation purpose, please obtain a trial license key from our web 
site http://www.litespeedtech.com, copy it to this directory 
and run Installer again.

If a production license has been purchased, please copy the serial number
from your confirmation email to this directory and run Installer again.

NOTE:
Please remember to set ftp to BINARY mode when you ftp trial.key from 
another machine.

EOF
            exit 1
        fi

    fi

}

configChroot()
{
    ENABLE_CHROOT=0
    CHROOT_PATH="/"
    if [ -f "$LSWS_HOME/conf/httpd_config.xml" ]; then
        OLD_ENABLE_CHROOT_CONF=`grep "<enableChroot>" "$LSWS_HOME/conf/httpd_config.xml"`
        OLD_CHROOT_PATH_CONF=`grep "<chrootPath>" "$LSWS_HOME/conf/httpd_config.xml"`
        OLD_ENABLE_CHROOT=`expr "$OLD_ENABLE_CHROOT_CONF" : '.*<enableChroot>\(.*\)</enableChroot>.*'`
        OLD_CHROOT_PATH=`expr "$OLD_CHROOT_PATH_CONF" : '[^<]*<chrootPath>\([^<]*\)</chrootPath>.*'`
        if [ "x$OLD_ENABLE_CHROOT" != "x" ]; then
            ENABLE_CHROOT=$OLD_ENABLE_CHROOT
        fi
        if [ "x$OLD_CHROOT_PATH" != "x" ]; then
            CHROOT_PATH=$OLD_CHROOT_PATH
        fi
    fi
    CHANGE_CHROOT=0
    if [ $INST_USER = "root" ]; then
        CHANGE_CHROOT=1

        if [ $INSTALL_TYPE = "upgrade" ]; then
            CHANGE_CHROOT=0
            if [ $ENABLE_CHROOT -eq 1 ]; then
                cat <<EOF
Chroot is enabled with your current setup and root directory is set to 
    $CHROOT_PATH

EOF
            else
                echo "Chroot is disabled with your current setup."
                echo
            fi
            printf "%s" "Would you like to change chroot settings [y/N]? "
            TMP_URC='n'
            echo ""
            if [ "x$TMP_URC" != "x" ]; then
                if [ `expr "$TMP_URC" : '[Yy]'` -gt 0 ]; then
                    CHANGE_CHROOT=1
                fi
            fi
        fi        

        if [ $CHANGE_CHROOT -eq 1 ]; then

            cat<<EOF

LiteSpeed Web Server Enterprise Edition can run in chroot environment.
It is impossible for the chrooted process and its children processes to 
access files outside the new root directory.

With chroot configured properly, there is no need to worry about sensitive 
data being accidentally exposed by insecure CGI programs or web server itself.
Even when a hacker some how gain a shell access, all files he can access is
under the chrooted directory. 

This installation script will try to setup the initial chroot environment 
automatically.

However, it is not easy to setup a chroot environment and you CGI program may
break. So we do not recommend enabling it for the first time user.
It can be enabled later by running this installation script again.

EOF

            SUCC=0
            printf "%s" "Enable chroot [y/N]: "
            TMP_YN='n'
            if [ `expr "x$TMP_YN" : 'x[Yy]'` -gt 1 ]; then
                ENABLE_CHROOT=1
            fi

            LSWS_HOME_LEN=`expr "$LSWS_HOME" : '.*'`
            if [ $ENABLE_CHROOT -eq 1 ]; then
                while [ $SUCC -eq 0 ]; do
                    cat <<EOF

Chroot path must be absolute path and the server root 
    $LSWS_HOME
must be included in the chroot directory tree.

EOF
                    printf "%s" "Chroot directory without trailing '/': "
                    TMP_CHROOT='n'
                    if [ "x$TMP_CHROOT" != "x" ]; then
                        if [ $TMP_CHROOT = '/' ]; then
                            echo "Set chroot directory to '/' will disable chroot."
                            printf "%s" "Are you sure? [y/N]"
                            read TMP_YN
                            if [ `expr "x$TMP_YN" : 'x[Yy]'` -gt 1 ]; then
                                ENABLE_CHROOT=0
                                SUCC=1
                            fi
                        else
                            CHROOT_LEN=`expr "$TMP_CHROOT" : '.*'`
                            MATCH_LEN=`expr "$LSWS_HOME" : "$TMP_CHROOT"`
                            if [ $CHROOT_LEN -ne $MATCH_LEN ]; then
                                echo "Server root is not included in the chroot directory tree"
                            else
                                TMP_CHROOT2="$TMP_CHROOT/"
                                TMP_HOME="$LSWS_HOME/"
                                MATCH_LEN=`expr "$TMP_HOME" : "$TMP_CHROOT2"`
                                if [ $MATCH_LEN -le $CHROOT_LEN ]; then
                                    echo "Server root is not included in the chroot diretory tree"
                                else
                                    SUCC=1
                                    CHROOT_PATH=$TMP_CHROOT
                                fi
                            fi
                        fi
                    fi
                done
            fi
        fi
    fi
}

changeChroot()
{
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/chroot.sh 

    if [ $CHANGE_CHROOT -eq 1 ]; then

        if [ $ENABLE_CHROOT -eq 1 ]; then
            $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH
            $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH $LSWS_HOME/bin/lshttpd
            $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH $LSWS_HOME/admin/fcgi-bin/admin_php5
            $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH $LSWS_HOME/bin/lscgid
            if [ -f $LSWS_HOME/fcgi-bin/php ]; then
                $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH $LSWS_HOME/fcgi-bin/php
            fi
            $LSWS_HOME/admin/misc/chroot.sh $CHROOT_PATH $LSWS_HOME/fcgi-bin/lsphp
            if [ `expr "x$CHROOT_PATH" : '^x/[^/]'` -gt 1 ]; then 
                cp $CHROOT_PATH/etc/passwd $CHROOT_PATH/etc/passwd.ls_bak
                cp $CHROOT_PATH/etc/group $CHROOT_PATH/etc/group.ls_bak
                egrep "$WS_USER|lsadm" /etc/passwd > $CHROOT_PATH/etc/passwd
                grep "$WS_GROUP" /etc/group > $CHROOT_PATH/etc/group
            fi
       fi    
        cp $LSWS_HOME/conf/httpd_config.xml $LSWS_HOME/conf/httpd_config.xml.bak
        chown "$DIR_OWN" $LSWS_HOME/conf/httpd_config.xml.bak
       RES=`grep '</chrootPath>' $LSWS_HOME/conf/httpd_config.xml.bak`
        if [ $? -eq 1 ]; then
            sed -e "s#</group>#</group><chrootPath>$CHROOT_PATH</chrootPath><enableChroot>$ENABLE_CHROOT</enableChroot>#" "$LSWS_HOME/conf/httpd_config.xml.bak" > "$LSWS_HOME/conf/httpd_config.xml" 
        else
            sed -e "s#<chrootPath>.*<\/chrootPath>#<chrootPath>$CHROOT_PATH<\/chrootPath>#" -e "s/<enableChroot>.*<\/enableChroot>/<enableChroot>$ENABLE_CHROOT<\/enableChroot>/" "$LSWS_HOME/conf/httpd_config.xml.bak" > "$LSWS_HOME/conf/httpd_config.xml"
        fi
    fi
}

installLicense()
{
    if [ -f ./serial.no ]; then
        cp -f ./serial.no $LSWS_HOME/conf
        chown "$SDIR_OWN" $LSWS_HOME/conf/serial.no
        chmod "$DOC_MOD" $LSWS_HOME/conf/serial.no
    fi

    if [ -f ./license.key ]; then
        cp -f ./license.key $LSWS_HOME/conf
        chown "$SDIR_OWN" $LSWS_HOME/conf/license.key
        chmod "$CONF_MOD" $LSWS_HOME/conf/license.key
    fi

    if [ -f ./trial.key ]; then
        cp -f ./trial.key $LSWS_HOME/conf
        chown "$SDIR_OWN" $LSWS_HOME/conf/trial.key
        chmod "$DOC_MOD" $LSWS_HOME/conf/trial.key
    fi
}

portOffset()
{
SUCC=0
SEL=0
while [ $SUCC -eq "0" ]; do

    cat <<EOF

Would you like to run LiteSpeed along side with Apache on another port
to make sure everything work properly? If yes, please set "Port Offset"
to a non-zero value, LiteSpeed will run on Port 80 + "Port Offset",
otherwise, set to "0" to replace Apache. 

EOF
    printf "%s" "Port Offset [2000]? "
    TMPS=0
    echo ""
    if [ "x$TMPS" != "x" ]; then
        if [ `expr "$TMP_PORT" : '.*[^0-9]'` -gt 0 ]; then
            echo "[ERROR] Only digits is allowed, try again!"
        else
            AP_PORT_OFFSET=$TMPS
            SUCC=1
        fi
    else
        SUCC=1
    fi
done
}

enablePHPsuExec()
{
SUCC=0
SEL=0
while [ $SUCC -eq "0" ]; do

    cat <<EOF

PHP suEXEC will run php scripts of each web site as the user who own the
document root directory, 
LiteSpeed PHP suEXEC does not have any performance penalty like other PHP
suEXEC implementation, and .htaccess configuration overriden has been fully
supported.

Note: You may need to fix some file/directory permissions if phpSuexec or 
suphp was not used with Apache.

Would you like to enable PHP suEXEC?
    0. No
    1. Yes
    2. Only in user's home directory (DirectAdmin should use this)
 

EOF
    printf "%s" "Please select (0-2)? [2]"
    TMPS=1
    echo ""
    if [ "x$TMPS" != "x" ]; then
        if [ `expr "$TMPS" : '[012]'` -gt 0 ]; then
            PHP_SUEXEC=$TMPS
            SUCC=1
        else
            echo "[ERROR] Wrong selection, try again!"
        fi
    else
        SUCC=1
    fi
done
}


hostPanelConfig()
{
    SETUP_PHP=1
    portOffset
    enablePHPsuExec
}

hostPanels()
{

SUCC=0
SEL=0
while [ $SUCC -eq "0" ]; do

    cat <<EOF

Will you use LiteSpeed Web Server with a hosting control panel?

    0. NONE
    1. cPanel
    2. DirectAdmin
    3. Plesk
    4. Hsphere
    5. Interworx
    6. Lxadmin
    7. ISPManager
EOF

    printf "%s" "Please select (0-7) [0]? "
    TMPS=0
    echo ""
    if [ "x$TMPS" != "x" ]; then
        if [ `expr "$TMPS" : '[01234567]'` -gt 0 ]; then
            SEL=$TMPS
            SUCC=1
            PANEL_VARY=""
            if [ $SEL -eq "1" ]; then
                HOST_PANEL="cpanel"
                WS_USER=nobody
                WS_GROUP=nobody
                if [ -e "/etc/cpanel/ea4/is_ea4" ] ; then
                    PANEL_VARY=".ea4"
                fi
            elif [ $SEL -eq "2" ]; then
                HOST_PANEL="directadmin"
                WS_USER=apache
                WS_GROUP=apache
            elif [ $SEL -eq "3" ]; then
                HOST_PANEL="plesk"
                USER_INFO=`id apache 2>/dev/null`
                TST_USER=`expr "$USER_INFO" : 'uid=.*(\(.*\)) gid=.*'`
                if [ "x$TST_USER" = "xapache" ]; then
                    WS_USER=apache
                    WS_GROUP=apache
                else
                    WS_USER=www-data
                    WS_GROUP=www-data
			# default PID FILE, source the real one, debian and ubuntu different
			APACHE_PID_FILE=/var/run/apache2/apache2.pid
			source /etc/apache2/envvars 2>/dev/null
			if [ $? != 0 ]; then
			    . /etc/apache2/envvars
			fi
		    PANEL_VARY=".debian"
                fi
                ADMIN_PORT=7088
            elif [ $SEL -eq "4" ]; then
                HOST_PANEL="hsphere"
                WS_USER=httpd
                WS_GROUP=httpd
            elif [ $SEL -eq "5" ]; then
                HOST_PANEL="interworx"
                WS_USER=apache
                WS_GROUP=apache
            elif [ $SEL -eq "6" ]; then
                HOST_PANEL="lxadminh"
                WS_USER=apache
                WS_GROUP=apache
            elif [ $SEL -eq "7" ]; then
                HOST_PANEL="ispmanager"
                WS_USER=apache
                WS_GROUP=apache
            fi
        fi
        DIR_OWN=$WS_USER:$WS_GROUP
        CONF_OWN=$WS_USER:$WS_GROUP
    else
        SUCC=1
    fi
done

}


LSINSTALL_DIR=`dirname "$0"`
cd $LSINSTALL_DIR

init
license
install_dir
test_license
admin_login


if [ $INSTALL_TYPE = "reinstall" ]; then

    configAdminEmail
    if [ $INST_USER = "root" ]; then
       hostPanels
    fi
    if [ "x$HOST_PANEL" = "x" ]; then
        getUserGroup
        stopLshttpd
        getServerPort
        getAdminPort
        configRuby
        enablePHPHandler
    else
        hostPanelConfig
    fi
fi

if [ "x$HOST_PANEL" = "x" ]; then
    configChroot
fi

cat <<EOF

Installing, please wait...

EOF

if [ "x$HOST_PANEL" = "xdirectadmin" ]; then
    chmod g+x /var/log/httpd/
    chgrp apache /var/log/httpd/
    chown apache:apache /var/log/httpd/domains
fi

if [ "x$HOST_PANEL" = "x" ]; then
    buildConfigFiles
else
    buildApConfigFiles
fi

installation

installLicense


if [ "x$HOST_PANEL" = "x" ]; then
    changeChroot
#    setupPHPAccelerator
    installAWStats
fi


finish

