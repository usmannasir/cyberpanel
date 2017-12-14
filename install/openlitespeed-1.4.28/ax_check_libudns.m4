#
# AC_LIBUDNS_CHECK
#
AC_DEFUN([AX_PATH_LIB_UDNS],[dnl
AC_MSG_CHECKING([lib udns])
UDNS_HOME=
AC_ARG_WITH(udns,
[  --with-udns=DIR root directory path of udns installation (defaults to
                    /usr/local or /usr if not found in /usr/local)],
[
    UDNS_HOME="$withval"
    if test ! -f "${UDNS_HOME}/include/udns.h"
    then
        AC_MSG_WARN([Sorry, $withval does not contains include/udns.h, checking usual places])
        UDNS_HOME=/usr/local
        if test ! -f "${UDNS_HOME}/include/udns.h"
        then
            UDNS_HOME=/usr
        fi
    fi
],
[
    UDNS_HOME=/usr/local
    if test ! -f "${UDNS_HOME}/include/udns.h"
    then
        UDNS_HOME=/usr
    fi
])
                    

UDNS_OLD_LDFLAGS=$LDFLAGS
UDNS_OLD_CPPFLAGS=$CPPFLAGS
LDFLAGS="$LDFLAGS -L${UDNS_HOME}/$OPENLSWS_LIBDIR"
CPPFLAGS="$CPPFLAGS -I${UDNS_HOME}/include"
AC_LANG_SAVE
AC_LANG_C
AC_CHECK_LIB(udns, dns_init, [udns_lib=yes], [udns_lib=no])
AC_CHECK_HEADER(udns.h, [udns_h=yes], [udns_h=no])
AC_LANG_RESTORE
if test "$udns_lib" = "yes" -a "$udns_h" = "yes"
then
    UDNS_LIBS="-ludns"
    UDNS_CFLAGS="-I${UDNS_HOME}/include"
    AC_MSG_CHECKING(udns in ${UDNS_HOME})
    AC_MSG_RESULT(ok)
    AC_MSG_RESULT([$UDNS_LIBS])
    m4_ifval($1,$1)
else
    LDFLAGS="$UDNS_OLD_LDFLAGS"
    CPPFLAGS="$UDNS_OLD_CPPFLAGS"
    AC_MSG_WARN([Cannot find udns, will try to build from source code])
    ./installudns.sh
    UDNS_HOME="`pwd`/udns-0.4/"
    echo UDNS_HOME is ${UDNS_HOME}
    
    LDFLAGS="$LDFLAGS -L${UDNS_HOME} "
    CPPFLAGS="$CPPFLAGS -I${UDNS_HOME} "
    echo UDNS location ${UDNS_HOME}, $LDFLAGS, $CPPFLAGS

    AC_LANG_SAVE
    AC_LANG_C
    unset ac_cv_lib_udns_dns_init
    unset ac_cv_header_udns_h
    AC_CHECK_LIB(udns, dns_init, [udns_lib=yes], [udns_lib=no])
    AC_CHECK_HEADER(udns.h, [udns_h=yes], [udns_h=no])
    AC_LANG_RESTORE
    if test "$udns_lib" = "yes" -a "$udns_h" = "yes"
    then
        UDNS_LIBS=" -ludns "
        UDNS_CFLAGS=" -I${UDNS_HOME} "
        AC_MSG_CHECKING(udns in ${UDNS_HOME})
        AC_MSG_RESULT(ok)
        AC_MSG_RESULT([$UDNS_LIBS])
        m4_ifval($1,$1)
    else
        AC_MSG_CHECKING(udns in ${UDNS_HOME})
        LDFLAGS="$UDNS_OLD_LDFLAGS"
        CPPFLAGS="$UDNS_OLD_CPPFLAGS"
        AC_MSG_RESULT(failed)
        AC_MSG_ERROR(Can not find and build udns library.)
        m4_ifval($2,$2)
    fi
fi


AC_SUBST([UDNS_LIBS])
AC_SUBST([UDNS_CFLAGS])
])
