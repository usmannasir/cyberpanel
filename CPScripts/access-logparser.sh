#!/bin/bash
## Author: Michael Ramsey
## Objective Find A Cyberpanel/cPanel Users Dom/Access logs Stats for last 5 days for all of their domains. v2
## https://gitlab.com/mikeramsey/access-log-parser
## How to use.
# ./access-logparser.sh username
#./access-logparser.sh exampleuserbob
#
##bash <(curl -s https://gitlab.com/mikeramsey/access-log-parser/-/raw/master/access-logparser.sh || wget -qO - https://gitlab.com/mikeramsey/access-log-parser/-/raw/master/access-logparser.sh) exampleuserbob;
##
Username=$1

#Detect Control panel
if [ -f /usr/local/cpanel/cpanel ]; then
    	# Cpanel check for /usr/local/cpanel/cpanel -V
    	ControlPanel="cpanel"
	datetimeDcpumon=$(date +"%Y/%b/%d") # 2019/Feb/15
	#Current Dcpumon file
	DcpumonCurrentLOG="/var/log/dcpumon/${datetimeDcpumon}" # /var/log/dcpumon/2019/Feb/15
	#Setup datetimeDcpumonLast5_array
	declare -a datetimeDcpumonLast5_array=($(date +"%Y/%b/%d") $(date --date='1 day ago' +"%Y/%b/%d") $(date --date='2 days ago' +"%Y/%b/%d") $(date --date='3 days ago' +"%Y/%b/%d") $(date --date='4 days ago' +"%Y/%b/%d")); #for DATE in "${datetimeDcpumonLast5_array[@]}"; do echo $DATE; done;

	user_homedir="/home/${Username}"
	user_accesslogs="/home/${Username}/logs/"
	domlogs_path="/usr/local/apache/domlogs/${Username}/"
	acesslog_sed="-ssl_log"
	
elif [ -f /usr/bin/cyberpanel ]; then
    	# CyberPanel check /usr/bin/cyberpanel
    	ControlPanel="cyberpanel"
	
	#Get users homedir path
	user_homedir=$(sudo egrep "^${Username}:" /etc/passwd | cut -d: -f6)	
	domlogs_path="${user_homedir}/logs/"
	acesslog_sed=".access_log"

else
	echo "Not able to detect Control panel. Unsupported Control Panel exiting now"
	   exit 1;
	fi
echo "=============================================================";	
echo "$ControlPanel Control Panel Detected"
echo "User Homedirectory: ${user_homedir}"
echo "User Domlogs Path: ${domlogs_path}"
echo "=============================================================";
echo "";
#Domlog Date array for past 5 days
declare -a datetimeDomLast5_array=($(date +"%d/%b/%Y") $(date --date='1 day ago' +"%d/%b/%Y") $(date --date='2 days ago' +"%d/%b/%Y") $(date --date='3 days ago' +"%d/%b/%Y") $(date --date='4 days ago' +"%d/%b/%Y")); #for DATE in "${datetimeDomLast5_array[@]}"; do echo $DATE; done;


Now=$(date +"%Y-%m-%d_%T")

user_Snapshot="${Username}-Snapshot_${Now}.txt";

#create logfile in user's homedirectory.
#sudo touch "$user_CyberpanelSnapshot"

#chown logfile to user
#sudo chown ${Username}:${Username} "$user_CyberpanelSnapshot";


main_function() {

if [ "${ControlPanel}" == "cpanel" ] ;

then
  	for DATE in "${datetimeDcpumonLast5_array[@]}"; do 
	echo "=============================================================";
	echo "Find $Username user's highest CPU use processes via Dcpumon Logs for $DATE";
	sudo grep "$Username" /var/log/dcpumon/"${DATE}";
	done; echo "";
	echo "For more information about Dcpumon(Daily Process Logs) see https://docs.cpanel.net/whm/server-status/daily-process-log/82/"
	echo "=============================================================" 
	echo "";
	else
   	#echo "The DcpumonCurrentLOG '$DcpumonCurrentLOG' was not found. Not running Dcpumon stats" 
	echo "";
	fi

echo ""
echo "Web Traffic Stats Check";

echo "";
for DATE in "${datetimeDomLast5_array[@]}"; do
echo "=============================================================";
echo "HTTP Dom Logs POST Requests for ${DATE} for $Username";

	sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $1}' | cut -d: -f1|sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs GET Requests for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep GET | awk '{print $1}' | cut -d: -f1 |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs Top 10 bot/crawler requests per domain name for ${DATE}"
	sudo grep -r "$DATE" ${domlogs_path} | grep -Ei 'crawl|bot|spider|yahoo|bing|google'| awk '{print $1}' | cut -d: -f1|sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs top ten IPs for ${DATE} for $Username"

	command=$(sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $1}'|sed -e 's/^[^=:]*[=:]//' -e 's|"||g' | sort | uniq -c | sort -rn | head| column -t);readarray -t iparray < <( echo "${command}" | tr '/' '\n'); echo ""; for IP in "${iparray[@]}"; do echo "$IP"; done; echo ""; echo "Show unique IP's with whois IP, Country,and ISP"; echo ""; for IP in "${iparray[@]}"; do IP=$(echo "$IP" |grep -Eo '([0-9]{1,3}[.]){3}[0-9]{1,3}|(*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:)))(%.+)?\s*)'); whois -h whois.cymru.com " -c -p $IP"|cut -d"|" -f 2,4,5|grep -Ev 'IP|whois.cymru.com'; done

	echo ""
	echo "Checking the IPs that Have Hit the Server Most and What Site they were hitting:"
	sudo grep -rs "$DATE" ${domlogs_path} | awk {'print $1'} |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed:| |g"| sort | uniq -c | sort -n | tail -10| sort -rn| column -t
	echo ""
	echo "Checking the Top Hits Per Site Per IP:"
	sudo grep -rs "$DATE" ${domlogs_path} | awk {'print $1,$6,$7'} |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed:| |g"| sort | uniq -c | sort -n | tail -10| sort -rn| column -t
	echo ""
	echo "HTTP Dom Logs find the top number of uri's being requested for ${DATE}"
	sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $7}' | cut -d: -f2 |sed "s|$domlogs_path||g"| sort | uniq -c | sort -rn | head| column -t
	echo ""
	echo "";
	echo "View HTTP requests per hour for $Username";
	sudo grep -r "$DATE" ${domlogs_path} | cut -d[ -f2 | cut -d] -f1 | awk -F: '{print $2":00"}' | sort -n | uniq -c| column -t
	echo ""
	echo "CMS Checks"
	echo ""
	echo "Wordpress Checks"
	echo "Wordpress Login Bruteforcing checks for wp-login.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep wp-login.php | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress Cron wp-cron.php(virtual cron) checks for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep wp-cron.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress XMLRPC Attacks checks for xmlrpc.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep xmlrpc.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress Heartbeat API checks for admin-ajax.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep admin-ajax.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'} | sort | uniq -c | sort -n|tail| sort -rn;
	echo ""
	echo "CMS Bruteforce Checks"
	echo "Drupal Login Bruteforcing checks for user/login/ for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "user/login/" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Magento Login Bruteforcing checks for admin pages /admin_xxxxx/admin/index/index for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "admin_[a-zA-Z0-9_]*[/admin/index/index]" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Joomla Login Bruteforcing checks for admin pages /administrator/index.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "/administrator/index.php" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "vBulletin Login Bruteforcing checks for admin pages admincp for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "admincp" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Opencart Login Bruteforcing checks for admin pages /admin/index.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "/admin/index.php" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Prestashop Login Bruteforcing checks for admin pages /adminxxxx for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "/admin[a-zA-Z0-9_]*$" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e "s|$acesslog_sed||g" -e "s|$Username/||g"|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""


done;
echo "============================================================="


echo "Contents have been saved to ${user_Snapshot}"
}

# log everything, but also output to stdout
main_function 2>&1 | tee -a "${user_Snapshot}"
