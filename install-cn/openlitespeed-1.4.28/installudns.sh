#!/bin/sh

#Download udns source code and install it

# detect download method
DLCMD=
DL=`which wget`
if [ $? -eq 0 ] ; then
    DLCMD="wget -nv -O "
else
    DL=`which curl`
    if [ $? -eq 0 ] ; then
        DLCMD="curl -L -o "
    else
        if [ "x$OS" = "xFreeBSD" ] ; then
            DL=`which fetch`
            if [ $? -eq 0 ] ; then
                DLCMD="fetch -o "
            fi
        fi
    fi
fi

echo Will download stable version of the udns library 0.4 and install it
$DLCMD ./udns.tar.gz  http://www.corpit.ru/mjt/udns/udns-0.4.tar.gz
tar xf udns.tar.gz
cd udns-0.4/
./configure
make
cd ../

