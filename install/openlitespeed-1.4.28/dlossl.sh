#
# This script is to download openssl latest stable and make the static library ready
# Or,
# Use your pre-built boringSSL
#! /bin/sh

if [ "x$1" = "xuse_bssl" ] ; then 
    if [ "x$2" != "x" ] ; then 
        mkdir ssl
        cp $2/build/ssl/libssl.a           ssl/
        cp $2/build/crypto/libcrypto.a     ssl/
        cp $2/build/decrepit/libdecrepit.a ssl/
        cp -r $2/include/                  ssl/
    fi
    
    if [ ! -f ssl/libcrypto.a ] ; then
        echo -e "\033[38;5;148mError: boringSSL libraries not found.\033[39m"
    else
        echo -e "\033[38;5;148mOK, boringSSL libraries copied.\033[39m"
    fi
    exit 0;
fi

VERSION=OpenSSL_1_0_2-stable

#a bug fix of openssl 1.0.2
fixbug()
{
    sed -i -e "s/], s->s3->wpend_tot/], len - tot/" ssl/s3_pkt.c
}


cd `dirname "$0"`
echo "Checking openssl ..."

if [ ! -f ssl/libcrypto.a ] ; then
    echo -e "\033[38;5;148mDownload openssl $VERSION and building, it will take several minutes ...\033[39m"

    DL=`which curl`
    DLCMD="$DL -k -L -o ossl.tar.gz"
    $DLCMD https://github.com/openssl/openssl/archive/$VERSION.tar.gz
    tar xf ossl.tar.gz
    rm -rf ssl
    mv openssl-$VERSION ssl
    rm ossl.tar.gz
    cd ssl
    fixbug
    ./config
    make depend
    make
    
    if [ ! -f libcrypto.a ] ; then
        echo -e "\033[38;5;148mError: failed to make openssl libraries.\033[39m"
        exit 1
    else
        echo -e "\033[38;5;148mOK, openssl libraries made.\033[39m"
    fi
    cd ..
else
    echo "openssl libraries exists."
    exit 0
fi

echo "OK, openssl libraries exists."
exit 0
