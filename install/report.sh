#!/bin/sh
#
# Please paste the output of this script when asking for installation related support on CyberPanel Forum
# Link: https://forums.cyberpanel.net/
#

clear; clear
echo 
echo "Starting installation fault script"
echo Data: `date`
echo

echo "################################"

if [[ $(command -v wget) ]]; then
	echo "Wget is present"
else
	echo "Wget not found"
fi

echo "################################"
echo Total Ram: `free -h | awk 'NR==2 {print $2}'`
echo "Recommended: 1GB"
echo
echo "Disk Space"
df -h --total | tail -n 1
echo "################################"
echo
if [[ $(hostnamectl status | grep Virtualization) ]]; then
hostnamectl status | grep Virtualization | sed -e 's/^[ \t]*//'
else
echo "No virtualization found"
fi

# Operating System
echo
#
if  [[ $(hostnamectl status | grep "Operating System") ]]; then
hostnamectl status | grep "Operating System" | sed -e 's/^[ \t]*//'
else
echo "Unable to detect operating system"
fi

# Kernel
echo
#
if [[ $(uname -a) ]]; then
echo Kernel: `uname -a`
else
echo "Unable to detect kernel"
fi
echo
# 

echo "###########################"
echo
if [[ -d /usr/local/CyberCP ]]; then
	echo "CyberCP directory found"
else
	echo "CyberCP directory not found"
fi
echo
echo "###########################"

echo "Last 100 lines from installLogs.txt"

if [[ -f /usr/local/CyberCP/installLogs.txt ]]; then
	tail -n 100 /usr/local/CyberCP/installLogs.txt
elif [[ -f install/installLogs.txt ]]; then # Look for log file in cwd/install
	tail -n 100 install/installLogs.txt
elif [[ -f /var/log/installLogs.txt ]]; then
	tail -n 100 /var/log/installLogs.txt
elif [[ -f /usr/local/installLogs.txt ]]; then
	tail -n 100 /usr/local/installLogs.txt
else
	echo "Error log file not found"
fi
echo "###########################"
echo
echo "Gunicorn Status:"
if [[ $(systemctl status gunicorn | grep active) ]]; then
	echo "Gunicorn seems to be running"
else 
	echo "Seems like gunicorn isn't running. Printing status"
	systemctl status gunicorn
fi

echo 
echo "###########################"
