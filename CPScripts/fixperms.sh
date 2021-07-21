#!/usr/bin/env bash
## Author: Michael Ramsey
## Objective Fix permissions issues on CyberPanel/cPanel/Plesk for a linux user or users
# https://gitlab.com/wizardassistantscripts/fixperms
# 
# Forked from https://github.com/PeachFlame/cPanel-fixperms
#
# Plesk portion credits too
# https://www.orware.com/blog/tips-and-how-tos/plesk/correct-httpdocs-permissions
# https://support.plesk.com/hc/en-us/articles/115001969889--BUG-plesk-repair-fs-doesn-t-set-correct-owner-inside-httpdocs

## How to use.
# wget https://gitlab.com/wizardassistantscripts/fixperms/-/raw/master/fixperms.sh ; bash fixperms.sh username
# 
# wget https://gitlab.com/wizardassistantscripts/fixperms/-/raw/master/fixperms.sh ; bash fixperms.sh exampleuserbob
#
# Or once of
## bash <(curl -s https://gitlab.com/wizardassistantscripts/fixperms/-/raw/master/fixperms.sh || wget -qO - https://gitlab.com/wizardassistantscripts/fixperms/-/raw/master/fixperms.sh) exampleuserbob;
#
# Permanent Install for reuse via the below
# wget -O /usr/bin/fixperms https://gitlab.com/wizardassistantscripts/fixperms/-/raw/master/fixperms.sh; chmod +x /usr/bin/fixperms;
#
# Then 
# fixperms -v -a Username
# fixperms -v -all
# Username=$1


#Detect Control panel
if [ -f /usr/local/cpanel/cpanel ]; then
    	# Cpanel check for /usr/local/cpanel/cpanel -V
    	ControlPanel="cpanel"
	#user_homedir="/home/${Username}"

	
elif [ -f /usr/bin/cyberpanel ]; then
    	# CyberPanel check /usr/bin/cyberpanel
    	ControlPanel="cyberpanel"
	#Get users homedir path
	#user_homedir=$(grep -E "^${Username}:" /etc/passwd | cut -d: -f6)	

elif [ -f /usr/local/psa/core.version ]; then
    	# Plesk check /usr/local/psa/core.version
    	ControlPanel="plesk"
	
	#Get users homedir path
	#user_homedir=$(grep -E "^${Username}:" /etc/passwd | cut -d: -f6)


else
	echo "Not able to detect Control panel. Unsupported Control Panel exiting now"
	   exit 1;
	fi
echo "=============================================================";	
echo "$ControlPanel Control Panel Detected"
echo "=============================================================";
echo "";



# Set verbose to null
verbose=""


#Print the help text
helptext () {
    tput bold
    tput setaf 2
    echo "Fix perms script help:"
    echo "Sets file/directory permissions to match suPHP and FastCGI schemes"
    echo "USAGE: fixperms [options] -a account_name"
    echo "-------"
    echo "Options:"
    echo "-h or --help: print this screen and exit"
    echo "-v: verbose output"
    echo "-all: run on all Cyberpanel accounts"
    echo "--account or -a: specify a Cyberpanel/cPanel/Plesk account"
#   echo "--domain or -d: specify a Cyberpanel domain"
    tput sgr0
    exit 0
}

#Detect OS
if [ -f /etc/os-release ]; then
    # freedesktop.org and systemd
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
elif type lsb_release >/dev/null 2>&1; then
    # linuxbase.org
    OS=$(lsb_release -si)
    VER=$(lsb_release -sr)
elif [ -f /etc/lsb-release ]; then
    # For some versions of Debian/Ubuntu without lsb_release command
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VER=$DISTRIB_RELEASE
elif [ -f /etc/debian_version ]; then
    # Older Debian/Ubuntu/etc.
    OS=Debian
    VER=$(cat /etc/debian_version)
elif [ -f /etc/SuSe-release ]; then
    # Older SuSE/etc.
    ...
elif [ -f /etc/redhat-release ]; then
    # Older Red Hat, CentOS, etc.
    ...
else
    # Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
    OS=$(uname -s)
    VER=$(uname -r)
fi



#### Cyberpanel Section

# fix mailperms
fixmailperms_cyberpanel () {
    tput bold
    tput setaf 4
    echo "Fixing mailperms...."
    tput sgr0
    #Fix perms of /home/vmail
    chown -R vmail:vmail /home/vmail
    chmod 755 /home/vmail
    find /home/vmail -type d -exec chmod 0755 {} \;
    find /home/vmail -type f -exec chmod 0640 {} \;
    echo "Finished fixing mailperms...."

}

# Main workhorse, fix perms per account passed to it
fixperms_cyberpanel () {

  #Get account from what is passed to the function
  account=$1

  #Make sure account isn't blank
  if [ -z "$account" ]
  then
    tput bold
    tput setaf 1
    echo "Need an account name!"
    tput sgr0
    helptext
  #Else, start doing work
  else

  # Get linux user from Domain
  domain_username=$(grep -E "/${1}:" /etc/passwd | cut -d: -f1)
  if id "$1" >/dev/null 2>&1; then
        echo "$1 exists"
  elif id "$domain_username" >/dev/null 2>&1; then
	echo "Found user: $domain_username from domain: $1"        
	echo "$domain_username exists"
	account=$domain_username
  else
        echo "user does not exist"
  fi


    #Get the account's homedir
    HOMEDIR=$(grep -E "^${account}:" /etc/passwd | cut -d: -f6)
    echo "User Homedirectory: ${HOMEDIR}"
    tput bold
    tput setaf 4
    echo "Fixing perms for $account:"
    tput setaf 3
    if [ -d "$HOMEDIR/.cagefs" ]; then
            chmod 775 "$HOMEDIR"/.cagefs
            chmod 700 "$HOMEDIR"/.cagefs/tmp
            chmod 700 "$HOMEDIR"/.cagefs/var
            chmod 777 "$HOMEDIR"/.cagefs/cache
            chmod 777 "$HOMEDIR"/.cagefs/run
     	fi
    echo "------------------------"
    tput setaf 4
    echo "Fixing website files...."
    tput sgr0

   
    #Fix individual files in public_html
    find "$HOMEDIR"/public_html -type d -exec chmod "$verbose" 755 {} \;
    find "$HOMEDIR"/public_html -type f -print0 | xargs -d$'\n' -r chmod "$verbose" 644
    find "$HOMEDIR"/public_html -name '*.cgi' -print0 -o -name '*.pl' | xargs -0 -r chmod "$verbose" 755
    chown $verbose -R "$account":"$account" "$HOMEDIR"/public_html/*
    # Hidden files test support: https://serverfault.com/a/156481
    chown "$verbose" -R "$account":"$account" "$HOMEDIR"/public_html/.[^.]*
    find "$HOMEDIR"/* -name .htaccess -exec chown "$verbose" "$account"."$account" {} \;

    tput bold
    tput setaf 4
    echo "Fixing public_html...."
    tput sgr0
    #Fix perms of public_html itself
    chown "$verbose" "$account":nobody "$HOMEDIR"/public_html
    chmod "$verbose" 755 "$HOMEDIR"/public_html

    tput bold
    tput setaf 4
    echo "Fixing logs...."
    tput sgr0
    #Fix perms of $HOMEDIR/logs
    chown "$verbose" nobody:"$account" "$HOMEDIR"/logs
    chmod "$verbose" 750 "$HOMEDIR"/logs
    find "$HOMEDIR"/logs/* -name '*.access_log' -exec chown "$verbose" nobody."$account" {} \;

    

    #Fix subdomains that lie outside of public_html
    #tput setaf 3
    #tput bold
    #echo "------------------------"
    #tput setaf 4
    #echo "Fixing any domains with a document root outside of public_html...."
    #for SUBDOMAIN in $(grep -i documentroot /var/cpanel/userdata/$account/* | grep -v '.cache\|_SSL' | awk '{print $2}' | grep -v public_html)
    #do
      #tput bold
      #tput setaf 4
      #echo "Fixing sub/addon domain document root $SUBDOMAIN...."
      #tput sgr0
      #find $SUBDOMAIN -type d -exec chmod $verbose 755 {} \;
      #find $SUBDOMAIN -type f -print0 | xargs -d$'\n' -r chmod $verbose 644
      #find $SUBDOMAIN -name '*.cgi' -o -name '*.pl' | xargs -r chmod $verbose 755
      #chown $verbose -R $account:$account $SUBDOMAIN
      #find $SUBDOMAIN -name .htaccess -exec chown $verbose $account.$account {} \;
    #done

  #Finished
    tput bold
    tput setaf 3
    echo "Finished!"
    echo "------------------------"
    printf "\n\n"
    tput sgr0
  fi

  return 0
}


#########cPanel 
# Main workhorse, fix perms per account passed to it
fixperms_cpanel () {

  #Get account from what is passed to the function
  account=$1

  #Check account against cPanel users file
  if ! grep "$account" /var/cpanel/users/*
  then
    tput bold
    tput setaf 1
    echo "Invalid cPanel account"
    tput sgr0
    exit 0
  fi

  #Make sure account isn't blank
  if [ -z "$account" ]
  then
    tput bold
    tput setaf 1
    echo "Need an account name!"
    tput sgr0
    helptext
  #Else, start doing work
  else

    #Get the account's homedir
    HOMEDIR=$(grep -E "^${account}:" /etc/passwd | cut -d: -f6)
    echo "User Homedirectory: ${HOMEDIR}"
    tput bold
    tput setaf 4
    echo "Fixing perms for $account:"
    tput setaf 3
    if [ -d "$HOMEDIR/.cagefs" ]; then
            chmod 775 "$HOMEDIR"/.cagefs
            chmod 700 "$HOMEDIR"/.cagefs/tmp
            chmod 700 "$HOMEDIR"/.cagefs/var
            chmod 777 "$HOMEDIR"/.cagefs/cache
            chmod 777 "$HOMEDIR"/.cagefs/run
     	fi
    echo "------------------------"
    tput setaf 4
    echo "Fixing website files...."
    tput sgr0
    


    #Fix individual files in public_html
    find "$HOMEDIR"/public_html -type d -exec chmod "$verbose" 755 {} \;
    find "$HOMEDIR"/public_html -type f -print0 | xargs -0 -d$'\n' -r chmod "$verbose" 644
    find "$HOMEDIR"/public_html -name '*.cgi' -print0 -o -name '*.pl' | xargs -0 -r chmod "$verbose" 755
    chown $verbose -R "$account":"$account" "$HOMEDIR"/public_html/*
    # fix hidden files and folders like .well-known/ with root or other user perms
    chown "$verbose" -R "$account":"$account" "$HOMEDIR"/public_html/.[^.]*
    find "$HOMEDIR"/* -name .htaccess -exec chown "$verbose" "$account"."$account" {} \;

    tput bold
    tput setaf 4
    echo "Fixing public_html...."
    tput sgr0
    #Fix perms of public_html itself
    chown "$verbose" "$account":nobody "$HOMEDIR"/public_html
    chmod "$verbose" 750 "$HOMEDIR"/public_html

    #Fix subdomains that lie outside of public_html
    tput setaf 3
    tput bold
    echo "------------------------"
    tput setaf 4
    echo "Fixing any domains with a document root outside of public_html...."
    for SUBDOMAIN in $(grep -i documentroot /var/cpanel/userdata/"$account"/* | grep -v '.cache\|_SSL' | awk '{print $2}' | grep -v public_html)
    do
      tput bold
      tput setaf 4
      echo "Fixing sub/addon domain document root $SUBDOMAIN...."
      tput sgr0
      find "$SUBDOMAIN" -type d -exec chmod "$verbose" 755 {} \;
      find "$SUBDOMAIN" -type f -print0 | xargs -0 -d$'\n' -r chmod "$verbose" 644
      find "$SUBDOMAIN" -name '*.cgi' -print0 -o -name '*.pl' | xargs -0 -r chmod "$verbose" 755
      chown "$verbose" -R "$account":"$account" "$SUBDOMAIN"
      chmod "$verbose" 755 "$SUBDOMAIN"
      find "$SUBDOMAIN" -name .htaccess -exec chown "$verbose" "$account"."$account" {} \;
    done

  #Finished
    tput bold
    tput setaf 3
    echo "Finished!"
    echo "------------------------"
    printf "\n\n"
    tput sgr0
  fi

  return 0
}

###################################





##################################

fixperms () {
	Username=$1
	if [ "${ControlPanel}" == "cpanel" ] ; then

	  	fixperms_cpanel "${Username}"
		# Fix users mailperms
		tput bold
    		tput setaf 4
    		echo "Fixing Mailperms...."
		tput sgr0
		/scripts/mailperm --verbose "${Username}"
		#Finished
		tput bold
		tput setaf 3
		echo "Finished!"
		echo "------------------------"
		printf "\n\n"
		tput sgr0

	elif [ "${ControlPanel}" == "cyberpanel" ] ; then

		fixperms_cyberpanel "${Username}"
		fixmailperms_cyberpanel


	elif [ "${ControlPanel}" == "plesk" ] ; then
		#Get users homedir path
		user_homedir=$(grep -E "^${Username}:" /etc/passwd | cut -d: -f6)
                echo "User Homedirectory: ${user_homedir}"
		echo "Resetting perms/ownership for ${user_homedir}/httpdocs"
		sudo chown -R "${Username}":psacln "${user_homedir}"/httpdocs
		sudo chown "${Username}":psaserv "${user_homedir}"/httpdocs	

	fi	
}

all () {

	if [ "${ControlPanel}" == "cpanel" ] ; then

		for user in $(cut -d: -f1 /etc/domainusers)
		    do
		  	fixperms_cpanel "$user"
		    done
		# Fix all users mailperms
		/scripts/mailperm --verbose

	elif [ "${ControlPanel}" == "cyberpanel" ] ; then

		if [[ $OS = 'CentOS Linux' ]] ; then
	   	for user in $(getent passwd | awk -F: '5001<$3 && $3<6000 {print $1}' |grep -v spamd)
		    do
		  	fixperms_cyberpanel "$user"
		    done
		   	fixmailperms_cyberpanel
		fi

		if [[ $OS = 'Ubuntu' ]] ; then
		   for user in $(getent passwd | awk -F: '1001<$3 && $3<2000 {print $1}')
		    do
		  	fixperms_cyberpanel "$user"
		    done
		  	fixmailperms_cyberpanel
		fi
	fi
}



#Main function, switches options passed to it
case "$1" in

    -h) helptext
  ;;
    --help) helptext
      ;;
    -v) verbose="-v"

  case "$2" in

    -all) all
           ;;
    --account) fixperms "$3"
         ;;
    -a) fixperms "$3"
        ;;
    *) tput bold
           tput setaf 1
       echo "Invalid Option!"
       helptext
       ;;
  esac
  ;;

    -all) all
    ;;
    --account) fixperms "$2"
          ;;
    -a) fixperms "$2"
  ;;
    *)
       tput bold
       tput setaf 1
       echo "Invalid Option!"
       helptext
       ;;
esac
