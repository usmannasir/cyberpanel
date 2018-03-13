#
# AC_LIBLUA_CHECK
#
AC_DEFUN([AC_LIBLUA_CHECK],[

    if test "x$lua_dir" != "x"
    then
        LUA_INCLUDES="$lua_dir"
        save_CFLAGS="$CFLAGS"
        CFLAGS="$CFLAGS -I$lua_dir"
        save_CPPFLAGS="$CPPFLAGS"
        CPPFLAGS="$CPPFLAGS -I$lua_dir"
    else 
        save_CFLAGS="$CFLAGS"
        save_CPPFLAGS="$CPPFLAGS"
    fi

    AC_CHECK_HEADERS(lua.h lualib.h lauxlib.h,,
    [
        if test "x$lua_dir" != "x"
        then
            AC_MSG_ERROR([liblua header not found in directory specified in --with-lua])
        else
            if test "x$need_lua" = "xyes"
            then
                AC_MSG_ERROR(Header file lua.h not found.)
            else
                need_lua=no
            fi
        fi
    ])

    if test "x$need_lua" != "xno"
    then
        CFLAGS="$save_CFLAGS"
        CPPFLAGS="$save_CPPFLAGS"
        AC_SUBST(LUA_INCLUDES)
    fi
])