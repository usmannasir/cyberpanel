#! /bin/bash
# Cyberpanel Fix Perms
# https://gitlab.com/cyberpaneltoolsnscripts/cyberpanel-fixperms
# 
# Forked from https://github.com/PeachFlame/cPanel-fixperms
#

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
    echo "--account or -a: specify a Cyberpanel account"
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


# fix mailperms
fixmailperms () {
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
fixperms () {

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

    #Get the account's homedir
    HOMEDIR=$(egrep "^${account}:" /etc/passwd | cut -d: -f6)

    tput bold
    tput setaf 4
    echo "Fixing perms for $account:"
    tput setaf 3
    echo "------------------------"
    tput setaf 4
    echo "Fixing website files...."
    tput sgr0
    
    #Fix individual files in public_html
    find "$HOMEDIR"/public_html -type d -exec chmod $verbose 755 {} \;
    find "$HOMEDIR"/public_html -type f | xargs -d$'\n' -r chmod $verbose 644
    find "$HOMEDIR"/public_html -name '*.cgi' -o -name '*.pl' | xargs -r chmod $verbose 755
    #chown $verbose -R "$account":"$account" "$HOMEDIR"/public_html/*
    # Hidden files test support: https://serverfault.com/a/156481
    chown $verbose -R "$account":"$account" "$HOMEDIR"/public_html/.[^.]*
    find "$HOMEDIR"/* -name .htaccess -exec chown $verbose "$account"."$account" {} \;

    tput bold
    tput setaf 4
    echo "Fixing public_html...."
    tput sgr0
    #Fix perms of public_html itself
    chown $verbose "$account":"$account" "$HOMEDIR"/public_html
    chmod $verbose 755 "$HOMEDIR"/public_html

    tput bold
    tput setaf 4
    echo "Fixing logs...."
    tput sgr0
    #Fix perms of $HOMEDIR/logs
    chown $verbose nobody:"$account" "$HOMEDIR"/logs
    chmod $verbose 750 "$HOMEDIR"/logs
    find "$HOMEDIR"/logs/* -name '*.access_log' -exec chown $verbose nobody."$account" {} \;

    

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
      #find $SUBDOMAIN -type f | xargs -d$'\n' -r chmod $verbose 644
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

#Parses all users through Cyberpanel's users file
#all () {
#    for user in $(cut -d: -f1 /etc/domainusers)
#    do
#  fixperms "$user"
#    done
#}


all () {

if [[ $OS = 'CentOS Linux' ]] ; then
   for user in $(getent passwd | awk -F: '5001<$3 && $3<6000 {print $1}' |grep -v spamd)
    do
  fixperms "$user"
    done
   fixmailperms
fi

if [[ $OS = 'Ubuntu' ]] ; then
   for user in $(getent passwd | awk -F: '1001<$3 && $3<2000 {print $1}')
    do
  fixperms "$user"
    done
  fixmailperms
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