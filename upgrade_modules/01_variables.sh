#!/usr/bin/env bash
# CyberPanel upgrade – set default variables and paths.
# Sourced by cyberpanel_upgrade.sh.

Set_Default_Variables() {
  echo -e "Clearing old log files..."
  rm -f /var/log/cyberpanel_upgrade_debug.log
  rm -f /var/log/installLogs.txt
  rm -f /var/log/upgradeLogs.txt

  echo -e "\n\n========================================" > /var/log/cyberpanel_upgrade_debug.log
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting CyberPanel Upgrade Script" >> /var/log/cyberpanel_upgrade_debug.log
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Old log files have been cleared" >> /var/log/cyberpanel_upgrade_debug.log
  echo -e "========================================\n" >> /var/log/cyberpanel_upgrade_debug.log

  rm -Rfv /usr/local/CyberCP/configservercsf 2>/dev/null || true
  rm -fv /home/cyberpanel/plugins/configservercsf 2>/dev/null || true
  rm -Rfv /usr/local/CyberCP/public/static/configservercsf 2>/dev/null || true
  sed -i "/configservercsf/d" /usr/local/CyberCP/CyberCP/settings.py 2>/dev/null || true
  sed -i "/configservercsf/d" /usr/local/CyberCP/CyberCP/urls.py 2>/dev/null || true
  if [ ! -e /etc/cxs/cxs.pl ]; then
    sed -i "/configserver/d" /usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html 2>/dev/null || true
  fi

  export LC_CTYPE=en_US.UTF-8
  echo -e "\nFetching latest data from CyberPanel server...\n"
  echo -e "This may take few seconds..."

  Server_Country="Unknown"
  Server_OS=""
  Server_OS_Version=""
  Server_Provider='Undefined'

  Temp_Value=$(curl --silent --max-time 30 -4 https://cyberpanel.net/version.txt)
  Panel_Version=${Temp_Value:12:3}
  Panel_Build=${Temp_Value:25:1}

  Branch_Name="v${Panel_Version}.${Panel_Build}"
  Base_Number="1.9.3"

  Git_User=""
  Git_Content_URL=""
  Git_Clone_URL=""

  MySQL_Version=$(mariadb -V 2>/dev/null | grep -P '\d+.\d+.\d+' -o || mysql -V 2>/dev/null | grep -P '\d+.\d+.\d+' -o)
  MySQL_Password=$(cat /etc/cyberpanel/mysqlPassword 2>/dev/null || echo "")

  LSWS_Latest_URL="https://cyberpanel.sh/update.litespeedtech.com/ws/latest.php"
  LSWS_Tmp=$(curl --silent --max-time 30 -4 "$LSWS_Latest_URL" 2>/dev/null)
  LSWS_Stable_Line=$(echo "$LSWS_Tmp" | grep "LSWS_STABLE")
  LSWS_Stable_Version=$(expr "$LSWS_Stable_Line" : '.*LSWS_STABLE=\(.*\) BUILD .*')
  if [ -z "$LSWS_Stable_Version" ]; then
    LSWS_Stable_Version="6.3.4"
  fi

  Debug_Log2 "Starting Upgrade...1"

  rm -rf /root/cyberpanel_upgrade_tmp
  mkdir -p /root/cyberpanel_upgrade_tmp
  cd /root/cyberpanel_upgrade_tmp || exit
}
