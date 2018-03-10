#!/bin/sh

CUR_DIR=`dirname "$0"`
cd $CUR_DIR
CUR_DIR=`pwd`

echo "Generating key pair for web console login page, please wait ..."
openssl genrsa -out key.pem 512

if [ "$?" -eq "0" ] ; then
    ../fcgi-bin/admin_php -q genjCryptionKeyPair.php key.pem
   rm -f key.pem 
else
    ../fcgi-bin/admin_php -q genjCryptionKeyPair.php
fi


