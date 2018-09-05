#!/bin/sh
cd `dirname "$0"`
if [[ $1 != "-xml" ]] && [[ $1 != "-plain" ]] 
then
    echo 
    echo This script is used to swtich between using XML configuration and using plain text configuration.
    echo "Usage:  $0   <-xml | -plain>"
    echo 
    exit 1
fi


echo
if [ $1 = "-xml" ]
then
	if [ -f httpd_config.xml ]
	then
		echo It is XML configuration mode, no need to switch.
	else
		if [ -f httpd_config.xml.backup ]
		then
			mv httpd_config.xml.backup httpd_config.xml
			if [ -f httpd_config.xml ]
			then
				echo XML configuration mode will be used after restart webserver.
				
                                printf "Would you like to restart the web server now? [Y/n]"
                                read TMP_YN
                                echo ""
                                if [ "x$TMP_YN" = "x" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
                                  ../bin/lswsctrl restart
                                  sleep 1
                                  echo Done!
                                fi
			else
				echo Failed to rename httpd_config.xml.backup to httpd_config.xml, check permission and do it again.
			fi
		else
			echo httpd_config.xml.backup not exist, can not switch to use XML configuration mode.
		fi
	fi
	
### Below is start to check -plain
else
	if [ -f httpd_config.conf ]
	then
		if [ -f httpd_config.xml ]
		then
			mv httpd_config.xml httpd_config.xml.backup
			if [ -f httpd_config.xml ]
                        then
                                echo Failed to rename httpd_config.xml to httpd_config.xml.backup, check permission and do it again.
			else
				echo Plain text configueration file will be used after restart webserver.

				printf "Would you like to restart the web server now? [Y/n]"
				read TMP_YN
				echo ""
				if [ "x$TMP_YN" = "x" ] || [ `expr "$TMP_YN" : '[Yy]'` -gt 0 ]; then
                                  ../bin/lswsctrl restart
                                  sleep 1
                                  echo Done!
                                fi
                        fi
        else
			echo It is plain text configueration mode, no need to switch.
		fi
	else
		echo httpd_config.conf not exist, can not switch to use plain text configueration.
	fi
fi

echo





