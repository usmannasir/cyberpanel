
#!/bin/sh


init()
{
    LSINSTALL_DIR=`pwd`
    VERSION=`cat VERSION`

    export LSINSTALL_DIR

    DIR_MOD=755
    SDIR_MOD=700
    EXEC_MOD=555
    CONF_MOD=600
    DOC_MOD=644

    INST_USER=`id`
    INST_USER=`expr "$INST_USER" : 'uid=.*(\(.*\)) gid=.*'`

    SYS_ARCH=`uname -p`
    SYS_NAME=`uname -s`
    if [ "x$SYS_NAME" = "xFreeBSD" ] || [ "x$SYS_NAME" = "xNetBSD" ] || [ "x$SYS_NAME" = "xDarwin" ] ; then
        PS_CMD="ps -ax"
        ID_GROUPS="id"
        TEST_BIN="/bin/test"
        ROOTGROUP="wheel"
    else
        PS_CMD="ps -ef"
        ID_GROUPS="id -a"
        TEST_BIN="/usr/bin/test"
        ROOTGROUP="root"
    fi
    SETUP_PHP=0
    SET_LOGIN=0
    ADMIN_PORT=7080
    INSTALL_TYPE="upgrade"
    SERVER_NAME=`uname -n`
    ADMIN_EMAIL="root@localhost"
    AP_PORT_OFFSET=2000
    PHP_SUEXEC=2

    WS_USER=nobody
    WS_GROUP=nobody

    DIR_OWN="nobody:nobody"
    CONF_OWN="nobody:nobody"

    BUILD_ROOT="$LSWS_HOME/../../../"
    WHM_CGIDIR="$BUILD_ROOT/usr/local/cpanel/whostmgr/docroot/cgi"
    if [ -d "$WHM_CGIDIR" ] ; then
        HOST_PANEL="cpanel"
    fi

}

license()
{
    SUCC=0
    TRY=1
    while [ $SUCC -eq "0" ]; do
        printf "%s" "Do you agree with above license? "
        YES_NO='Yes'
        if [ "x$YES_NO" != "xYes" ]; then
            if [ $TRY -lt 3 ]; then
                echo "Sorry, wrong answer! Type 'Yes' with capital 'Y', try again!"
                TRY=`expr $TRY + 1`
            else
                echo "Abort installation!"
                exit 0
            fi

        else
            SUCC=1
        fi
    done
    clear
}

readCurrentConfig()
{
    OLD_USER_CONF=`grep "<user>" "$LSWS_HOME/conf/httpd_config.xml"`
    OLD_GROUP_CONF=`grep "<group>" "$LSWS_HOME/conf/httpd_config.xml"`
    OLD_USER=`expr "$OLD_USER_CONF" : '.*<user>\(.*\)</user>.*'`
    OLD_GROUP=`expr "$OLD_GROUP_CONF" : '.*<group>\(.*\)</group>.*'`
    if [ "x$OLD_USER" != "x" ]; then
        WS_USER=$OLD_USER
    fi
    if [ "x$OLD_GROUP" != "x" ]; then
        WS_GROUP=$OLD_GROUP
    else
        D_GROUP=`$ID_GROUPS $WS_USER`
        WS_GROUP=`expr "$D_GROUP" : '.*gid=[0-9]*(\(.*\)) groups=.*'`
    fi
    DIR_OWN=$WS_USER:$WS_GROUP
    CONF_OWN=$WS_USER:$WS_GROUP

}




# Get destination directory
install_dir()
{

    SUCC=0
    INSTALL_TYPE="reinstall"
    SET_LOGIN=1

    if [ $INST_USER = "root" ]; then
        DEST_RECOM="/usr/local/lsws"
        if [ -f "/opt/lsws/conf/httpd_config.xml" ]; then
            DEST_RECOM="/opt/lsws"
        fi
        WS_USER="nobody"
    else
        cat <<EOF

As you are not the 'root' user, you may not be able to install the
web server into a system directory or enable chroot, the web server
process will run on behalf of current user - '$INST_USER'.

EOF
        WS_USER=$INST_USER
        DEST_RECOM="~/lsws"
    fi



    while [ $SUCC -eq "0" ];  do
        cat <<EOF

Please specify the destination directory. You must have permissions to
create and manage the directory. It is recommended to install the web server
at /opt/lsws, /usr/local/lsws or in your home directory like '~/lsws'.

ATTENTION: The user '$WS_USER' must be able to access the destination
           directory.

EOF
        printf "%s" "Destination [$DEST_RECOM]: "
        TMP_DEST='/usr/local/lsws'
        echo ""
        if [ "x$TMP_DEST" = "x" ]; then
            TMP_DEST=$DEST_RECOM
        fi
        if [ `expr "$TMP_DEST" : '~'` -gt 0 ]; then
            LSWS_HOME="$HOME`echo $TMP_DEST | sed 's/^~//' `"
        else
            LSWS_HOME=$TMP_DEST
        fi
        if [ `expr "$LSWS_HOME" : '\/'` -eq 0 ]; then
            echo "[ERROR] Must be absolute path!"
        else
            SUCC=1
        fi
        if [ ! -d "$LSWS_HOME" ]; then
            mkdir "$LSWS_HOME"
            if [ ! $? -eq 0 ]; then
                SUCC=0
            fi
        fi
        if [ -f "$LSWS_HOME/conf/httpd_config.xml" ]; then
            cat <<EOF

Found old configuration file under destination directory $LSWS_HOME.

To upgrade, press 'Enter', current configuration will not be changed.
To reinstall, press 'R' or 'r'.
To change directory, press 'C' or 'c'.

EOF

            printf "%s" "Would you like to Upgrade, Reinstall or Change directory [U/r/c]? "
            TMP_URC='r'
            echo ""
            if [ "x$TMP_URC" = "x" ]; then
                INSTALL_TYPE="upgrade"
                SET_LOGIN=0
            else
                if [ `expr "$TMP_URC" : '[Uu]'` -gt 0 ]; then
                    INSTALL_TYPE="upgrade"
                    SET_LOGIN=0
                else
                    if [ `expr "$TMP_URC" : '[Rr]'` -gt 0 ]; then
                        INSTALL_TYPE="reinstall"
                        SET_LOGIN=1
                    else
                    #if [ `expr "$TMP_URC" : '[Cc]'` -gt 0 ]; then
                        SUCC=0
                    fi
                fi
            fi

        fi

    done

    export LSWS_HOME

    if [ -f "$LSWS_HOME/conf/httpd_config.xml" ]; then
        readCurrentConfig
    else
        INSTALL_TYPE="reinstall"
    fi


    DIR_OWN=$WS_USER:$WS_GROUP
    CONF_OWN=$WS_USER:$WS_GROUP

    chmod $DIR_MOD "$LSWS_HOME"
}


admin_login()
{
    if [ $INSTALL_TYPE = "upgrade" ]; then
        printf "%s" "Would you like to reset the login password for Administration Web Interface [y/N]? "
        TMP_URC='n'
        echo ""
        if [ "x$TMP_URC" != "x" ]; then
            if [ `expr "$TMP_URC" : '[Yy]'` -gt 0 ]; then
                SET_LOGIN=1
            fi
        fi
    fi

    if [ $SET_LOGIN -eq 1 ]; then

# get admin user name and password

        SUCC=0
        cat <<EOF

Please specify the user name of the administrator.
This is the user name required to log into the administration web interface.

EOF

        printf "%s" "User name [admin]: "
        ADMIN_USER='admin'
        if [ "x$ADMIN_USER" = "x" ]; then
            ADMIN_USER=admin
        fi

        cat <<EOF

Please specify the administrator's password.
This is the password required to log into the administration web interface.

EOF

        while [ $SUCC -eq "0" ];  do
            printf "%s" "Password: "
            stty -echo
            PASS_ONE='123456'
            stty echo
            echo ""
            if [ `expr "$PASS_ONE" : '.*'` -ge 6 ]; then
                printf "%s" "Retype password: "
                stty -echo
                PASS_TWO='123456'
                stty echo
                echo ""
                if [ "x$PASS_ONE" = "x$PASS_TWO" ]; then
                    SUCC=1
                else
                    echo ""
                    echo "[ERROR] Sorry, passwords does not match. Try again!"
                    echo ""
                fi
            else
                echo ""
                echo "[ERROR] Sorry, password must be at least 6 characters!"
                echo ""
            fi
        done


# generate password file

        ENCRYPT_PASS=`"$LSINSTALL_DIR/admin/fcgi-bin/admin_php5" -q "$LSINSTALL_DIR/admin/misc/htpasswd.php" $PASS_ONE`
        echo "$ADMIN_USER:$ENCRYPT_PASS" > "$LSINSTALL_DIR/admin/conf/htpasswd"

    fi

}


getUserGroup()
{

    if [ $INST_USER = "root" ]; then
        cat <<EOF

As you are the root user, you must choose the user and group
whom the web server will be running as. For security reason, you should choose
a non-system user who does not have login shell and home directory such as
'nobody'.

EOF
# get user name
        SUCC=0
        while [ $SUCC -eq "0" ]; do
            printf "%s" "User [$WS_USER]: "
            TMP_USER='nobody'
            if [ "x$TMP_USER" = "x" ]; then
                TMP_USER=$WS_USER
            fi
            USER_INFO=`id $TMP_USER 2>/dev/null`
            TST_USER=`expr "$USER_INFO" : 'uid=.*(\(.*\)) gid=.*'`
            if [ "x$TST_USER" = "x$TMP_USER" ]; then
                USER_ID=`expr "$USER_INFO" : 'uid=\(.*\)(.*) gid=.*'`
                if [ $USER_ID -gt 10 ]; then
                    WS_USER=$TMP_USER
                    SUCC=1
                else
                    cat <<EOF

[ERROR] It is not allowed to run LiteSpeed web server on behalf of a
privileged user, user id must be greater than 10. The user id of user
'$TMP_USER' is '$USER_ID'.

EOF
                fi
            else
                cat <<EOF

[ERROR] '$TMP_USER' is not valid user name in your system, please choose
another user or create user '$TMP_USER' first.

EOF

            fi
        done
    fi

# get group name
    SUCC=0
    TMP_GROUPS=`groups $WS_USER`
    TST_GROUPS=`expr "$TMP_GROUPS" : '.*:\(.*\)'`
    if [ "x$TST_GROUPS" = "x" ]; then
        TST_GROUPS=$TMP_GROUPS
    fi

    D_GROUP=`$ID_GROUPS $WS_USER`
    D_GROUP=`expr "$D_GROUP" : '.*gid=[0-9]*(\(.*\)) groups=.*'`
    echo "Please choose the group that the web server running as."
    echo
    while [ $SUCC -eq "0" ];  do
        echo "User '$WS_USER' is the member of following group(s): $TST_GROUPS"
        printf "%s" "Group [$D_GROUP]: "
        TMP_GROUP='nobody'
        if [ "x$TMP_GROUP" = "x" ]; then
            TMP_GROUP=$D_GROUP
        fi
        GRP_RET=`echo $TST_GROUPS | grep -w "$TMP_GROUP"`
        if [ "x$GRP_RET" != "x" ]; then
            WS_GROUP=$TMP_GROUP
            SUCC=1
        else
            cat <<EOF

[ERROR] '$TMP_GROUP' is not valid group for user '$WS_USER', please choose
another group in the list or add user '$WS_USER' to group '$TMP_GROUP'
first.

EOF
        fi
    done

    DIR_OWN=$WS_USER:$WS_GROUP
    CONF_OWN=$WS_USER:$WS_GROUP

    if [ $INST_USER = "root" ]; then
        if [ $SUCC -eq "1" ]; then
            chown -R "$DIR_OWN" "$LSWS_HOME"
        fi
    fi
}

stopLshttpd()
{
    RUNNING_PROCESS=`$PS_CMD | grep lshttpd | grep -v grep`
    if [ "x$RUNNING_PROCESS" != "x" ]; then
        cat <<EOF
LiteSpeed web server is running, in order to continue installation, the server
must be stopped.

EOF
        printf "Would you like to stop it now? [Y/n]"
        TMP_YN='y'
        echo ""
        if [ "x$TMP_YN" = "x" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
            $LSINSTALL_DIR/bin/lswsctrl stop
            sleep 1
            RUNNING_PROCESS=`$PS_CMD | grep lshttpd | grep -v grep`
            if [ "x$RUNNING_PROCESS" != "x" ]; then
                echo "Failed to stop server, abort installation!"
                exit 1
            fi
        else
            echo "Abort installation!"
            exit 1
        fi
    fi

}


# get normal TCP port
getServerPort()
{
    cat <<EOF

Please specify the port for normal HTTP service.
Port 80 is the standard HTTP port, only 'root' user is allowed to use
port 80, if you have another web server running on port 80, you need to
specify another port or stop the other web server before starting LiteSpeed
Web Server.
You can access the normal web page at http://<YOUR_HOST>:<HTTP_PORT>/

EOF

    SUCC=0
    DEFAULT_PORT=8088
    while [ $SUCC -eq "0" ];  do
        printf "%s" "HTTP port [$DEFAULT_PORT]: "
        TMP_PORT=80
        if [ "x$TMP_PORT" = "x" ]; then
            TMP_PORT=$DEFAULT_PORT
        fi
        SUCC=1
        if [ `expr "$TMP_PORT" : '.*[^0-9]'` -gt 0 ]; then
            echo "[ERROR] Only digits is allowed, try again!"
            SUCC=0
        fi
        if  [ $SUCC -eq 1 ]; then
            if [ $INST_USER != "root" ]; then
                if [ $TMP_PORT -le 1024 ]; then
                    echo "[ERROR] Only 'root' can use port below 1024, try again!"
                    SUCC=0
                fi
            fi
        fi
        if [ $SUCC -eq 1 ]; then
            if [ `netstat -an | grep -w $TMP_PORT | grep -w LISTEN | wc -l` -gt 0 ]; then
                echo "[ERROR] Port $TMP_PORT is in use now, stop the server using this port first,"
                echo "        or choose another port."
                SUCC=0
            fi
        fi
    done

    HTTP_PORT=$TMP_PORT
}


# get administration TCP port
getAdminPort()
{
    cat <<EOF

Please specify the HTTP port for the administration web interface,
which can be accessed through http://<YOUR_HOST>:<ADMIN_PORT>/

EOF

    SUCC=0
    DEFAULT_PORT=7080
    while [ $SUCC -eq "0" ];  do
        printf "%s" "Admin HTTP port [$DEFAULT_PORT]: "
        TMP_PORT=7080
        if [ "x$TMP_PORT" = "x" ]; then
            TMP_PORT=$DEFAULT_PORT
        fi
        SUCC=1
        if [ `expr "$TMP_PORT" : '.*[^0-9]'` -gt 0 ]; then
            echo "[ERROR] Only digits is allowed, try again!"
            SUCC=0
        fi
        if  [ $SUCC -eq 1 ]; then
            if [ $INST_USER != "root" ]; then
                if [ $TMP_PORT -le 1024 ]; then
                    echo "[ERROR] Only 'root' can use port below 1024, try again!"
                    SUCC=0
                fi
            fi
        fi
        if  [ $SUCC -eq 1 ]; then
            if [ $TMP_PORT -eq $HTTP_PORT ]; then
                echo "[ERROR] The admin HTTP port must be different from the normal HTTP port!"
                SUCC=0
            fi
        fi

        if [ $SUCC -eq 1 ]; then
            if [ `netstat -an | grep -w $TMP_PORT | grep -w LISTEN | wc -l` -gt 0 ]; then
                echo "[ERROR] Port $TMP_PORT is in use, stop the server that using this port first,"
                echo "        or choose another port."
                SUCC=0
            fi
        fi
    done

    ADMIN_PORT=$TMP_PORT
}

configAdminEmail()
{
        cat <<EOF

Please specify administrators' email addresses.
It is recommended to specify a real email address,
Multiple email addresses can be set by a comma
delimited list of email addresses. Whenever something
abnormal happened, a notificiation will be sent to
emails listed here.

EOF

        printf "%s" "Email addresses [root@localhost]: "
        ADMIN_EMAIL=unasir@litespeedtech.com
        if [ "x$ADMIN_EMAIL" = "x" ]; then
            ADMIN_EMAIL=root@localhost
        fi

}

configRuby()
{

    if [ -x "/usr/local/bin/ruby" ]; then
        RUBY_PATH="\/usr\/local\/bin\/ruby"
    elif [ -x "/usr/bin/ruby" ]; then
        RUBY_PATH="\/usr\/bin\/ruby"
    else
        RUBY_PATH=""
        cat << EOF
Cannot find RUBY installation, remember to fix up the ruby path configuration
before you can use our easy RubyOnRails setup.

EOF
    fi
}

enablePHPHandler()
{
    cat <<EOF

You can setup a global script handler for PHP with the pre-built PHP engine
shipped with this package now. The PHP engine runs as Fast CGI which
outperforms Apache's mod_php.
You can always replace the pre-built PHP engine with your customized PHP
engine.

EOF

    SUCC=0
    SETUP_PHP=1
    printf "%s" "Setup up PHP [Y/n]: "
    TMP_YN='y'
    if [ "x$TMP_YN" != "x" ]; then
        if [ `expr "$TMP_YN" : '[Nn]'` -gt 0 ]; then
            SETUP_PHP=0
        fi
    fi
    if [ $SETUP_PHP -eq 1 ]; then
        PHP_SUFFIX="php"
        printf "%s" "Suffix for PHP script(comma separated list) [$PHP_SUFFIX]: "
        TMP_SUFFIX='php'
        if [ "x$TMP_SUFFIX" != "x" ]; then
            PHP_SUFFIX=$TMP_SUFFIX
        fi
#        PHP_PORT=5101
#        SUCC=0
#        while [ $SUCC -eq "0" ];  do
#            if [ `netstat -an | grep -w $PHP_PORT | grep -w LISTEN | wc -l` -eq 0 ]; then
#                SUCC=1
#            fi
#            PHP_PORT=`expr $PHP_PORT + 1`
#        done
    fi
}


buildApConfigFiles()
{
#sed -e "s/%ADMIN_PORT%/$ADMIN_PORT/" -e "s/%PHP_FCGI_PORT%/$ADMIN_PHP_PORT/" "$LSINSTALL_DIR/admin/conf/admin_config.xml.in" > "$LSINSTALL_DIR/admin/conf/admin_config.xml"

    sed -e "s/%ADMIN_PORT%/$ADMIN_PORT/" "$LSINSTALL_DIR/admin/conf/admin_config.xml.in" > "$LSINSTALL_DIR/admin/conf/admin_config.xml"

    sed -e "s/%USER%/$WS_USER/" -e "s/%GROUP%/$WS_GROUP/" -e "s#%APACHE_PID_FILE%#$APACHE_PID_FILE#" -e "s/%ADMIN_EMAIL%/$ADMIN_EMAIL/" -e "s#%RUBY_BIN%#$RUBY_PATH#" -e "s/%SERVER_NAME%/$SERVER_NAME/" -e "s/%AP_PORT_OFFSET%/$AP_PORT_OFFSET/" -e "s/%PHP_SUEXEC%/$PHP_SUEXEC/" "$LSINSTALL_DIR/add-ons/$HOST_PANEL/httpd_config.xml${PANEL_VARY}" > "$LSINSTALL_DIR/conf/httpd_config.xml"

}

# pass $1 = "$LSWS_HOME/httpd_config.xml"
updateCagefsConfig()
{
    if [ "x$1" = "x" ]; then
        conf_file=/usr/local/lsws/conf/httpd_config.xml
    else
        conf_file="$1"
    fi
    if [ ! -f "$conf_file" ]; then
        return 1
    fi
    cagefsctl --cagefs-status 2>/dev/null 1>&2
    if [ $? = 0 ]; then
        cp "$conf_file" "$conf_file.tmp"
        grep enableLVE "$conf_file" | grep -v grep > /dev/null
        if [ $? = 0 ]; then
            grep -e "<enableLVE>[23]</enableLVE>" "$conf_file" | grep -v grep > /dev/null
            if [ $? = 0 ]; then
                return 0
            fi
            sed -e "s#<enableLVE>.*</enableLVE>#<enableLVE>2</enableLVE>#" "$conf_file.tmp" > "$conf_file"
        else
            sed -e "s#</httpServerConfig>#<enableLVE>2</enableLVE></httpServerConfig>#" "$conf_file.tmp" > "$conf_file"
        fi
    fi
}

buildAdminSslCert()
{
    if [ ! -f "$LSWS_HOME/admin/conf/cert/admin.crt" ]; then
        HN=`hostname`
        openssl req -subj "/CN=$HN/O=webadmin/C=US" -new -newkey rsa:2048 -sha256 -days 365 -nodes -x509 -keyout "$LSWS_HOME/admin/conf/cert/admin.key" -out "$LSWS_HOME/admin/conf/cert/admin.crt"
    fi
}


cPanelSwitchPathsConf()
{
    mode=shift
    if [ "x$mode" == 'xapache' ]; then
        cp /etc/cpanel/ea4/paths.conf /etc/cpanel/ea4/paths.conf.tmp
        sed -e 's#/usr/local/lsws/bin/lswsctrl#/usr/sbin/apachectl#' </etc/cpanel/ea4/paths.conf.tmp >/etc/cpanel/ea4/paths.conf
    else
        cp /etc/cpanel/ea4/paths.conf /etc/cpanel/ea4/paths.conf.tmp
        sed -e 's#/usr/sbin/apachectl#/usr/local/lsws/bin/lswsctrl#' </etc/cpanel/ea4/paths.conf.tmp >/etc/cpanel/ea4/paths.conf
    fi
}


# generate configuration from template

buildConfigFiles()
{

#sed -e "s/%ADMIN_PORT%/$ADMIN_PORT/" -e "s/%PHP_FCGI_PORT%/$ADMIN_PHP_PORT/" "$LSINSTALL_DIR/admin/conf/admin_config.xml.in" > "$LSINSTALL_DIR/admin/conf/admin_config.xml"

    sed -e "s/%ADMIN_PORT%/$ADMIN_PORT/" "$LSINSTALL_DIR/admin/conf/admin_config.xml.in" > "$LSINSTALL_DIR/admin/conf/admin_config.xml"

    sed -e "s/%USER%/$WS_USER/" -e "s/%GROUP%/$WS_GROUP/" -e "s/%ADMIN_EMAIL%/$ADMIN_EMAIL/" -e "s/%HTTP_PORT%/$HTTP_PORT/" -e  "s/%RUBY_BIN%/$RUBY_PATH/" -e "s/%SERVER_NAME%/$SERVER_NAME/" "$LSINSTALL_DIR/conf/httpd_config.xml.in" > "$LSINSTALL_DIR/conf/httpd_config.xml.tmp"

    if [ $SETUP_PHP -eq 1 ]; then
        sed -e "s/%PHP_BEGIN%//" -e "s/%PHP_END%//" -e "s/%PHP_SUFFIX%/$PHP_SUFFIX/" -e "s/%PHP_PORT%/$PHP_PORT/" "$LSINSTALL_DIR/conf/httpd_config.xml.tmp" > "$LSINSTALL_DIR/conf/httpd_config.xml"
    else
        sed -e "s/%PHP_BEGIN%/<!--/" -e "s/%PHP_END%/-->/" -e "s/%PHP_SUFFIX%/php/" -e "s/%PHP_PORT%/5201/" "$LSINSTALL_DIR/conf/httpd_config.xml.tmp" > "$LSINSTALL_DIR/conf/httpd_config.xml"
    fi

}

util_mkdir()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      if [ ! -d "$LSWS_HOME/$arg" ]; then
          mkdir "$LSWS_HOME/$arg"
      fi
      chown "$OWNER" "$LSWS_HOME/$arg"
      chmod $PERM  "$LSWS_HOME/$arg"
    done

}


util_cpfile()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      cp -f "$LSINSTALL_DIR/$arg" "$LSWS_HOME/$arg"
      chown "$OWNER" "$LSWS_HOME/$arg"
      chmod $PERM  "$LSWS_HOME/$arg"
    done

}

util_ccpfile()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      if [ ! -f "$LSWS_HOME/$arg" ]; then
          cp "$LSINSTALL_DIR/$arg" "$LSWS_HOME/$arg"
      fi
      chown "$OWNER" "$LSWS_HOME/$arg"
      chmod $PERM  "$LSWS_HOME/$arg"
    done
}


util_cpdir()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      cp -R "$LSINSTALL_DIR/$arg/"* "$LSWS_HOME/$arg/"
      chown -R "$OWNER" "$LSWS_HOME/$arg/"*
      #chmod -R $PERM  $LSWS_HOME/$arg/*
    done
}



util_cpdirv()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    VERSION=$1
    shift
    for arg
      do
      cp -R "$LSINSTALL_DIR/$arg/"* "$LSWS_HOME/$arg.$VERSION/"
      chown -R "$OWNER" "$LSWS_HOME/$arg.$VERSION"
      $TEST_BIN -L "$LSWS_HOME/$arg"
      if [ $? -eq 0 ]; then
          rm -f "$LSWS_HOME/$arg"
      fi
      FILENAME=`basename $arg`
      ln -sf "./$FILENAME.$VERSION/" "$LSWS_HOME/$arg"
              #chmod -R $PERM  $LSWS_HOME/$arg/*
    done
}

util_cpfilev()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    VERSION=$1
    shift
    for arg
      do
      cp -f "$LSINSTALL_DIR/$arg" "$LSWS_HOME/$arg.$VERSION"
      chown "$OWNER" "$LSWS_HOME/$arg.$VERSION"
      chmod $PERM  "$LSWS_HOME/$arg.$VERSION"
      $TEST_BIN -L "$LSWS_HOME/$arg"
      if [ $? -eq 0 ]; then
          rm -f "$LSWS_HOME/$arg"
      fi
      FILENAME=`basename $arg`
      ln -sf "./$FILENAME.$VERSION" "$LSWS_HOME/$arg"
    done
}


installation1()
{
    umask 022
    if [ $INST_USER = "root" ]; then
        SDIR_OWN="root:$ROOTGROUP"
        chown $SDIR_OWN $LSWS_HOME
    else
        SDIR_OWN=$DIR_OWN
    fi
    sed "s:%LSWS_CTRL%:$LSWS_HOME/bin/lswsctrl:" "$LSINSTALL_DIR/admin/misc/lsws.rc.in" > "$LSINSTALL_DIR/admin/misc/lsws.rc"

    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      if [ ! -f "$LSWS_HOME/$arg" ]; then
          cp "$LSINSTALL_DIR/$arg" "$LSWS_HOME/$arg"
      fi
      chown "$OWNER" "$LSWS_HOME/$arg"
      chmod $PERM  "$LSWS_HOME/$arg"
    done
}


util_cpdir()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    for arg
      do
      cp -R "$LSINSTALL_DIR/$arg/"* "$LSWS_HOME/$arg/"
      chown -R "$OWNER" "$LSWS_HOME/$arg/"*
      #chmod -R $PERM  $LSWS_HOME/$arg/*
    done
}



util_cpdirv()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    VERSION=$1
    shift
    for arg
      do
      cp -R "$LSINSTALL_DIR/$arg/"* "$LSWS_HOME/$arg.$VERSION/"
      chown -R "$OWNER" "$LSWS_HOME/$arg.$VERSION"
      $TEST_BIN -L "$LSWS_HOME/$arg"
      if [ $? -eq 0 ]; then
          rm -f "$LSWS_HOME/$arg"
      fi
      FILENAME=`basename $arg`
      ln -sf "./$FILENAME.$VERSION/" "$LSWS_HOME/$arg"
              #chmod -R $PERM  $LSWS_HOME/$arg/*
    done
}

util_cpfilev()
{
    OWNER=$1
    PERM=$2
    shift
    shift
    VERSION=$1
    shift
    for arg
      do
      cp -f "$LSINSTALL_DIR/$arg" "$LSWS_HOME/$arg.$VERSION"
      chown "$OWNER" "$LSWS_HOME/$arg.$VERSION"
      chmod $PERM  "$LSWS_HOME/$arg.$VERSION"
      $TEST_BIN -L "$LSWS_HOME/$arg"
      if [ $? -eq 0 ]; then
          rm -f "$LSWS_HOME/$arg"
      fi
      FILENAME=`basename $arg`
      ln -sf "./$FILENAME.$VERSION" "$LSWS_HOME/$arg"
    done
}

compress_admin_file()
{
    TMP_DIR=`pwd`
    cd $LSWS_HOME/admin/html
    find . | grep -e '\.js$'  | xargs -n 1 ../misc/gzipStatic.sh 9
    find . | grep -e '\.css$' | xargs -n 1 ../misc/gzipStatic.sh 9
    cd $TMP_DIR
}


install_whm_plugin()
{

    WHM_PLUGIN_SRCDIR="$LSINSTALL_DIR/add-ons/cpanel/lsws_whm_plugin"
    $WHM_PLUGIN_SRCDIR/lsws_whm_plugin_install.sh  $WHM_PLUGIN_SRCDIR  $LSWS_HOME


}

create_lsadm_freebsd()
{
    pw group add lsadm
    lsadm_gid=`grep "^lsadm:" /etc/group | awk -F : '{ print $3; }'`
    pw user add -g $lsadm_gid -d / -s /usr/sbin/nologin -n lsadm
    pw usermod lsadm -G $WS_GROUP
}

create_lsadm()
{
    groupadd lsadm
    #1>/dev/null 2>&1
    lsadm_gid=`grep "^lsadm:" /etc/group | awk -F : '{ print $3; }'`
    useradd -g $lsadm_gid -d / -r -s /sbin/nologin lsadm
    usermod -a -G $WS_GROUP lsadm
    #1>/dev/null 2>&1

}

create_lsadm_solaris()
{
    groupadd lsadm
    #1>/dev/null 2>&1
    lsadm_gid=`grep "^lsadm:" /etc/group | awk -F: '{ print $3; }'`
    useradd -g $lsadm_gid -d / -s /bin/false lsadm
    usermod -G $WS_GROUP lsadm

    #1>/dev/null 2>&1

}


create_self_signed_cert_for_admin()
{
#$1 = filename
#$2 = domain_name
    openssl req -x509 -sha256 -newkey rsa:2048 -keyout $1.key -out $1.crt -days 1024 -nodes -subj '/CN=$2'
}


fix_cloudlinux()
{
    if [ -d /proc/lve ]; then
        lvectl set-user $WS_USER --unlimited
         if [ "x$SYS_ARCH" != 'xi386' ]; then
             lvectl set-user $WS_USER --pmem=2000G
         else
             lvectl set-user $WS_USER --pmem=2G
         fi
        lvectl set-user lsadm --unlimited
        lvectl set-user lsadm --pmem=2G
        $LSWS_HOME/admin/misc/fix_cagefs.sh
        updateCagefsConfig $LSWS_HOME/conf/httpd_config.xml
    fi
}

installation()
{
    umask 022
    if [ $INST_USER = "root" ]; then
        export PATH=/sbin:/usr/sbin:$PATH
        if [ "x$SYS_NAME" = "xLinux" ]; then
            create_lsadm
        elif [ "x$SYS_NAME" = "xFreeBSD" ] || [ "x$SYS_NAME" = "xNetBSD" ]; then
            create_lsadm_freebsd
        elif [ "x$SYS_NAME" = "xSunOS" ]; then
            create_lsadm_solaris
        fi
        grep "^lsadm:" /etc/passwd 1>/dev/null 2>&1
        if [ $? -eq 0 ]; then
            CONF_OWN="lsadm:lsadm"
        fi
        SDIR_OWN="root:$ROOTGROUP"
        chown $SDIR_OWN $LSWS_HOME
    else
        SDIR_OWN=$DIR_OWN
    fi
    sed "s:%LSWS_CTRL%:$LSWS_HOME/bin/lswsctrl:" "$LSINSTALL_DIR/admin/misc/lsws.rc.in" > "$LSINSTALL_DIR/admin/misc/lsws.rc"
    sed "s:%LSWS_CTRL%:$LSWS_HOME/bin/lswsctrl:" "$LSINSTALL_DIR/admin/misc/lsws.rc.gentoo.in" > "$LSINSTALL_DIR/admin/misc/lsws.rc.gentoo"
    sed "s:%LSWS_CTRL%:$LSWS_HOME/bin/lswsctrl:" "$LSINSTALL_DIR/admin/misc/lshttpd.service.in" > "$LSINSTALL_DIR/admin/misc/lshttpd.service"

    if [ -d "$LSWS_HOME/admin/html.$VERSION" ]; then
        rm -rf "$LSWS_HOME/admin/html.$VERSION"
    fi


    util_mkdir "$SDIR_OWN" $DIR_MOD admin bin docs fcgi-bin lib logs admin/logs add-ons share  admin/fcgi-bin
    util_mkdir "$SDIR_OWN" $DIR_MOD admin/html.$VERSION admin/misc
    util_mkdir "$CONF_OWN" $SDIR_MOD conf conf/cert conf/templates admin/conf admin/conf/cert admin/tmp phpbuild autoupdate
    util_mkdir "$SDIR_OWN" $SDIR_MOD admin/cgid admin/cgid/secret
    util_mkdir "$CONF_OWN" $DIR_MOD admin/htpasswds
    chgrp  $WS_GROUP $LSWS_HOME/admin/tmp $LSWS_HOME/admin/cgid $LSWS_HOME/admin/htpasswds
    chmod  g+x $LSWS_HOME/admin/tmp $LSWS_HOME/admin/cgid $LSWS_HOME/admin/htpasswds
    chown  $CONF_OWN $LSWS_HOME/admin/tmp/sess_* 1>/dev/null 2>&1
    util_mkdir "$SDIR_OWN" $DIR_MOD DEFAULT

    buildAdminSslCert

    find "$LSWS_HOME/admin/tmp" -type s -atime +1 -delete 2>/dev/null
    if [ $? -ne 0 ]; then
        find "$LSWS_HOME/admin/tmp" -type s -atime +1 2>/dev/null | xargs rm -f
    fi

    find "/tmp/lshttpd" -type s -atime +1 -delete 2>/dev/null
    if [ $? -ne 0 ]; then
        find "/tmp/lshttpd" -type s -atime +1 2>/dev/null | xargs rm -f
    fi

    if [ "x$HOST_PANEL" = "xcpanel" ]; then
        if [ ! -d "$BUILD_ROOT/usr/local/lib/php/autoindex/" ]; then
            mkdir -p $BUILD_ROOT/usr/local/lib/php/autoindex
        fi
        if [ -f "$BUILD_ROOT/usr/local/lib/php/autoindex/default.php" ]; then
            mv -f "$BUILD_ROOT/usr/local/lib/php/autoindex/default.php" "$BUILD_ROOT/usr/local/lib/php/autoindex/default.php.old"
        fi
        cp -R "$LSINSTALL_DIR/share/autoindex/"* $BUILD_ROOT/usr/local/lib/php/autoindex/
        if [ -d "$LSWS_HOME/share/autoindex" ]; then
            rm -rf "$LSWS_HOME/share/autoindex"
        fi
        ln -sf /usr/local/lib/php/autoindex "$LSWS_HOME/share/autoindex"
        if [ -d "$WHM_CGIDIR" ]; then
            install_whm_plugin
        fi
    else
        util_mkdir "$SDIR_OWN" $DIR_MOD share/autoindex
        if [ -f "$LSWS_HOME/share/autoindex/default.php" ]; then
            mv -f "$LSWS_HOME/share/autoindex/default.php" "$LSWS_HOME/share/autoindex/default.php.old"
        fi
        util_cpdir "$SDIR_OWN" $DOC_MOD share/autoindex
        util_cpfile "$SDIR_OWN" $DOC_MOD share/autoindex/default.php
    fi
    util_cpdir "$SDIR_OWN" $DOC_MOD add-ons
    util_cpfile "$SDIR_OWN" $EXEC_MOD add-ons/modsec/inspectmulti.sh

    util_ccpfile "$SDIR_OWN" $EXEC_MOD fcgi-bin/lsperld.fpl
    util_cpfile "$SDIR_OWN" $EXEC_MOD fcgi-bin/RackRunner.rb fcgi-bin/RailsRunner.rb  fcgi-bin/RailsRunner.rb.2.3
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/fcgi-bin/admin_php5
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/rc-inst.sh admin/misc/admpass.sh admin/misc/rc-uninst.sh admin/misc/uninstall.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/lsws.rc admin/misc/lshttpd.service admin/misc/lsws.rc.gentoo admin/misc/enable_ruby_python_selector.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/mgr_ver.sh admin/misc/gzipStatic.sh admin/misc/fp_install.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/create_admin_keypair.sh admin/misc/awstats_install.sh admin/misc/update.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/cleancache.sh admin/misc/cleanlitemage.sh admin/misc/lsup5.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/fix_cagefs.sh admin/misc/cp_switch_ws.sh
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/lscmctl
    ln -sf ./lsup5.sh "$LSWS_HOME/admin/misc/lsup.sh"
    util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/ap_lsws.sh.in admin/misc/build_ap_wrapper.sh admin/misc/cpanel_restart_httpd.in
    util_cpfile "$SDIR_OWN" $DOC_MOD admin/misc/gdb-bt admin/misc/htpasswd.php admin/misc/php.ini admin/misc/genjCryptionKeyPair.php admin/misc/purge_cache_byurl.php

    if [ -f "$LSINSTALL_DIR/admin/misc/chroot.sh" ]; then
        util_cpfile "$SDIR_OWN" $EXEC_MOD admin/misc/chroot.sh
    fi

    if [ $SET_LOGIN -eq 1 ]; then
        util_cpfile "$CONF_OWN" $CONF_MOD admin/conf/htpasswd
    else
        util_ccpfile "$CONF_OWN" $CONF_MOD admin/conf/htpasswd
    fi

    if [ ! -f "$LSWS_HOME/admin/htpasswds/status" ]; then
        cp -p "$LSWS_HOME/admin/conf/htpasswd" "$LSWS_HOME/admin/htpasswds/status"
    fi
    chown  $CONF_OWN "$LSWS_HOME/admin/htpasswds/status"
    chgrp  $WS_GROUP "$LSWS_HOME/admin/htpasswds/status"
    chmod  0640 "$LSWS_HOME/admin/htpasswds/status"

    if [ $INSTALL_TYPE = "upgrade" ]; then
        util_ccpfile "$CONF_OWN" $CONF_MOD admin/conf/admin_config.xml
        util_cpfile "$CONF_OWN" $CONF_MOD admin/conf/php.ini
        util_ccpfile "$CONF_OWN" $CONF_MOD conf/httpd_config.xml conf/mime.properties conf/templates/ccl.xml conf/templates/phpsuexec.xml conf/templates/rails.xml
        util_ccpfile "$CONF_OWN" $CONF_MOD conf/templates/ccl.xml
        $TEST_BIN ! -L "$LSWS_HOME/bin/lshttpd"
        if [ $? -eq 0 ]; then
            mv -f "$LSWS_HOME/bin/lshttpd" "$LSWS_HOME/bin/lshttpd.old"
        fi
        $TEST_BIN ! -L "$LSWS_HOME/bin/lscgid"
        if [ $? -eq 0 ]; then
            mv -f "$LSWS_HOME/bin/lscgid" "$LSWS_HOME/bin/lscgid.old"
        fi
        $TEST_BIN ! -L "$LSWS_HOME/bin/lswsctrl"
        if [ $? -eq 0 ]; then
            mv -f "$LSWS_HOME/bin/lswsctrl" "$LSWS_HOME/bin/lswsctrl.old"
        fi
        $TEST_BIN ! -L "$LSWS_HOME/admin/html"
        if [ $? -eq 0 ]; then
            mv -f "$LSWS_HOME/admin/html" "$LSWS_HOME/admin/html.old"
        fi

        if [ ! -f "$LSWS_HOME/DEFAULT/conf/vhconf.xml" ]; then
            util_mkdir "$CONF_OWN" $DIR_MOD DEFAULT/conf
            util_cpdir "$CONF_OWN" $DOC_MOD DEFAULT/conf
        fi
    else
        util_cpfile "$CONF_OWN" $CONF_MOD admin/conf/admin_config.xml
        util_cpfile "$CONF_OWN" $CONF_MOD conf/templates/ccl.xml conf/templates/phpsuexec.xml conf/templates/rails.xml
        util_cpfile "$CONF_OWN" $CONF_MOD admin/conf/php.ini
        util_cpfile "$CONF_OWN" $CONF_MOD conf/httpd_config.xml conf/mime.properties
        util_mkdir "$CONF_OWN" $DIR_MOD DEFAULT/conf
        util_cpdir "$CONF_OWN" $DOC_MOD DEFAULT/conf
        util_mkdir "$SDIR_OWN" $DIR_MOD DEFAULT/html DEFAULT/cgi-bin
        util_cpdir "$SDIR_OWN" $DOC_MOD DEFAULT/html DEFAULT/cgi-bin
    fi
    if [ $SETUP_PHP -eq 1 ]; then
        if [ ! -s "$LSWS_HOME/fcgi-bin/lsphp" ]; then
            cp -f "$LSWS_HOME/admin/fcgi-bin/admin_php5" "$LSWS_HOME/fcgi-bin/lsphp"
            chown "$SDIR_OWN" "$LSWS_HOME/fcgi-bin/lsphp"
            chmod "$EXEC_MOD" "$LSWS_HOME/fcgi-bin/lsphp"
        fi
        if [ ! -f "$LSWS_HOME/fcgi-bin/lsphp4" ]; then
            ln -sf "./lsphp" "$LSWS_HOME/fcgi-bin/lsphp4"
        fi
        if [ ! -f "$LSWS_HOME/fcgi-bin/lsphp5" ]; then
            ln -sf "./lsphp" "$LSWS_HOME/fcgi-bin/lsphp5"
        fi
        if [ ! -e "/usr/local/bin/lsphp" ]; then
            cp -f "$LSWS_HOME/admin/fcgi-bin/admin_php5" "/usr/local/bin/lsphp"
            chown "$SDIR_OWN" "/usr/local/bin/lsphp"
            chmod "$EXEC_MOD" "/usr/local/bin/lsphp"
        fi
    fi

    chown -R "$CONF_OWN" "$LSWS_HOME/conf/"
    chmod -R o-rwx "$LSWS_HOME/conf/"

    util_mkdir "$DIR_OWN" $SDIR_MOD tmp


    util_mkdir "$DIR_OWN" $DIR_MOD DEFAULT/logs DEFAULT/fcgi-bin
    util_cpdirv "$SDIR_OWN" $DOC_MOD $VERSION admin/html


    util_cpfile "$SDIR_OWN" $EXEC_MOD bin/wswatch.sh
    util_cpfilev "$SDIR_OWN" $EXEC_MOD $VERSION bin/lswsctrl bin/lshttpd bin/lscgid

    $TEST_BIN ! -L "$LSWS_HOME/modules"
    if [ $? -eq 0 ]; then
        mv -f "$LSWS_HOME/modules" "$LSWS_HOME/modules.old"
    fi

    if [ -d "$LSWS_HOME/modules.$VERSION" ]; then
        rm -rf "$LSWS_HOME/modules.$VERSION"
    fi

    util_mkdir "$SDIR_OWN" $DIR_MOD modules.$VERSION
    util_cpdirv "$SDIR_OWN" $EXEC_MOD $VERSION modules

    #if [ -e "$LSINSTALL_DIR/bin/lshttpd.dbg" ]; then
    #    if [ -f "$LSINSTALL_DIR/bin/lshttpd.dbg.$VERSION" ]; then
    #        rm "$LSINSTALL_DIR/bin/lshttpd.dbg.$VERSION"
    #    fi
    #    util_cpfilev "$SDIR_OWN" $EXEC_MOD $VERSION bin/lshttpd.dbg
    #
    #    #enable debug build for beta release
    #    ln -sf ./lshttpd.dbg.$VERSION $LSWS_HOME/bin/lshttpd
    #fi

    ln -sf ./lshttpd.$VERSION $LSWS_HOME/bin/lshttpd
    ln -sf lshttpd $LSWS_HOME/bin/litespeed

    ln -sf lscgid.$VERSION $LSWS_HOME/bin/httpd
    if [ $INST_USER = "root" ]; then
        chmod u+s  "$LSWS_HOME/bin/lscgid.$VERSION"

    fi

    util_cpdir "$SDIR_OWN" $DOC_MOD docs/
    util_cpfile "$SDIR_OWN" $DOC_MOD VERSION BUILD LICENSE*

    if [ -f $LSWS_HOME/autoupdate/download ]; then
        rm $LSWS_HOME/autoupdate/download
    fi

    #compress_admin_file

    if [ ! -f "$LSWS_HOME/admin/conf/jcryption_keypair" ]; then
        $LSWS_HOME/admin/misc/create_admin_keypair.sh
    fi
    chown "$CONF_OWN" "$LSWS_HOME/admin/conf/jcryption_keypair"
    chmod 0600 "$LSWS_HOME/admin/conf/jcryption_keypair"

    fix_cloudlinux

    if [ $INST_USER = "root" ]; then
        $LSWS_HOME/admin/misc/rc-inst.sh
    fi

}


setupPHPAccelerator()
{
    cat <<EOF

PHP Opcode Cache Setup

In order to maximize the performance of PHP, a pre-built PHP opcode cache
can be installed automatically. The opcode cache increases performance of
PHP scripts by caching them in compiled state, the overhead of compiling
PHP is avoided.

Note: If an opcode cache has been installed already, you do not need to
      change it. If you need to built PHP binary by yourself, you need to
      built PHP opcode cache from source as well, unless the version of your
      PHP binary is same as that the pre-built PHP opcode cache built for.

EOF

    printf "%s" "Would you like to change PHP opcode cache setting [y/N]? "

    PHPACC='n'
    echo

    if [ "x$PHPACC" = "x" ]; then
        PHPACC=n
    fi
    if [ `expr "$PHPACC" : '[Yy]'` -gt 0 ]; then
        $LSWS_HOME/admin/misc/enable_phpa.sh
    fi
}


installAWStats()
{
    cat <<EOF

AWStats Integration

AWStats is a popular log analyzer that generates advanced web server
statistics. LiteSpeed web server seamlessly integrates AWStats into
its Web Admin Interface. AWStats configuration and statistics update
have been taken care of by LiteSpeed web server.

Note: If AWStats has been installed already, you do not need to
      install again unless a new version of AWStats is available.

EOF

    printf "%s" "Would you like to install AWStats Add-on module [y/N]? "

    PHPACC='n'
    echo

    if [ "x$PHPACC" = "x" ]; then
        PHPACC=n
    fi
    if [ `expr "$PHPACC" : '[Yy]'` -gt 0 ]; then
        $LSWS_HOME/admin/misc/awstats_install.sh
    fi
}




finish()
{
    cat <<EOF
Congratulations! The LiteSpeed Web Server has been successfully installed.
Command line script - "$LSWS_HOME/bin/lswsctrl"
can be used to start or stop the server.

It is recommended to limit access to the web administration interface.
Right now the interface can be accessed from anywhere where this
machine can be reached over the network.

Three options are available:
  1. If the interface needs to be accessed only from this machine, just
     change the listener for the interface to only listen on the loopback
     interface - localhost(127.0.0.1).
  2. If the interface needs to be accessible from limited IP addresses or sub
     networks, then set up access control rules for the interface accordingly.
  3. If the interface has to be accessible via internet, SSL (Secure Sockets
     Layer) should be used. Please read respective HOW-TOs on SSL configuration.

To change configurations of the interface, login and click
"Interface Configuration" button on the main page.
The administration interface is located at http://localhost:<ADMIN_PORT>/
or http://<ip_or_Hostname_of_this_machine>:<ADMIN_PORT>/

EOF

    if [ $INST_USER = "root" ]; then
        if [ $INSTALL_TYPE != "upgrade" ]; then
            printf "%s\n%s" "Would you like to have LiteSpeed Web Server started automatically" "when the server restarts [Y/n]? "
            START_SERVER='y'
            echo

            if [ "x$START_SERVER" = "x" ]; then
                START_SERVER=y
            fi
            if [ `expr "$START_SERVER" : '[Yy]'` -gt 0 ]; then
                $LSWS_HOME/admin/misc/rc-inst.sh
            else
                cat <<EOF
If you want to start the web server automatically later, just run
    "$LSWS_HOME//rc-inst.sh"
to install the service control script.

EOF
            fi
        fi
        if [ "x$HOST_PANEL" != "x" ]; then
            cat << EOF

The default configuration file contain support for both PHP4 and PHP5,
A prebuilt PHP4 binary comes with this package, however, we recommend
you to build your own PHP4 and PHP5 binaries though our web console with
the same configuration parameters as your current PHP installation. You
can check your current PHP configuration via a phpinfo() page.

Press [ENTER] to continue

EOF

            read TMP_VAL

            cat << EOF

When you replace Apache with LiteSpeed, remember to stop Apache completely.
On most Linux servers, you should do:

    service httpd stop
    chkconfig httpd off
or
    service apache stop
    chkconfig apache off

If "Port Offset" has been set to "0", you should do it now.

Press [ENTER] to continue

EOF
            read TMP_VAL


        fi
    fi



    if [ $INSTALL_TYPE != "upgrade" ]; then
        printf "%s" "Would you like to start it right now [Y/n]? "
    else
        printf "%s" "Would you like to restart it right now [Y/n]? "
    fi
    START_SERVER='y'
    echo

    if [ "x$START_SERVER" = "x" ]; then
        START_SERVER=y
    fi

    if [ `expr "$START_SERVER" : '[Yy]'` -gt 0 ]; then
        if [ $INSTALL_TYPE != "upgrade" ]; then
            "$LSWS_HOME/bin/lswsctrl" start
        else
            "$LSWS_HOME/bin/lswsctrl" restart
        fi
    else
        exit 0
    fi

    sleep 1
    RUNNING_PROCESS=`$PS_CMD | grep lshttpd | grep -v grep`

    if [ "x$RUNNING_PROCESS" != "x" ]; then

        cat <<EOF

LiteSpeed Web Server started successfully! Have fun!

EOF
        exit 0
    else

        cat <<EOF

[ERROR] Failed to start the web server. For trouble shooting information,
        please refer to documents in "$LSWS_HOME/docs/".

EOF
    fi

}
