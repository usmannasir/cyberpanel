
# ===========================================================================
#     http://www.gnu.org/software/autoconf-archive/ax_check_openssl.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_CHECK_OPENSSL([action-if-found[, action-if-not-found]])
#
# DESCRIPTION
#
#   Look for OpenSSL in a number of default spots, or in a user-selected
#   spot (via --with-openssl).  Sets
#
#     OPENSSL_INCLUDES to the include directives required
#     OPENSSL_LIBS to the -l directives required
#     OPENSSL_LDFLAGS to the -L or -R flags required
#
#   and calls ACTION-IF-FOUND or ACTION-IF-NOT-FOUND appropriately
#
#   This macro sets OPENSSL_INCLUDES such that source files should use the
#   openssl/ directory in include directives:
#
#     #include <openssl/hmac.h>
#
# LICENSE
#
#   Copyright (c) 2009,2010 Zmanda Inc. <http://www.zmanda.com/>
#   Copyright (c) 2009,2010 Dustin J. Mitchell <dustin@zmanda.com>
#
#   Copying and distribution of this file, with or without modification, are
#   permitted in any medium without royalty provided the copyright notice
#   and this notice are preserved. This file is offered as-is, without any
#   warranty.

#serial 8

AU_ALIAS([CHECK_SSL], [AX_CHECK_OPENSSL])
AC_DEFUN([AX_CHECK_OPENSSL], [
    AC_ARG_WITH([openssl],
        [AS_HELP_STRING([--with-openssl=DIR],
            [root of the OpenSSL directory])],
        [
            case "$withval" in
            "" | y | ye | yes | n | no)
            AC_MSG_ERROR([Invalid --with-openssl value])
              ;;
            *) ssldirs="$withval"
              ;;
            esac
        ], [
            # use some default ssldirs
            ssldirs="/usr/local /usr/local/ssl /usr /usr/ssl /usr/lib/ssl /usr/pkg "
        ]
        )


    # note that we #include <openssl/foo.h>, so the OpenSSL headers have to be in
    # an 'openssl' subdirectory

    OPENSSL_INCLUDES=
    for ssldir in $ssldirs; do
    AC_MSG_CHECKING([for openssl/ssl.h in $ssldir])
        if test -f "$ssldir/include/openssl/ssl.h"; then
            OPENSSL_INCLUDES="-I$ssldir/include"
            OPENSSL_LDFLAGS="$ssldir/$OPENLSWS_LIBDIR"
            OPENSSL_LIBS="-lssl -lcrypto"
            AC_MSG_RESULT([yes])
            break
         else
            AC_MSG_RESULT([no])
        fi
    done


    # try the preprocessor and linker with our new flags,
    # being careful not to pollute the global LIBS, LDFLAGS, and CPPFLAGS

    AC_MSG_CHECKING([whether compiling and linking against OpenSSL works])
    echo "Trying link with OPENSSL_LDFLAGS=$OPENSSL_LDFLAGS;" \
        "OPENSSL_LIBS=$OPENSSL_LIBS; OPENSSL_INCLUDES=$OPENSSL_INCLUDES" >&AS_MESSAGE_LOG_FD

    save_LIBS="$LIBS"
    save_LDFLAGS="$LDFLAGS"
    save_CPPFLAGS="$CPPFLAGS"
    LDFLAGS="-L$OPENSSL_LDFLAGS $LDFLAGS"
    if test "$OPENLSWS_DISABLE_RPATH" = "no" ; then
        LDFLAGS="$LDFLAGS -Wl,-rpath,$OPENSSL_LDFLAGS"
    fi
    
    LIBS="$OPENSSL_LIBS $LIBS"
    CPPFLAGS="$OPENSSL_INCLUDES $CPPFLAGS"
    AC_LINK_IFELSE(
        [AC_LANG_PROGRAM([#include <openssl/ssl.h>], [SSL_new(NULL)])],
        [
            AC_MSG_RESULT([yes])
            $1
        ], [
            AC_MSG_RESULT([no])
            
            # when fail, add -ldl and try again 
            echo "Add -ldl and try test linking again..."
            LDFLAGS="-ldl $LDFLAGS"
            AC_LINK_IFELSE(
            [AC_LANG_PROGRAM([#include <openssl/ssl.h>], [SSL_new(NULL)])],
            [
                AC_MSG_RESULT([yes])
                $1
            ], [
                AC_MSG_RESULT([no])
                $2
            ])
        ])
        
        
    CPPFLAGS="$save_CPPFLAGS"
    # LDFLAGS="$OPENSSL_LDFLAGS $save_LDFLAGS"
    # LIBS="$save_LIBS"

    AC_SUBST([OPENSSL_INCLUDES])
    AC_SUBST([OPENSSL_LIBS])
    AC_SUBST([OPENSSL_LDFLAGS])
])
