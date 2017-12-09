#
# AC_IP2LOCATION_CHECK
#
AC_DEFUN([AC_IP2LOCATION_CHECK],[

    if test "x$ip2location_dir" != "x"
    then
        IP2LOCATION_INCLUDES="$ip2location_dir"
        save_CFLAGS="$CFLAGS"
        CFLAGS="$CFLAGS -I$ip2location_dir"
        save_CPPFLAGS="$CPPFLAGS"
        CPPFLAGS="$CPPFLAGS -I$ip2location_dir"
    else 
        save_CFLAGS="$CFLAGS"
        save_CPPFLAGS="$CPPFLAGS"
    fi

    AC_CHECK_HEADERS(IP2Location.h IP2Loc_DBInterface.h ,,
    [
        if test "x$ip2location_dir" != "x"
        then
            AC_MSG_ERROR([IP2Location header not found in directory specified in --with-ip2loc])
        else
            if test "x$need_ip2location" = "xyes"
            then
                AC_MSG_ERROR(Header file IP2Location.h not found.)
            else
                need_ip2location=no
            fi
        fi
    ])

    if test "x$need_ip2location" != "xno"
    then
        IP2LOCATION_LIBS="-lIP2Location"
        CFLAGS="$save_CFLAGS"
        CPPFLAGS="$save_CPPFLAGS"
        AC_SUBST(IP2LOCATION_INCLUDES)
        AC_SUBST([IP2LOCATION_LIBS])

    fi
])
