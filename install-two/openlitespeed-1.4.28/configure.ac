m4_include(ax_check_zlib.m4)
m4_include(ax_check_openssl.m4)
m4_include(ax_path_lib_pcre.m4)
m4_include(ax_lib_expat.m4)
m4_include(ax_check_liblua.m4)
m4_include(ax_check_libudns.m4)
m4_include(ax_check_brotli.m4)
m4_include(ax_check_ip2location.m4)

dnl Process this file with autoconf to produce a configure script.
AC_PREREQ([2.69])
AC_INIT([openlitespeed],[1.4.28],[info@litespeedtech.com],[openlitespeed],[http://www.litespeedtech.com/])
AM_INIT_AUTOMAKE([1.0 foreign no-define ])

AM_CONFIG_HEADER(src/config.h:src/config.h.in)

dnl NOW change the default installation directory!
AC_PREFIX_DEFAULT('/usr/local/lsws')

# General "with" options
# ----------------------------------------------------------------------------
dnl Checks for programs.

AC_PROG_MAKE_SET
AC_PROG_INSTALL

# Checks for programs.
AC_PROG_AWK
AC_PROG_CXX
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_LN_S
AC_PROG_MAKE_SET
AC_PROG_RANLIB
LT_INIT

OSTYPE=`uname -m`
OSNAME=`uname -s`

# Checks for header files.
AC_CHECK_HEADER([pthread.h],
    [AC_CHECK_LIB([pthread],[pthread_join],[
        AC_DEFINE([HAVE_LIBPTHREAD],[],[Define if pthread (-lpthread)])
        AC_DEFINE([HAVE_PTHREAD_H],[],[Define if <pthread.h>])
       LIBS="-lpthread $LIBS"
    ])])
    
AC_CHECK_HEADERS(arpa/inet.h fcntl.h inttypes.h limits.h netdb.h netinet/in.h stddef.h stdlib.h string.h strings.h sys/ioctl.h sys/param.h sys/socket.h sys/time.h unistd.h)

AC_HEADER_ASSERT

## ##Set option --with-user
AC_ARG_WITH([user],
            AS_HELP_STRING([--with-user],[Set user name to run openlitespeed/lscpd [default: nobody]]),
            [OPENLSWS_USER="$withval"], [OPENLSWS_USER=nobody])
AC_DEFINE_UNQUOTED([OPENLSWS_USER], ["$OPENLSWS_USER"], [Defined the user name])
AC_SUBST([OPENLSWS_USER])

## ##Set option --with-group
AC_ARG_WITH([group],
            AS_HELP_STRING([--with-group],[Set group of the user [default: nobody]]),
            [OPENLSWS_GROUP="$withval"], [OPENLSWS_GROUP=nobody])
AC_DEFINE_UNQUOTED([OPENLSWS_GROUP], ["$OPENLSWS_GROUP"], [Defined the group of the user])
AC_SUBST([OPENLSWS_GROUP])

## ##Set option --with-admin
AC_ARG_WITH([admin],
            AS_HELP_STRING([--with-admin],[Set administrator user name [default: admin]]),
            [OPENLSWS_ADMIN="$withval"], [OPENLSWS_ADMIN=admin])
AC_SUBST([OPENLSWS_ADMIN])

## ##Set option --with-adminport
AC_ARG_WITH([adminport],
            AS_HELP_STRING([--with-adminport],[Set administrator listener port [default: 7080]]),
            [OPENLSWS_ADMINPORT="$withval"], [OPENLSWS_ADMINPORT=7080])
AC_SUBST([OPENLSWS_ADMINPORT])


## ##Set option --with-password
AC_ARG_WITH([password],
            AS_HELP_STRING([--with-password],[Set password of administrator [default: 123456]]),
            [OPENLSWS_PASSWORD="$withval"], [OPENLSWS_PASSWORD=123456])
AC_SUBST([OPENLSWS_PASSWORD])

## ##Set option --with-email
AC_ARG_WITH([email],
            AS_HELP_STRING([--with-email],[Set email of administrator [default: root@localhost]]),
            [OPENLSWS_EMAIL="$withval"], [OPENLSWS_EMAIL=root@localhost])
AC_SUBST([OPENLSWS_EMAIL])


AC_ARG_ENABLE([adminssl],
              [AC_HELP_STRING([--enable-adminssl=@<:@yes/no@:>@],
                              [Enable HTTPS for admin console (modify adminssl.conf before installation) @<:@default=yes@:>@])],
              [OPENLSWS_ADMINSSL="$enableval"], [OPENLSWS_ADMINSSL=yes])
AC_SUBST([OPENLSWS_ADMINSSL])

AC_ARG_WITH([exampleport],
            AS_HELP_STRING([--with-exampleport],[Set example listener port [default: 8088]]),
            [OPENLSWS_EXAMPLEPORT="$withval"], [OPENLSWS_EXAMPLEPORT=8088])
AC_SUBST([OPENLSWS_EXAMPLEPORT])




AC_ARG_WITH([lsphp7],
            AS_HELP_STRING([--with-lsphp7],[Set lsphp7 as default php script handler[default: yes]]),
            [USE_LSPHP7="$withval"], [USE_LSPHP7=no])

AC_ARG_WITH([tempdir],
            AS_HELP_STRING([--with-tempdir],[Set a customized temprary directory[default: /tmp/lshttpd]]),
            [DEFAULT_TMP_DIR="$withval"], [DEFAULT_TMP_DIR=/tmp/lshttpd])

AC_ARG_WITH([pidfile],
            AS_HELP_STRING([--with-pidfile],[Set a customized pid file path name[default: $DEFAULT_TMP_DIR/lshttpd.pid]]),
            [PID_FILE="$withval"], [PID_FILE=$DEFAULT_TMP_DIR/lshttpd.pid])

AC_ARG_WITH([lscpd],
            AS_HELP_STRING([--with-lscpd],[Set to build lscpd instead of openlitespeed[default: yes]]),
            [IS_LSCPD="$withval"], [IS_LSCPD=no])
echo IS_LSCPD=$IS_LSCPD
if test "$IS_LSCPD" = "yes" ; then
    DEFAULT_TMP_DIR=/tmp/lscpd
    PID_FILE=$DEFAULT_TMP_DIR/lscpd.pid
    USE_LSPHP7=yes
    OPENLSWS_ADMINSSL=no
    AC_DEFINE_UNQUOTED([IS_LSCPD], [1], [Defined to build lscpd])
    AC_SUBST([IS_LSCPD])
fi

AM_CONDITIONAL([BUILD_LSCPD], [test x$IS_LSCPD = xyes])
AC_DEFINE_UNQUOTED([DEFAULT_TMP_DIR], ["$DEFAULT_TMP_DIR"], [Defined the temprary directory])
AC_SUBST([DEFAULT_TMP_DIR])
AC_DEFINE_UNQUOTED([PID_FILE], ["$PID_FILE"], [Defined the pid file path])
AC_SUBST([PID_FILE])
AC_SUBST([USE_LSPHP7])
AC_SUBST([OPENLSWS_ADMINSSL])
echo "OPENLSWS_ADMINSSL=$OPENLSWS_ADMINSSL"
echo USE_LSPHP7=$USE_LSPHP7            
echo DEFAULT_TMP_DIR=$DEFAULT_TMP_DIR
echo PID_FILE=$PID_FILE


OPENLSWS_HTTP2="?"
AC_ARG_ENABLE([spdy],
              [AC_HELP_STRING([--enable-spdy=@<:@yes/no@:>@],
                              [Enable SPDY and http2 over HTTPS @<:@default=yes@:>@])],
               [OPENLSWS_HTTP2="$enableval"], [])

AC_ARG_ENABLE([http2],
              [AC_HELP_STRING([--enable-http2=@<:@yes/no@:>@],
                              [Enable SPDY and http2 over HTTPS @<:@default=yes@:>@])],
               [OPENLSWS_HTTP2="$enableval"], [])
if test "$OPENLSWS_HTTP2" = "no" ; then 
    echo "SPDY/http2 disabled!!!"
else
    AC_DEFINE([LS_ENABLE_SPDY], [1], [Define if need spdy/http2 feature]) 
    echo "SPDY/http2 enabled!!!"
fi


#AC_ARG_ENABLE([cacheredis],
#              [AC_HELP_STRING([--enable-redis],
#                              [Enable redis for cache module (Using redis is disabled by default)])],
#               [ AC_DEFINE([LS_ENABLE_REDIS], [1], [Define if cache module needs redis feature]) 
#                 echo "Cache redis enabled!!!" ], [])

AC_ARG_ENABLE([debug],
              [AC_HELP_STRING([--enable-debug],
                              [Enable debugging symbols (Debug is disabled by default)])],
              [OPENLSWS_DEBUG="$enableval"
                if test "$OPENLSWS_DEBUG" = "yes" ; then 
                    CFLAGS="-g3 -O0"
                    CXXFLAGS="-g3 -O0"
                else
                    CFLAGS="-g -O3"
                    CXXFLAGS="-g -O3"
                fi
                echo "OPENLSWS_DEBUG='$OPENLSWS_DEBUG'"
                ], [])
                
AC_ARG_ENABLE([profiling],
              [AC_HELP_STRING([--enable-profiling],
                              [Enable cpu profiling (profiling is disabled by default)])],
              [OPENLSWS_PROF="$enableval"
                if test "$OPENLSWS_PROF" = "yes" ; then 
                    CFLAGS="$CFLAGS -pg"
                    CXXFLAGS="$CXXFLAGS -pg"
                fi
                echo "OPENLSWS_PROF='$OPENLSWS_PROF'"
                ], [])                
                
dnl liblua check
AC_MSG_CHECKING(whether to compile mod_lua module)


AC_ARG_WITH(lua,
[  --with-lua[[=DIR]]        use liblua (located in directory DIR, if supplied) for compiling mod_lua module.  [[default=no]]],
[
    if test $withval = no
    then
        need_lua=no
    elif test $withval = yes
    then
        need_lua=yes
    else
        need_lua=yes
        lua_dir=$withval
    fi
],[
    need_lua=no
    lua_dir=
])
if test "x$need_lua" = "xno" ; then
    AC_MSG_RESULT(no)
else
    AC_MSG_RESULT(yes)
    AC_LIBLUA_CHECK
    if test "x$need_lua" = "xno" ; then
        AC_MSG_RESULT(liblua header files not found - disabling compile mod_lua module)
    fi
fi
AM_CONDITIONAL([HAVE_LIBLUA], [test x$need_lua = xyes])
echo "Lua inlcude = $LUA_INCLUDES, need_lua = $need_lua"    
                
CFLAGS="$CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -fstack-protector $(getconf LFS_CFLAGS) "
CXXFLAGS="$CXXFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -fstack-protector $(getconf LFS_CFLAGS) "

## ##Set option --with-bssl
AC_ARG_WITH(bssl,
            [  --with-bssl[[=DIR]]       Set to use BoringSSL instead of OpenSSL [[default=no]]],
            [
                if test $withval = no
                then
                    OPENLSWS_BSSL=no
                elif test $withval = yes
                then
                    OPENLSWS_BSSL=yes
                else
                    OPENLSWS_BSSL="$withval"
                fi
            ],[OPENLSWS_BSSL=no])
AC_SUBST([OPENLSWS_BSSL])

if test "$OPENLSWS_BSSL" = no ; then
    if test "$OSNAME" = Darwin ; then
        usedynossl=yes
        CPPFLAGS="$CPPFLAGS -I../../src -I../../include -I/usr/local/include -I/usr/local -I/usr -I/usr/pkg "
    else
        usedynossl=no
        CPPFLAGS="$CPPFLAGS -I../../ssl/include -I../../src -I../../include -I/usr/local/include -I/usr/local -I/usr -I/usr/pkg "
        echo "Will build latest stable openssl libraries for you, this may take several minutes ..."
        OSSL=`. $srcdir/dlossl.sh`
        echo "Finsihed building openssl."
    fi
    echo "Openssl: use_dyn_ossl = $usedynossl"
else
    #### Not provide location, use default location, will not copy files
    usedynossl=no
    AC_DEFINE_UNQUOTED([USE_BORINGSSL], [1], [Defined to use BoringSSL instead of OpenSSL])
    CPPFLAGS=" -I../../ssl/include $CPPFLAGS -I../../src -I../../include -I/usr/local/include -I/usr/local -I/usr -I/usr/pkg -DUSE_BORINGSSL=1 "
    if test "$OPENLSWS_BSSL" = yes ; then
        echo "Will use exist BoringSSL files in $srcdir/ssl/."
    else
        OSSL=`. $srcdir/dlossl.sh use_bssl "$OPENLSWS_BSSL"`
        echo "BoringSSL files copied to $srcdir/ssl/ from $OPENLSWS_BSSL."
    fi
    OPENLSWS_BSSL=yes
fi
AM_CONDITIONAL([USE_DYN_OSSL], [test x$usedynossl = xyes])
AM_CONDITIONAL([USE_BSSL], [test x$OPENLSWS_BSSL = xyes])

AC_ARG_WITH(brotli,
[  --with-brotli[[=DIR]]        enable brotli compression (located in directory DIR, if supplied).  [[default=no]]],
[
    if test "x$withval" = "x" ; then
        need_brotli=no
    elif test $withval = no ; then
        need_brotli=no
    elif test $withval = yes ; then
        need_brotli=yes
    else
        need_brotli=yes
        brotli_dir=$withval
    fi
],[
    need_brotli=no
    brotli_dir=
])
AC_SUBST([need_brotli])
AC_SUBST([brotli_dir])

AC_MSG_CHECKING(whether to check if brotli library exists)
if test "x$need_brotli" = "xno" ; then
    AC_MSG_RESULT(no)
else
    AC_MSG_RESULT(yes)
    AC_DEFINE_UNQUOTED([USE_BROTLI], [1], [Defined to compile with Brotli compression included])
    AC_BROTLI_CHECK
    if test "x$need_brotli" = "xno" ; then
        AC_MSG_RESULT(brotli header files not found - disabling brotli)
    elif test "x$need_brotli" = "xcheck" ; then
        need_brotli=yes
        AC_MSG_RESULT(brotli header files found - enable brotli)
    fi
fi
AM_CONDITIONAL([HAVE_BROTLI], [test x$need_brotli = xyes])
echo "Brotli include = $BROTLI_INCLUDES, need_brotli = $need_brotli"

AC_ARG_WITH(ip2loc,
[  --with-ip2loc[[=DIR]]        enable ip2location (located in directory DIR, if supplied).  [[default=no]]],
[
    if test "x$withval" = "x" ; then
        need_ip2location=no
    elif test $withval = no ; then
        need_ip2location=no
    elif test $withval = yes ; then
        need_ip2location=yes
    else
        need_ip2location=yes
        ip2location_dir=$withval
    fi
],[
    need_ip2location=no
    ip2location_dir=
])
AC_SUBST([need_ip2location])
AC_SUBST([ip2location_dir])

AC_MSG_CHECKING(whether to check if ip2location library exists)
if test "x$need_ip2location" = "xno" ; then
    AC_MSG_RESULT(no)
else
    AC_MSG_RESULT(yes)
    AC_DEFINE_UNQUOTED([USE_IP2LOCATION], [1], [Defined to compile with IP2Location included])
    AC_IP2LOCATION_CHECK
    if test "x$need_ip2location" = "xno" ; then
        AC_MSG_RESULT(ip2location header files not found - disabling ip2location)
    elif test "x$need_ip2location" = "xcheck" ; then
        need_ip2location=yes
        AC_MSG_RESULT(ip2location header files found - enable ip2location)
    fi
fi
AM_CONDITIONAL([HAVE_IP2LOCATION], [test x$need_ip2location = xyes])
echo "IP2Location include = $IP2LOCATION_INCLUDES, need_ip2location = $need_ip2location"

AC_ARG_ENABLE([rpath],
              [AC_HELP_STRING([--disable-rpath], 
                              [Disable rpath (It is 'no' by default)])],
              [OPENLSWS_DISABLE_RPATH=yes              
               echo "OPENLSWS_DISABLE_RPATH=yes"], [OPENLSWS_DISABLE_RPATH=no])                
AC_SUBST([OPENLSWS_DISABLE_RPATH])
               
AC_ARG_WITH([libdir],
            AS_HELP_STRING([--with-libdir],[Set system lib directory. It is lib or lib64 and will be automatically checked by default]),
            [OPENLSWS_LIBDIR="$withval"], [

                OPENLSWS_LIBDIR=lib
                if test "$OSNAME" = Linux ; then
                    if test "$OSTYPE" = x86_64 ; then
                        OPENLSWS_LIBDIR=lib64
                    elif test "$OSTYPE" = i686 ; then
               
                        CFLAGS="$CFLAGS -march=i686"
                        CXXFLAGS="$CXXFLAGS -march=i686"
                        elif test "$OSTYPE" = armv7l ; then
                       # Raspberry Pi 2, Scaleway C1, Parallella
                        CFLAGS="$CFLAGS -march=armv7"
                        CXXFLAGS="$CXXFLAGS -march=armv7"
                    elif test "$OSTYPE" = armv6l ; then
                       # Raspberry Pi (not Pi 2)
                        CFLAGS="$CFLAGS -march=armv6 -mfloat-abi=hard -mfpu=vfp"
                        CXXFLAGS="$CXXFLAGS -march=armv6 -mfloat-abi=hard -mfpu=vfp"
                        
                    fi
                fi
             ])
echo "Final CFLAGS='$CFLAGS' CXXFLAGS='$CXXFLAGS' CPPFLAGS='$CPPFLAGS'"
             
echo "Default system lib directory = $OPENLSWS_LIBDIR"
AC_SUBST([OPENLSWS_LIBDIR])


AX_CHECK_ZLIB(, AC_MSG_ERROR(Can not find zlib. You must install it before continuing.))


if test "$OSNAME" = Darwin ; then
    AX_CHECK_OPENSSL(, AC_MSG_ERROR(Can not find openssl. You must install it before continuing.))
fi

AX_PATH_LIB_PCRE(, AC_MSG_ERROR(Can not find pcre. You must install it before continuing.))
AX_PATH_LIB_UDNS(, AC_MSG_ERROR(Can not find udns library. You must install it before continuing.))

AX_LIB_EXPAT(0.5)
AC_CHECK_LIB([GeoIP], [GeoIP_id_by_addr])
AC_CHECK_LIB(crypt,crypt,LIBS="-lcrypt $LIBS")
      
      
# Checks for typedefs, structures, and compiler characteristics.
AC_CHECK_HEADER_STDBOOL
AC_TYPE_UID_T
AC_C_INLINE
AC_TYPE_INT16_T
AC_TYPE_INT32_T
AC_TYPE_INT8_T
AC_TYPE_MODE_T
AC_TYPE_OFF_T
AC_TYPE_PID_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT16_T
AC_TYPE_UINT32_T
AC_CHECK_TYPES(ptrdiff_t)

# Checks for library functions.
AC_FUNC_CHOWN
AC_FUNC_ERROR_AT_LINE
AC_FUNC_FORK
AC_FUNC_FSEEKO
AC_FUNC_LSTAT_FOLLOWS_SLASHED_SYMLINK
#AC_FUNC_MALLOC disable due to this replacing malloc() with non-existing rpl_malloc() issue on some systems
AC_FUNC_MMAP
AC_FUNC_REALLOC
AC_CHECK_FUNCS(malloc bzero dup2 ftruncate getcwd gethostbyaddr gethostbyname gettimeofday inet_ntoa localtime_r memchr memmove memset mkdir munmap select socket strcasecmp strchr strcspn strdup strerror strncasecmp strpbrk strrchr strspn strstr strtol)

RT_LIB_OPTION=" -lrt" 
DL_LIB_OPTION=" -ldl"
if test "$OSNAME" = Linux ; then
    LDFLAGS="$LDFLAGS -Wl,--export-dynamic"
fi

if test "$OSNAME" = FreeBSD ; then
    LDFLAGS="$LDFLAGS -Wl,--export-dynamic"
    DL_LIB_OPTION=
fi

#For Mac OS, add special falgs for LuaJit
if test "$OSNAME" = Darwin ; then
    LDFLAGS="$LDFLAGS -Wl,-export_dynamic -pagezero_size 10000 -image_base 100000000"
    RT_LIB_OPTION=
fi

LDFLAGS="$LDFLAGS $PCRE_LDFLAGS $UDNS_LDFLAGS -D_GLIBCXX_USE_CXX11_ABI=0"
echo "Final LDFLAGS='$LDFLAGS'"
AC_SUBST([DL_LIB_OPTION])
AC_SUBST([RT_LIB_OPTION])

MODULE_VERSION_INFO=`. $srcdir/modverinfo.sh`
AC_DEFINE_UNQUOTED([LS_MODULE_VERSION_INFO], ["$MODULE_VERSION_INFO"], [The pre-defined modules version info])

AC_CONFIG_FILES(Makefile
                src/Makefile
                src/edio/Makefile
                src/extensions/Makefile
                src/http/Makefile
                src/spdy/Makefile
                src/log4cxx/Makefile
                src/main/Makefile
                src/socket/Makefile
                src/sslpp/Makefile
                src/ssi/Makefile
                src/lsiapi/Makefile
                src/modules/Makefile
                src/shm/Makefile
                src/adns/Makefile
                src/modules/cache/Makefile
                src/modules/modinspector/Makefile
                src/modules/modreqparser/Makefile
                src/modules/uploadprogress/Makefile)
                
if test x$need_lua = xyes ; then
    AC_CONFIG_FILES(src/modules/lua/Makefile)
    echo "Will compile and build mod_lua module."
else
    echo "Will NOT compile and build mod_lua module."
fi

AC_OUTPUT

