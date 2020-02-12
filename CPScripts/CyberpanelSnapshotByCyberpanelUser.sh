#!/bin/bash
## Author: Michael Ramsey
## Objective Find A Cyberpanel Users Domlogs Stats for last 5 days for all of their domains. v2
## https://gitlab.com/cyberpaneltoolsnscripts/snapshotbycyberpaneluser
## How to use.
# ./CyberpanelSnapshotByCyberpanelUser.sh username
#./CyberpanelSnapshotCyberpanelUser.sh exampleuserbob
#
##bash <(curl -s https://gitlab.com/cyberpaneltoolsnscripts/snapshotbycyberpaneluser/-/raw/master/CyberpanelSnapshotByCyberpanelUser.sh || wget -qO - https://gitlab.com/cyberpaneltoolsnscripts/snapshotbycyberpaneluser/-/raw/master/CyberpanelSnapshotByCyberpanelUser.sh) exampleuserbob;
##
Username=$1

#CURRENTDATE=$(date +"%Y-%m-%d %T") # 2019-02-09 06:47:56
#PreviousDay1=$(date --date='1 day ago' +"%Y-%m-%d")  # 2019-02-08
#PreviousDay2=$(date --date='2 days ago' +"%Y-%m-%d") # 2019-02-07
#PreviousDay3=$(date --date='3 days ago' +"%Y-%m-%d") # 2019-02-06
#PreviousDay4=$(date --date='4 days ago' +"%Y-%m-%d") # 2019-02-05

#datetimeDom=$(date +"%d/%b/%Y") # 09/Feb/2019
#datetimeDom1DaysAgo=$(date --date='1 day ago' +"%d/%b/%Y")  # 08/Feb/2019
#datetimeDom2DaysAgo=$(date --date='2 days ago' +"%d/%b/%Y") # 07/Feb/2019
#datetimeDom3DaysAgo=$(date --date='3 days ago' +"%d/%b/%Y") # 06/Feb/2019
#datetimeDom4DaysAgo=$(date --date='4 days ago' +"%d/%b/%Y") # 05/Feb/2019

#Domlog Date array for past 5 days
declare -a datetimeDomLast5_array=($(date +"%d/%b/%Y") $(date --date='1 day ago' +"%d/%b/%Y") $(date --date='2 days ago' +"%d/%b/%Y") $(date --date='3 days ago' +"%d/%b/%Y") $(date --date='4 days ago' +"%d/%b/%Y")); #for DATE in "${datetimeDomLast5_array[@]}"; do echo $DATE; done;

#Get users homedir path
user_homedir=$(sudo egrep "^${Username}:" /etc/passwd | cut -d: -f6)

#setup Domlogs/Accesslog path based off user_homedir/logs
domlogs_path="${user_homedir}/logs/"

Now=$(date +"%Y-%m-%d_%T")

user_CyberpanelSnapshot="${Username}-CyberpanelSnapshot_${Now}.txt";

#create logfile in user's homedirectory.
#sudo touch "$user_CyberpanelSnapshot"

#chown logfile to user
#sudo chown ${Username}:${Username} "$user_CyberpanelSnapshot";


main_function() {


echo ""
echo "Web Traffic Stats Check";

echo "";
for DATE in "${datetimeDomLast5_array[@]}"; do
echo "=============================================================";
echo "Apache Dom Logs POST Requests for ${DATE} for $Username";

	sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $1}' | cut -d: -f1|sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs GET Requests for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep GET | awk '{print $1}' | cut -d: -f1 |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs Top 10 bot/crawler requests per domain name for ${DATE}"
	sudo grep -r "$DATE" ${domlogs_path} | grep -Ei 'crawl|bot|spider|yahoo|bing|google'| awk '{print $1}' | cut -d: -f1|sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'| sort | uniq -c | sort -rn | head
	echo ""
	echo "HTTP Dom Logs top ten IPs for ${DATE} for $Username"

	command=$(sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $1}'|sed -e 's/^[^=:]*[=:]//' -e 's|"||g' | sort | uniq -c | sort -rn | head| column -t);readarray -t iparray < <( echo "${command}" | tr '/' '\n'); echo ""; for IP in "${iparray[@]}"; do echo "$IP"; done; echo ""; echo "Show unique IP's with whois IP, Country,and ISP"; echo ""; for IP in "${iparray[@]}"; do IP=$(echo "$IP" |grep -Eo '([0-9]{1,3}[.]){3}[0-9]{1,3}|(*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}))|:)))(%.+)?\s*)'); whois -h whois.cymru.com " -c -p $IP"|cut -d"|" -f 2,4,5|grep -Ev 'IP|whois.cymru.com'; done

	echo ""
	echo "Checking the IPs that Have Hit the Server Most and What Site they were hitting:"
	sudo grep -rs "$DATE" ${domlogs_path} | awk {'print $1'} |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log:/ /g'| sort | uniq -c | sort -n | tail -10| sort -rn| column -t
	echo ""
	echo "Checking the Top Hits Per Site Per IP:"
	sudo grep -rs "$DATE" ${domlogs_path} | awk {'print $1,$6,$7'} |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log:/ /g'| sort | uniq -c | sort -n | tail -15| sort -rn| column -t
	echo ""
	echo "Apache Dom Logs find the top number of uri's being requested for ${DATE}"
	sudo grep -r "$DATE" ${domlogs_path} | grep POST | awk '{print $7}' | cut -d: -f2 |sed "s|$domlogs_path||g"| sort | uniq -c | sort -rn | head| column -t
	echo ""
	echo "";
	echo "View Apache requests per hour for $Username";
	sudo grep -r "$DATE" ${domlogs_path} | cut -d[ -f2 | cut -d] -f1 | awk -F: '{print $2":00"}' | sort -n | uniq -c| column -t
	echo ""
	echo "CMS Checks"
	echo ""
	echo "Wordpress Checks"
	echo "Wordpress Login Bruteforcing checks for wp-login.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "wp-login.php|wp-admin.php" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress Cron wp-cron.php(virtual cron) checks for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep wp-cron.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress XMLRPC Attacks checks for xmlrpc.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep xmlrpc.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Wordpress Heartbeat API checks for admin-ajax.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep admin-ajax.php| cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'} | sort | uniq -c | sort -n|tail| sort -rn;
	echo ""
	echo "CMS Bruteforce Checks"
	echo "Drupal Login Bruteforcing checks for user/login/ for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "user/login/" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Magento Login Bruteforcing checks for admin pages /admin_xxxxx/admin/index/index for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "admin_[a-zA-Z0-9_]*[/admin/index/index]" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Joomla Login Bruteforcing checks for admin pages /administrator/index.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "admin_[a-zA-Z0-9_]*[/admin/index/index]" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "vBulletin Login Bruteforcing checks for admin pages admincp for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "admincp" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Opencart Login Bruteforcing checks for admin pages /admin/index.php for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "/admin/index.php" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""
	echo "Prestashop Login Bruteforcing checks for admin pages /adminxxxx for ${DATE} for $Username"
	sudo grep -r "$DATE" ${domlogs_path} | grep -E "/admin[a-zA-Z0-9_]*$" | cut -f 1 -d ":" |sed -e "s|$domlogs_path||g" -e 's|"||g' -e 's/.access_log//g'|awk {'print $1,$6,$7'}  | sort | uniq -c | sort -n|tail| sort -rn
	echo ""


done;
echo "============================================================="


echo "Contents have been saved to ${user_CyberpanelSnapshot}"
}

# log everything, but also output to stdout
main_function 2>&1 | tee -a "${user_CyberpanelSnapshot}"