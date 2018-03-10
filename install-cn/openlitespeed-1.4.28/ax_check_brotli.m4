#
# AC_BROTLI_CHECK
#
AC_DEFUN([AC_BROTLI_CHECK],[

    if test "x$brotli_dir" != "x"
    then
        BROTLI_INCLUDES="$brotli_dir"
        save_CFLAGS="$CFLAGS"
        CFLAGS="$CFLAGS -I$brotli_dir"
        save_CPPFLAGS="$CPPFLAGS"
        CPPFLAGS="$CPPFLAGS -I$brotli_dir"
    else 
        save_CFLAGS="$CFLAGS"
        save_CPPFLAGS="$CPPFLAGS"
    fi

    AC_CHECK_HEADERS(brotli/encode.h brotli/decode.h ,,
    [
        if test "x$brotli_dir" != "x"
        then
            AC_MSG_ERROR([brotli header not found in directory specified in --with-brotli])
        else
            if test "x$need_brotli" = "xyes"
            then
                AC_MSG_ERROR(Header file brotli/encode.h not found.)
            else
                need_brotli=no
            fi
        fi
    ])

    if test "x$need_brotli" != "xno"
    then
        BROTLI_LIBS="-lbrotlidec -lbrotlienc -lbrotlicommon"
        CFLAGS="$save_CFLAGS"
        CPPFLAGS="$save_CPPFLAGS"
        AC_SUBST(BROTLI_INCLUDES)
        AC_SUBST([BROTLI_LIBS])

    fi
])
