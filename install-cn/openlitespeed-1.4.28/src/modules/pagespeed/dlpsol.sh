#
# This script is to download PSOL and extract it to right location
#
#
#! /bin/sh

cd `dirname "$0"`

if [ ! -f psol/include/out/Release/obj/gen/net/instaweb/public/version.h ] ; then

    DL=`which curl`
    DLCMD="$DL -O -k "
    TARGET=1.11.33.3.tar.gz
    $DLCMD https://dl.google.com/dl/page-speed/psol/$TARGET  
    tar -xzvf $TARGET # expands to psol/
    rm $TARGET

    #make symbolic links for code browsing
    ln -sf psol/include/net/ net
    ln -sf psol/include/out/ out
    ln -sf psol/include/pagespeed/ pagespeed
    ln -sf psol/include/third_party/ third_party
    ln -sf psol/include/third_party/chromium/src/base/ base
    ln -sf psol/include/third_party/chromium/src/build/ build
    ln -sf psol/include/third_party/css_parser/src/strings strings

    #fix a file which stop the compiling of pagespeed module
    
    cat << EOF > psol/include/pagespeed/kernel/base/scoped_ptr.h
/**
* Due the compiling issue, this file was updated from the original file.
*/
#ifndef PAGESPEED_KERNEL_BASE_SCOPED_PTR_H_
#define PAGESPEED_KERNEL_BASE_SCOPED_PTR_H_
#include "base/memory/scoped_ptr.h"

namespace net_instaweb {
template<typename T> class scoped_array : public scoped_ptr<T[]> {
public:
    scoped_array() : scoped_ptr<T[]>() {}
    explicit scoped_array(T* t) : scoped_ptr<T[]>(t) {}
};
}
#endif

EOF
    
fi
cd -

