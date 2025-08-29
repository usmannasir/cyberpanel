#!/bin/sh

# shellcheck disable=SC2153,SC1091
# SC2153 may trigger for variables (INST_USER, SDIR_OWN) that are defined in
# the sourced `functions.sh` or set by init(); disable to avoid false positives.
# SC1091: the linter may not be able to follow local or system-sourced files in
# this analysis environment; we intentionally source ./functions.sh and other
# env files at runtime so silence the not-following informational message.

cd "$(dirname "$0")" || exit 1
if ! . ./functions.sh 2>/dev/null; then
    if ! . ./functions.sh; then
        echo "[ERROR] Can not include 'functions.sh'."
        exit 1
    fi
fi

# shellcheck disable=SC2153
# SC2153 may trigger for variables (INST_USER, SDIR_OWN) that are defined in
# the sourced `functions.sh` or set by init(); disable to avoid false positives.
# NOTE: Several variables below (COPY_LICENSE_KEY, LSWS_HOME_LEN, AP_PORT_OFFSET,
# PHP_SUEXEC, SETUP_PHP, PANEL_VARY, ADMIN_PORT, CONF_OWN etc.) are intentionally
# defined in this script and referenced/consumed by the sourced functions.sh and
# by runtime templating (sed replacements). ShellCheck may report SC2034
# (appears unused) for them here; they are required for the installer runtime.


test_license()
{
    # shellcheck disable=SC2034
    COPY_LICENSE_KEY=1
    # NOTE: COPY_LICENSE_KEY is referenced by functions.sh/template flows when
    # copying existing license/serial files during upgrade paths.
    if [ -f "$LSWS_HOME/conf/serial.no" ]; then
        if [ ! -f "$LSINSTALL_DIR/serial.no" ]; then
            cp "$LSWS_HOME/conf/serial.no" "$LSINSTALL_DIR/serial.no"
        else
            if ! diff "$LSWS_HOME/conf/serial.no" "$LSINSTALL_DIR/serial.no" >/dev/null 2>&1; then
                # shellcheck disable=SC2034
                COPY_LICENSE_KEY=0
            fi
        fi
    fi
#    if [ $COPY_LICENSE_KEY -eq 1 ]; then
#        if [ -f "$LSWS_HOME/conf/license.key" ] && [ ! -f "$LSINSTALL_DIR/license.key" ]; then
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
    if "${LSINSTALL_DIR}/bin/lshttpd" -V; then
            LICENSE_OK=1
            if [ -f "$LSINSTALL_DIR/conf/license.key" ]; then
                mv "$LSINSTALL_DIR/conf/license.key" "$LSINSTALL_DIR/license.key"
                bin/lshttpd -t
            fi
        fi
        echo
    fi

    if [ -z "$LICENSE_OK" ]; then
        if [ -f "$LSINSTALL_DIR/serial.no" ]; then
#            echo "Serial number is available."
#            printf "Would you like to register a license key for this server? [Y/n]"
#            read -r TMP_YN
#            echo ""
#            if [ -z "$TMP_YN" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
                echo "Contacting licensing server ..."

                echo ""
                if "${LSINSTALL_DIR}/bin/lshttpd" -r; then
                    echo "[OK] License key received."
                    if "${LSINSTALL_DIR}/bin/lshttpd" -t; then
                        LICENSE_OK=1
                    else
                        echo "The license key received does not work."
                    fi
                fi
#            fi
        fi
    fi

    if [ -z "$LICENSE_OK" ]; then

        if [ -f "$LSINSTALL_DIR/trial.key" ]; then
            if ! "${LSINSTALL_DIR}/bin/lshttpd" -t; then
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
        OLD_ENABLE_CHROOT_CONF=$(grep "<enableChroot>" "$LSWS_HOME/conf/httpd_config.xml")
        OLD_CHROOT_PATH_CONF=$(grep "<chrootPath>" "$LSWS_HOME/conf/httpd_config.xml")
        OLD_ENABLE_CHROOT=$(expr "$OLD_ENABLE_CHROOT_CONF" : '.*<enableChroot>\(.*\)</enableChroot>.*')
        OLD_CHROOT_PATH=$(expr "$OLD_CHROOT_PATH_CONF" : '[^<]*<chrootPath>\([^<]*\)</chrootPath>.*')
        if [ -n "$OLD_ENABLE_CHROOT" ]; then
            ENABLE_CHROOT=$OLD_ENABLE_CHROOT
        fi
        if [ -n "$OLD_CHROOT_PATH" ]; then
            CHROOT_PATH=$OLD_CHROOT_PATH
        fi
    fi
    CHANGE_CHROOT=0
    if [ "$INST_USER" = "root" ]; then
        CHANGE_CHROOT=1

            if [ "$INSTALL_TYPE" = "upgrade" ]; then
            CHANGE_CHROOT=0
            if [ "$ENABLE_CHROOT" -eq 1 ]; then
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
            if [ -n "$TMP_URC" ]; then
                if [ "$(expr "$TMP_URC" : '[Yy]')" -gt 0 ]; then
                    CHANGE_CHROOT=1
                fi
            fi
        fi        

        if [ "$CHANGE_CHROOT" -eq 1 ]; then

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
            if [ -n "$TMP_YN" ] && [ "$(expr "$TMP_YN" : '[Yy]')" -gt 0 ]; then
                ENABLE_CHROOT=1
            fi

            # shellcheck disable=SC2034
            LSWS_HOME_LEN=$(expr "$LSWS_HOME" : '.*')
            # NOTE: LSWS_HOME_LEN is intentionally computed here and used by
            # functions.sh and chroot path matching routines.
            if [ "$ENABLE_CHROOT" -eq 1 ]; then
                while [ "$SUCC" -eq 0 ]; do
                    cat <<EOF

Chroot path must be absolute path and the server root 
    $LSWS_HOME
must be included in the chroot directory tree.

EOF
                    printf "%s" "Chroot directory without trailing '/': "
                    TMP_CHROOT='n'
                    if [ -n "$TMP_CHROOT" ]; then
                        if [ "$TMP_CHROOT" = '/' ]; then
                            echo "Set chroot directory to '/' will disable chroot."
                            printf "%s" "Are you sure? [y/N]"
                            read -r TMP_YN
                                    if [ -n "$TMP_YN" ] && [ "$(expr "$TMP_YN" : '[Yy]')" -gt 0 ]; then
                                        ENABLE_CHROOT=0
                                SUCC=1
                            fi
                        else
                            CHROOT_LEN=$(expr "$TMP_CHROOT" : '.*')
                            MATCH_LEN=$(expr "$LSWS_HOME" : "$TMP_CHROOT")
                            if [ "$CHROOT_LEN" -ne "$MATCH_LEN" ]; then
                                echo "Server root is not included in the chroot directory tree"
                            else
                                TMP_CHROOT2="$TMP_CHROOT/"
                                TMP_HOME="$LSWS_HOME/"
                                MATCH_LEN=$(expr "$TMP_HOME" : "$TMP_CHROOT2")
                                if [ "$MATCH_LEN" -le "$CHROOT_LEN" ]; then
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
    util_cpfile "$SDIR_OWN" "$EXEC_MOD" admin/misc/chroot.sh 

    if [ "$CHANGE_CHROOT" -eq 1 ]; then

        if [ "$ENABLE_CHROOT" -eq 1 ]; then
              "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH"
                  "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH" "${LSWS_HOME}/bin/lshttpd"
              "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH" "${LSWS_HOME}/admin/fcgi-bin/admin_php5"
              "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH" "${LSWS_HOME}/bin/lscgid"
            if [ -f "$LSWS_HOME/fcgi-bin/php" ]; then
                  "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH" "${LSWS_HOME}/fcgi-bin/php"
            fi
              "${LSWS_HOME}/admin/misc/chroot.sh" "$CHROOT_PATH" "${LSWS_HOME}/fcgi-bin/lsphp"
            if [ "$(expr "$CHROOT_PATH" : '^/[^/]')" -gt 1 ]; then
                cp "$CHROOT_PATH/etc/passwd" "$CHROOT_PATH/etc/passwd.ls_bak"
                cp "$CHROOT_PATH/etc/group" "$CHROOT_PATH/etc/group.ls_bak"
                grep -E "$WS_USER|lsadm" /etc/passwd > "$CHROOT_PATH/etc/passwd"
                grep "$WS_GROUP" /etc/group > "$CHROOT_PATH/etc/group"
            fi
       fi
        cp "$LSWS_HOME/conf/httpd_config.xml" "$LSWS_HOME/conf/httpd_config.xml.bak"
        chown "$DIR_OWN" "$LSWS_HOME/conf/httpd_config.xml.bak"
       RES=$(grep '</chrootPath>' "$LSWS_HOME/conf/httpd_config.xml.bak")
        if [ -z "$RES" ]; then
            sed -e "s#</group>#</group><chrootPath>$CHROOT_PATH</chrootPath><enableChroot>$ENABLE_CHROOT</enableChroot>#" "$LSWS_HOME/conf/httpd_config.xml.bak" > "$LSWS_HOME/conf/httpd_config.xml"
        else
            sed -e "s#<chrootPath>.*<\/chrootPath>#<chrootPath>$CHROOT_PATH<\/chrootPath>#" -e "s/<enableChroot>.*<\/enableChroot>/<enableChroot>$ENABLE_CHROOT<\/enableChroot>/" "$LSWS_HOME/conf/httpd_config.xml.bak" > "$LSWS_HOME/conf/httpd_config.xml"
        fi
    fi
}

installLicense()
{
    if [ -f ./serial.no ]; then
        cp -f ./serial.no "$LSWS_HOME/conf"
        chown "$SDIR_OWN" "$LSWS_HOME/conf/serial.no"
        chmod "$DOC_MOD" "$LSWS_HOME/conf/serial.no"
    fi

    if [ -f ./license.key ]; then
        cp -f ./license.key "$LSWS_HOME/conf"
        chown "$SDIR_OWN" "$LSWS_HOME/conf/license.key"
        chmod "$CONF_MOD" "$LSWS_HOME/conf/license.key"
    fi

    if [ -f ./trial.key ]; then
        cp -f ./trial.key "$LSWS_HOME/conf"
        chown "$SDIR_OWN" "$LSWS_HOME/conf/trial.key"
        chmod "$DOC_MOD" "$LSWS_HOME/conf/trial.key"
    fi
}

portOffset()
{
SUCC=0
SEL=0
while [ "$SUCC" -eq 0 ]; do

    cat <<EOF

Would you like to run LiteSpeed along side with Apache on another port
to make sure everything work properly? If yes, please set "Port Offset"
to a non-zero value, LiteSpeed will run on Port 80 + "Port Offset",
otherwise, set to "0" to replace Apache. 

EOF
    printf "%s" "Port Offset [2000]? "
    TMPS=0
    echo ""
    if [ -n "$TMPS" ]; then
        if [ "$(expr "$TMPS" : '.*[^0-9]')" -gt 0 ]; then
            echo "[ERROR] Only digits is allowed, try again!"
        else
            # shellcheck disable=SC2034
            AP_PORT_OFFSET=$TMPS
            # NOTE: AP_PORT_OFFSET is consumed by functions.sh when building
            # config templates (sed replacements) to shift ports for Apache
            # compatibility; kept intentionally.
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
while [ "$SUCC" -eq 0 ]; do

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
            if [ -n "$TMPS" ]; then
        if [ "$(expr "$TMPS" : '[012]')" -gt 0 ]; then
            # shellcheck disable=SC2034
            PHP_SUEXEC=$TMPS
            # NOTE: PHP_SUEXEC is used later by buildApConfigFiles/buildConfigFiles
            # via templating and by functions.sh; leave defined here.
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
    # shellcheck disable=SC2034
    SETUP_PHP=1
    # NOTE: SETUP_PHP toggles PHP blocks in templating performed by
    # buildConfigFiles and is intentionally left defined here.
    portOffset
    enablePHPsuExec
}

hostPanels()
{

SUCC=0
SEL=0
while [ "$SUCC" -eq 0 ]; do

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
    if [ -n "$TMPS" ]; then
        if [ "$(expr "$TMPS" : '[01234567]')" -gt 0 ]; then
            SEL=$TMPS
            SUCC=1
            PANEL_VARY=""
            if [ "$SEL" -eq "1" ]; then
                HOST_PANEL="cpanel"
                WS_USER=nobody
                WS_GROUP=nobody
                if [ -e "/etc/cpanel/ea4/is_ea4" ] ; then
                    PANEL_VARY=".ea4"
                fi
            elif [ "$SEL" -eq "2" ]; then
                HOST_PANEL="directadmin"
                WS_USER=apache
                WS_GROUP=apache
            elif [ "$SEL" -eq "3" ]; then
                HOST_PANEL="plesk"
                USER_INFO=$(id apache 2>/dev/null)
                TST_USER=$(expr "$USER_INFO" : 'uid=.*(\(.*\)) gid=.*')
                if [ "$TST_USER" = "apache" ]; then
                    WS_USER=apache
                    WS_GROUP=apache
                else
                    WS_USER=www-data
                    WS_GROUP=www-data
			# default PID FILE, source the real one, debian and ubuntu different
            # shellcheck disable=SC2034
            APACHE_PID_FILE=/var/run/apache2/apache2.pid
            . /etc/apache2/envvars 2>/dev/null
            if ! . /etc/apache2/envvars 2>/dev/null; then
                . /etc/apache2/envvars
            fi
            # shellcheck disable=SC2034
            PANEL_VARY=".debian"
            # NOTE: PANEL_VARY modifies which panel-specific templates to use.
                fi
                # shellcheck disable=SC2034
                ADMIN_PORT=7088
                # NOTE: ADMIN_PORT may be adjusted for panel variants and is
                # referenced in admin config templating.
            elif [ "$SEL" -eq "4" ]; then
                HOST_PANEL="hsphere"
                WS_USER=httpd
                WS_GROUP=httpd
            elif [ "$SEL" -eq "5" ]; then
                HOST_PANEL="interworx"
                WS_USER=apache
                WS_GROUP=apache
            elif [ "$SEL" -eq "6" ]; then
                HOST_PANEL="lxadminh"
                WS_USER=apache
                WS_GROUP=apache
            elif [ "$SEL" -eq "7" ]; then
                HOST_PANEL="ispmanager"
                WS_USER=apache
                WS_GROUP=apache
            fi
        fi
        DIR_OWN=$WS_USER:$WS_GROUP
    # shellcheck disable=SC2034
    CONF_OWN=$WS_USER:$WS_GROUP
    # NOTE: CONF_OWN is used when copying/chowning config files by functions.sh
    else
        SUCC=1
    fi
done

}


LSINSTALL_DIR=$(dirname "$0")
cd "$LSINSTALL_DIR" || exit 1

init
license
install_dir
test_license
admin_login


if [ "$INSTALL_TYPE" = "reinstall" ]; then

    configAdminEmail
    if [ "$INST_USER" = "root" ]; then
       hostPanels
    fi
    if [ -z "$HOST_PANEL" ]; then
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

if [ -z "$HOST_PANEL" ]; then
    configChroot
fi

cat <<EOF

Installing, please wait...

EOF

if [ "$HOST_PANEL" = "directadmin" ]; then
    chmod g+x /var/log/httpd/
    chgrp apache /var/log/httpd/
    chown apache:apache /var/log/httpd/domains
fi

if [ -z "$HOST_PANEL" ]; then
    buildConfigFiles
else
    buildApConfigFiles
fi

installation

installLicense


if [ -z "$HOST_PANEL" ]; then
    changeChroot
#    setupPHPAccelerator
    installAWStats
fi


finish

