#
# This script is to gather pre-defined modules version info
#
#
#! /bin/sh

OS=`uname -s`
ALL_VER_INFO=
DEFINED_VALUE=
get_file_defined_value()
{
    DEFINED_VALUE=`grep $2 $1 | grep -v "," | awk '{print substr($3,1,40)}' | tr -d '"' `
}

MODULESPACE=
if [ "x$OS" = "xLinux" ] ; then
    MODULESPACE="\n"
    get_file_defined_value src/modules/pagespeed/pagespeed.h MODULE_VERSION_INFO
    ALL_VER_INFO="$ALL_VER_INFO\tmodpagespeed $DEFINED_VALUE$MODULESPACE"
fi


get_file_defined_value src/modules/cache/cache.cpp MODULE_VERSION_INFO
ALL_VER_INFO="$ALL_VER_INFO\tcache $DEFINED_VALUE$MODULESPACE"

get_file_defined_value src/modules/modinspector/modinspector.cpp MODULE_VERSION_INFO
ALL_VER_INFO="$ALL_VER_INFO\tmodinspector $DEFINED_VALUE$MODULESPACE"

get_file_defined_value src/modules/uploadprogress/uploadprogress.cpp MODULE_VERSION_INFO
ALL_VER_INFO="$ALL_VER_INFO\tuploadprogress $DEFINED_VALUE$MODULESPACE"

echo $ALL_VER_INFO

