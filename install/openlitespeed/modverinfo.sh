#! /bin/sh
#
# This script is to gather pre-defined modules version info
#
#

OS=`uname -s`
ALL_VER_INFO=
DEFINED_VALUE=
get_file_defined_value()
{
    DEFINED_VALUE=`grep "$2" "$1" | awk '{print substr($3,1,40)}' | tr -d '"' `
}

MODULESPACE=
if [ "x$OS" = "xLinux" ] ; then
    MODULESPACE="\n"
    get_file_defined_value src/modules/pagespeed/pagespeed.cpp "#define MODPAGESPEEDVERSION"
    ALL_VER_INFO="$ALL_VER_INFO\tmodpagespeed $DEFINED_VALUE$MODULESPACE"
fi


get_file_defined_value src/modules/cache/cache.cpp "#define MODULE_VERSION_INFO"
ALL_VER_INFO="$ALL_VER_INFO\tcache $DEFINED_VALUE$MODULESPACE"

get_file_defined_value src/modules/modinspector/modinspector.cpp "#define MODULE_VERSION_INFO"
ALL_VER_INFO="$ALL_VER_INFO\tmodinspector $DEFINED_VALUE$MODULESPACE"

get_file_defined_value src/modules/uploadprogress/uploadprogress.cpp "#define MODULE_VERSION_INFO"
ALL_VER_INFO="$ALL_VER_INFO\tuploadprogress $DEFINED_VALUE$MODULESPACE"


get_file_defined_value src/modules/modsecurity-ls/mod_security.cpp "#define VERSIONNUMBER"
ALL_VER_INFO="$ALL_VER_INFO\tmod_security $DEFINED_VALUE$MODULESPACE"



echo $ALL_VER_INFO

